# baseparser.py
"""
Base + generic template-driven log parser with fast paths.

Highlights:
- Compiled once: parse-template (if used), device-id regex, int/float regex.
- Fast timestamp parser for "%Y-%m-%d %H:%M:%S.%f".
- Exception-free type inference (regex checks first, then parse).
- Threaded *or* process-based batch parsing.
- Batching of set updates, string interning to reduce churn.
- Optional skip-sort if the log is already chronological.
- Subclass hooks:
    - TEMPLATE: parse-style template string (optional if LINE_RE provided)
    - LINE_RE: precompiled re.Pattern with named groups (ts, path, signal, value, etc.)
    - TYPE_MAP, TIMESTAMP_FORMAT, DEVICE_ID_REGEX, INFER_TYPES, etc.

If a subclass sets LINE_RE, the parser uses the regex fast path.
Otherwise, it uses a compiled `parse` template once per class.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterator, Optional, Dict, Set, List, Tuple, Iterable
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
import re
import sys

# Optional import (installed in your project). Only used if TEMPLATE is provided.
try:
    from parse import compile as parse_compile, Result as ParseResultTemplate
except Exception:  # pragma: no cover
    parse_compile = None
    ParseResultTemplate = None

# Project models
from plc_visualizer.models import (
    LogEntry,
    ParseResult,
    ParseError,
    SignalType,
    ParsedLog,
)

# ---------------------- Small fast utilities (shared) ----------------------

# Device-ID default pattern (subclasses may override via DEVICE_ID_REGEX)
_DEFAULT_DID_RE = re.compile(r"([A-Za-z0-9_-]+-\d+)(?:@[^\]]+)?$")

# Regexes for numeric detection (avoid exceptions in hot path)
_INT_RE = re.compile(
    r'^[+-]?(?:0[xX][0-9A-Fa-f_]+|0[bB][01_]+|0[oO][0-7_]+|\d[\d_,]*)$'
)
_FLT_RE = re.compile(
    r'^[+-]?(?:\d[\d_,]*\.\d+|\.\d+|\d+\.)(?:[eE][+-]?\d+)?$'
    r'|^[+-]?\d+(?:[eE][+-]?\d+)$'
)

_BOOL_TRUE = {"ON", "TRUE", "1", "YES"}
_BOOL_FALSE = {"OFF", "FALSE", "0", "NO"}


def _fast_ts(ts: str) -> datetime:
    """Fast parser for '%Y-%m-%d %H:%M:%S.%f' (handles millis/micros)."""
    # Example: "2025-09-25 06:02:11.086" or ".086123"
    year = int(ts[0:4])
    month = int(ts[5:7])
    day = int(ts[8:10])
    hour = int(ts[11:13])
    minute = int(ts[14:16])
    second = int(ts[17:19])
    micro = 0
    if len(ts) > 19 and ts[19] == ".":
        frac = ts[20:]
        if frac:
            micro = int(frac[:6].ljust(6, "0"))
    return datetime(year, month, day, hour, minute, second, micro)


def _is_int_like(s: str) -> bool:
    return bool(_INT_RE.match(s))


def _is_float_like(s: str) -> bool:
    return bool(_FLT_RE.match(s))


def _parse_int_like(s: str) -> int:
    t = s.replace(",", "").replace("_", "").strip()
    if t.startswith(("+0x", "-0x", "0x")):
        return int(t, 16)
    if t.startswith(("+0b", "-0b", "0b")):
        return int(t, 2)
    if t.startswith(("+0o", "-0o", "0o")):
        return int(t, 8)
    return int(t, 10)


def _parse_float_like(s: str) -> float:
    t = s.replace(",", "").replace("_", "").strip()
    return float(t)


def _infer_type_fast(raw: str, has_float: bool) -> SignalType:
    s = (raw or "").strip()
    if not s:
        return SignalType.STRING
    u = s.upper()
    if u in _BOOL_TRUE or u in _BOOL_FALSE:
        return SignalType.BOOLEAN
    if _is_int_like(s):
        return SignalType.INTEGER
    if has_float and _is_float_like(s):
        return getattr(SignalType, "FLOAT")
    return SignalType.STRING


def _parse_value_fast(s: str, stype: SignalType, infer_ok: bool, has_float: bool):
    s = (s or "").strip()
    if stype == SignalType.BOOLEAN:
        u = s.upper()
        if u in _BOOL_TRUE:
            return True
        if u in _BOOL_FALSE:
            return False
        if infer_ok:
            return s
        raise ValueError(f"Invalid boolean value: {s}")

    if stype == SignalType.INTEGER:
        try:
            return _parse_int_like(s)
        except ValueError:
            if infer_ok:
                return s
            raise

    if hasattr(SignalType, "FLOAT") and stype == getattr(SignalType, "FLOAT"):
        try:
            return _parse_float_like(s)
        except ValueError:
            if infer_ok:
                return s
            raise

    # STRING or unknown enum → just return the original text
    return s


# ---------------------- Public base classes ----------------------

class BaseParser(ABC):
    name: str = "base"

    @abstractmethod
    def parse(
        self,
        file_path: str,
        num_workers: Optional[int] = None,
        *,
        use_processes: bool = False,
    ) -> ParseResult:
        raise NotImplementedError

    def can_parse(self, file_path: str) -> bool:
        """Default: accept. Subclasses can override with a template/regex sniff."""
        return True

    def parse_streaming(self, file_path: str) -> Iterator[LogEntry]:
        """Synchronous streaming parse; yields entries as they are read."""
        result = self.parse(file_path)
        if result.data:
            yield from result.data.entries


# ---------------------- Generic template/regex parser ----------------------

class GenericTemplateLogParser(BaseParser):
    """
    Template-driven (or regex-driven) parser with optional concurrency + inference.

    Subclasses provide either:
      - TEMPLATE (string for parse module). Example:
        "{ts} [] {path}\t{signal}\t{direction}\t{value}\t{blank}\t{location}\t{flag1}\t{flag2}\t{ts2}"
        (We compile it once per class.)
      - LINE_RE (precompiled regex with named groups: ts, path, signal, value, ...).
        Regex fast path is *much* faster than parse().

    Type map:
      TYPE_MAP: {"boolean": SignalType.BOOLEAN, ...} (used if the line declares a dtype)

    Performance knobs:
      - BUFFER_SIZE: file read buffer
      - BATCH_SIZE: batch merging of unique signal/device strings
      - LINES_PER_BATCH: batch size per worker (increase for processes)
      - USE_CHRONO_DETECTION: skip final sort if timestamps are already monotonic

    Concurrency:
      parse(file_path, num_workers=None, use_processes=False)
          None or 1 -> single-threaded
          0         -> auto (#CPUs)
          >1        -> that many threads/processes

    Subclass extras:
      - TIMESTAMP_FORMAT: if not "%Y-%m-%d %H:%M:%S.%f", override _parse_ts()
      - DEVICE_ID_REGEX: compiled regex or pattern string
    """

    # ----- subclass knobs -----
    TEMPLATE: Optional[str] = None
    LINE_RE: Optional[re.Pattern[str]] = None  # if provided, used instead of TEMPLATE

    TYPE_MAP: Dict[str, SignalType] = {
        "boolean": SignalType.BOOLEAN,
        "bool": SignalType.BOOLEAN,
        "string": SignalType.STRING,
        "str": SignalType.STRING,
        "integer": SignalType.INTEGER,
        "int": SignalType.INTEGER,
        "short": SignalType.INTEGER,
    }
    TIMESTAMP_FORMAT: str = "%Y-%m-%d %H:%M:%S.%f"
    DEVICE_ID_REGEX = _DEFAULT_DID_RE  # can be pattern or compiled regex

    # Performance knobs
    BUFFER_SIZE = 1 << 20     # 1 MiB; good default on SSD/NVMe
    BATCH_SIZE = 2000         # for set flush (single-thread & merge stage)
    LINES_PER_BATCH = 20_000  # tune upward for processes (e.g., 50_000)

    # Type inference controls
    INFER_TYPES: bool = True

    # Sort behavior controls
    USE_CHRONO_DETECTION: bool = True  # avoid sort if timestamps monotonic

    # --- class-level caches (one per subclass) ---
    _CACHED_PARSE = None          # compiled parse template (if TEMPLATE provided)
    _CACHED_DID_RE = None         # compiled device-id regex
    _HAS_FLOAT = hasattr(SignalType, "FLOAT")

    # ---------- Capability probe ----------
    def can_parse(self, file_path: str) -> bool:
        """
        Try matching a few non-blank lines. Prefers LINE_RE if provided; else TEMPLATE if parse is available.
        """
        try:
            with open(
                file_path, "r", encoding="utf-8-sig", buffering=self.BUFFER_SIZE
            ) as f:
                checked = matched = 0
                for line in f:
                    if not line or line.isspace():
                        continue
                    checked += 1
                    if self.LINE_RE is not None:
                        if self.LINE_RE.match(line):
                            matched += 1
                    elif self._get_compiled_template() is not None:
                        if self._get_compiled_template().parse(line):
                            matched += 1
                    else:
                        # No way to check; bail conservative.
                        return True
                    if checked >= 5:
                        break
                return checked > 0 and (matched / checked) >= 0.6
        except Exception:
            return False

    # ---------- Public API ----------
    def parse(
        self,
        file_path: str,
        num_workers: Optional[int] = None,
        *,
        use_processes: bool = False,
    ) -> ParseResult:
        if num_workers is None or num_workers == 1:
            return self._parse_single(file_path)

        # Determine worker count
        if num_workers == 0:
            try:
                from os import cpu_count

                num_workers = cpu_count() or 4
            except Exception:
                num_workers = 4

        if use_processes:
            return self._parse_concurrent(file_path, int(num_workers), engine="process")
        else:
            return self._parse_concurrent(file_path, int(num_workers), engine="thread")

    def parse_streaming(self, file_path: str) -> Iterator[LogEntry]:
        """Yield entries one by one (single-thread)."""
        did_re = self._get_device_id_regex()
        tpl = self._get_compiled_template()
        for entry in self._iter_entries(file_path, did_re, tpl):
            yield entry

    # ---------- Single-thread path ----------
    def _parse_single(self, file_path: str) -> ParseResult:
        entries: List[LogEntry] = []
        signals: Set[str] = set()
        devices: Set[str] = set()
        errors: List[ParseError] = []

        sig_batch: List[str] = []
        dev_batch: List[str] = []

        did_re = self._get_device_id_regex()
        tpl = self._get_compiled_template()

        out_of_order = False
        last_ts: Optional[datetime] = None

        try:
            with open(
                file_path, "r", encoding="utf-8-sig", buffering=self.BUFFER_SIZE
            ) as f:
                for i, line in enumerate(f, start=1):
                    if not line or line.isspace():
                        continue
                    try:
                        entry = self._parse_line_hot(line, did_re, tpl)
                        # Chrono check
                        if self.USE_CHRONO_DETECTION:
                            if last_ts and entry.timestamp < last_ts:
                                out_of_order = True
                            last_ts = entry.timestamp

                        entries.append(entry)

                        # Batch dedup keys (intern strings to cut memory churn)
                        did = sys.intern(entry.device_id)
                        sgn = sys.intern(entry.signal_name)
                        sig_batch.append(f"{did}::{sgn}")
                        dev_batch.append(did)
                        if len(sig_batch) >= self.BATCH_SIZE:
                            signals.update(sig_batch)
                            devices.update(dev_batch)
                            sig_batch.clear()
                            dev_batch.clear()

                    except ValueError as e:
                        errors.append(
                            ParseError(i, line.rstrip("\r\n"), str(e))
                        )

                if sig_batch:
                    signals.update(sig_batch)
                    devices.update(dev_batch)

        except FileNotFoundError:
            errors.append(ParseError(0, "", f"File not found: {file_path}"))
            return ParseResult(data=None, errors=errors)
        except Exception as e:
            errors.append(ParseError(0, "", f"Failed to read file: {e}"))
            return ParseResult(data=None, errors=errors)

        if not entries:
            return ParseResult(data=None, errors=errors)

        if not self.USE_CHRONO_DETECTION or out_of_order:
            entries.sort(key=lambda e: e.timestamp)

        parsed = ParsedLog(entries=entries, signals=signals, devices=devices)
        return ParseResult(data=parsed, errors=errors)

    # ---------- Concurrent path (thread or process) ----------
    def _parse_concurrent(
        self, file_path: str, workers: int, *, engine: str = "thread"
    ) -> ParseResult:
        """
        Batch parsing with threads or processes.
        For CPU-bound logs, prefer engine="process".
        """
        errors: List[ParseError] = []
        all_entries: List[LogEntry] = []
        all_signals: Set[str] = set()
        all_devices: Set[str] = set()

        # Configure worker
        cfg = _WorkerConfig(
            ts_format=self.TIMESTAMP_FORMAT,
            type_map=self.TYPE_MAP,
            device_id_regex=self._get_device_id_regex().pattern
            if isinstance(self._get_device_id_regex(), re.Pattern)
            else str(self._get_device_id_regex()),
            infer_types=self.INFER_TYPES,
            has_float=self._HAS_FLOAT,
            use_line_re=self.LINE_RE is not None,
        )

        # For line regex path, we pass its pattern (compiled in worker)
        cfg.line_re_pattern = self.LINE_RE.pattern if self.LINE_RE is not None else None

        # For parse-template path, pass rendered template (compiled in worker)
        tpl = self._get_compiled_template()
        cfg.parse_template = getattr(tpl, "_template", None) if tpl else self.TEMPLATE

        # Choose executor
        Executor = ThreadPoolExecutor if engine == "thread" else ProcessPoolExecutor

        try:
            futures = []
            with Executor(max_workers=workers) as ex:
                for start_line, batch in self._iter_line_batches(
                    file_path, self.LINES_PER_BATCH
                ):
                    futures.append(
                        ex.submit(_parse_lines_batch, batch, start_line, cfg)
                    )

                # Merge results
                out_of_order = False
                last_ts: Optional[datetime] = None
                for fut in as_completed(futures):
                    batch_entries, batch_signals, batch_devices, batch_errors = fut.result()

                    # Construct LogEntry in parent (cheaper pickling from workers)
                    for did, sig, ts_str, val, stype in batch_entries:
                        ts = (
                            _fast_ts(ts_str)
                            if self.TIMESTAMP_FORMAT == "%Y-%m-%d %H:%M:%S.%f"
                            else self._parse_ts(ts_str)
                        )
                        if self.USE_CHRONO_DETECTION:
                            if last_ts and ts < last_ts:
                                out_of_order = True
                            last_ts = ts

                        all_entries.append(
                            LogEntry(
                                device_id=sys.intern(did),
                                signal_name=sys.intern(sig),
                                timestamp=ts,
                                value=val,
                                signal_type=stype,
                            )
                        )

                    all_signals.update(batch_signals)
                    all_devices.update(batch_devices)
                    errors.extend(batch_errors)

        except FileNotFoundError:
            errors.append(ParseError(0, "", f"File not found: {file_path}"))
            return ParseResult(data=None, errors=errors)
        except Exception as e:
            errors.append(ParseError(0, "", f"Failed during concurrent parse: {e}"))
            return ParseResult(data=None, errors=errors)

        if not all_entries:
            return ParseResult(data=None, errors=errors)

        if not self.USE_CHRONO_DETECTION or out_of_order:
            all_entries.sort(key=lambda e: e.timestamp)

        parsed = ParsedLog(entries=all_entries, signals=all_signals, devices=all_devices)
        return ParseResult(data=parsed, errors=errors)

    # ---------- Helpers ----------
    def _iter_line_batches(
        self, file_path: str, lines_per_batch: int
    ) -> Iterator[Tuple[int, List[str]]]:
        """Yield (start_line_no, [lines...]) batches."""
        with open(file_path, "r", encoding="utf-8-sig", buffering=self.BUFFER_SIZE) as f:
            batch: List[str] = []
            start_line_no = 1
            for i, line in enumerate(f, start=1):
                batch.append(line)
                if len(batch) >= lines_per_batch:
                    yield start_line_no, batch
                    start_line_no = i + 1
                    batch = []
            if batch:
                yield start_line_no, batch

    def _get_compiled_template(self):
        """Compile and cache the parse-template once per subclass."""
        if self.LINE_RE is not None:
            return None  # regex fast path active
        if self.TEMPLATE is None:
            return None
        if parse_compile is None:
            raise RuntimeError(
                "parse module is not available but TEMPLATE was provided."
            )
        cls = self.__class__
        if cls._CACHED_PARSE is None:
            cls._CACHED_PARSE = parse_compile(self.TEMPLATE)
        return cls._CACHED_PARSE

    def _get_device_id_regex(self) -> re.Pattern:
        """Normalize DEVICE_ID_REGEX to a compiled pattern and cache it."""
        cls = self.__class__
        if cls._CACHED_DID_RE is not None:
            return cls._CACHED_DID_RE
        did = self.DEVICE_ID_REGEX
        if isinstance(did, re.Pattern):
            cls._CACHED_DID_RE = did
        else:
            cls._CACHED_DID_RE = re.compile(str(did))
        return cls._CACHED_DID_RE

    def _parse_ts(self, ts_str: str) -> datetime:
        if self.TIMESTAMP_FORMAT == "%Y-%m-%d %H:%M:%S.%f":
            return _fast_ts(ts_str)
        # Fallback to strptime if subclass changed the format
        try:
            return datetime.strptime(ts_str, self.TIMESTAMP_FORMAT)
        except ValueError as e:
            raise ValueError(f"Invalid timestamp: {ts_str} ({e})")

    def _parse_line_hot(
        self, line: str, did_re: re.Pattern, tpl_compiled
    ) -> LogEntry:
        """
        Hot-path line parser. Prefers LINE_RE; else compiled parse-template.
        Subclasses with very specific formats should set LINE_RE for speed.
        """
        if self.LINE_RE is not None:
            m = self.LINE_RE.match(line)
            if not m:
                raise ValueError("Line does not match format (regex)")
            d = m.groupdict()

            ts_str = (d.get("ts") or "").strip()
            ts = self._parse_ts(ts_str)

            path = (d.get("path") or "").strip()
            md = did_re.search(path)
            if not md:
                raise ValueError(f"Device id not found in path: {path}")
            device_id = sys.intern(md.group(1))

            signal = sys.intern((d.get("signal") or "").strip())
            raw_value = (d.get("value") or "").strip()

            # 1) declared dtype (optional)
            dtype_token = (d.get("dtype") or "").strip().lower()
            stype = self.TYPE_MAP.get(dtype_token)

            # 2) inference if needed
            if stype is None and self.INFER_TYPES:
                stype = _infer_type_fast(raw_value, self._HAS_FLOAT)
            if stype is None:
                raise ValueError(f"Invalid/unknown type: {dtype_token or '<missing>'}")

            # 3) parse value (graceful downgrade)
            value = _parse_value_fast(raw_value, stype, self.INFER_TYPES, self._HAS_FLOAT)

            return LogEntry(
                device_id=device_id,
                signal_name=signal,
                timestamp=ts,
                value=value,
                signal_type=stype,
            )

        # else: parse-template path
        if tpl_compiled is None:
            raise ValueError("No LINE_RE or TEMPLATE provided.")
        m = tpl_compiled.parse(line)
        if not m:
            raise ValueError("Line does not match template")
        d = m.named

        ts = self._parse_ts(d.get("ts", ""))
        path = d.get("path", "")
        md = did_re.search(path)
        if not md:
            raise ValueError(f"Device id not found in path: {path}")
        device_id = sys.intern(md.group(1))
        signal_name = sys.intern((d.get("signal") or "").strip())

        dtype_token = (d.get("dtype") or "").strip().lower()
        stype = self.TYPE_MAP.get(dtype_token)

        raw_value = d.get("value", "")
        if stype is None and self.INFER_TYPES:
            stype = _infer_type_fast(raw_value, self._HAS_FLOAT)
        if stype is None:
            raise ValueError(f"Invalid/unknown type: {dtype_token or '<missing>'}")

        value = _parse_value_fast(raw_value, stype, self.INFER_TYPES, self._HAS_FLOAT)

        return LogEntry(
            device_id=device_id,
            signal_name=signal_name,
            timestamp=ts,
            value=value,
            signal_type=stype,
        )


# ----------------- Worker plumbing (module-level for reuse) -----------------

class _WorkerConfig:
    """Lightweight, executor-friendly config container."""
    __slots__ = (
        "ts_format",
        "type_map",
        "device_id_regex",
        "infer_types",
        "has_float",
        "use_line_re",
        "line_re_pattern",
        "parse_template",
    )

    def __init__(
        self,
        ts_format: str,
        type_map: Dict[str, SignalType],
        device_id_regex: str,
        infer_types: bool,
        has_float: bool,
        use_line_re: bool,
    ):
        self.ts_format = ts_format
        self.type_map = type_map
        self.device_id_regex = device_id_regex
        self.infer_types = infer_types
        self.has_float = has_float
        self.use_line_re = use_line_re
        # set separately by caller:
        self.line_re_pattern: Optional[str] = None
        self.parse_template: Optional[str] = None


def _parse_lines_batch(
    lines: List[str], start_line_no: int, cfg: _WorkerConfig
):
    """
    Parse a batch of lines in a worker.
    Returns (entries, signals, devices, errors) where:
      - entries: list of tuples (device_id, signal_name, ts_str, value, signal_type)
      - signals/devices: sets of strings
      - errors: list[ParseError]
    We return tuples instead of LogEntry to reduce pickling load.
    """
    entries: List[Tuple[str, str, str, object, SignalType]] = []
    signals: Set[str] = set()
    devices: Set[str] = set()
    errors: List[ParseError] = []

    did_re = re.compile(cfg.device_id_regex)

    # Choose timestamp function
    fast_ts_format = cfg.ts_format == "%Y-%m-%d %H:%M:%S.%f"
    # Prepare format parsers
    line_re = re.compile(cfg.line_re_pattern) if cfg.use_line_re and cfg.line_re_pattern else None
    tpl_parser = parse_compile(cfg.parse_template) if (not line_re and cfg.parse_template and parse_compile) else None

    for idx, line in enumerate(lines):
        line_no = start_line_no + idx
        if not line or line.isspace():
            continue
        try:
            if line_re is not None:
                m = line_re.match(line)
                if not m:
                    raise ValueError("Line does not match format (regex)")
                d = m.groupdict()

                ts_str = (d.get("ts") or "").strip()
                # leave as string; parent will convert to datetime
                path = (d.get("path") or "").strip()
                md = did_re.search(path)
                if not md:
                    raise ValueError(f"Device id not found in path: {path}")
                device_id = md.group(1)

                signal = (d.get("signal") or "").strip()
                raw = (d.get("value") or "").strip()

                dtype_token = (d.get("dtype") or "").strip().lower()
                st = cfg.type_map.get(dtype_token)

                if st is None and cfg.infer_types:
                    st = _infer_type_fast(raw, cfg.has_float)
                if st is None:
                    raise ValueError(f"Invalid/unknown type: {dtype_token or '<missing>'}")

                try:
                    value = _parse_value_fast(raw, st, cfg.infer_types, cfg.has_float)
                except ValueError as e:
                    raise

                entries.append((device_id, signal, ts_str, value, st))
                signals.add(f"{device_id}::{signal}")
                devices.add(device_id)

            else:
                if tpl_parser is None:
                    raise ValueError("No LINE_RE or TEMPLATE available in worker")
                m = tpl_parser.parse(line)
                if not m:
                    raise ValueError("Line does not match template")
                d = m.named

                ts_str = (d.get("ts") or "").strip()
                path = d.get("path", "")
                md = did_re.search(path)
                if not md:
                    raise ValueError(f"Device id not found in path: {path}")
                device_id = md.group(1)

                signal = (d.get("signal") or "").strip()
                raw = (d.get("value") or "").strip()

                dtype_token = (d.get("dtype") or "").strip().lower()
                st = cfg.type_map.get(dtype_token)

                if st is None and cfg.infer_types:
                    st = _infer_type_fast(raw, cfg.has_float)
                if st is None:
                    raise ValueError(f"Invalid/unknown type: {dtype_token or '<missing>'}")

                try:
                    value = _parse_value_fast(raw, st, cfg.infer_types, cfg.has_float)
                except ValueError as e:
                    raise

                entries.append((device_id, signal, ts_str, value, st))
                signals.add(f"{device_id}::{signal}")
                devices.add(device_id)

        except ValueError as e:
            errors.append(ParseError(line_no, line.rstrip("\r\n"), str(e)))

    return entries, signals, devices, errors
