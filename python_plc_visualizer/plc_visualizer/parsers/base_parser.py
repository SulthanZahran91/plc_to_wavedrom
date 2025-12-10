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

    def parse_time_window(
        self,
        file_path: str,
        start_time: datetime,
        end_time: datetime
    ) -> ParseResult:
        """Parse only entries within a specific time window.

        This is a memory optimization for large files. The default implementation
        parses the entire file and filters, but subclasses can override for
        more efficient implementations (e.g., seeking to time range).

        Args:
            file_path: Path to the log file
            start_time: Start of time window (inclusive)
            end_time: End of time window (exclusive)

        Returns:
            ParseResult containing only entries in the time window
        """
        # Default: parse entire file and filter
        # Subclasses should override for better performance
        result = self.parse(file_path)

        if not result.success or not result.data:
            return result

        # Filter entries to time window
        filtered_entries = [
            entry for entry in result.data.entries
            if start_time <= entry.timestamp < end_time
        ]

        # Create new ParsedLog with filtered entries
        filtered_log = ParsedLog(
            entries=filtered_entries,
            signals=result.data.signals,  # Keep all signals metadata
            devices=result.data.devices,  # Keep all devices metadata
            time_range=(start_time, end_time)
        )

        return ParseResult(data=filtered_log, errors=result.errors)


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
        import time
        start_time = time.perf_counter()
        
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
            elapsed = time.perf_counter() - start_time
            return ParseResult(data=None, errors=errors, processing_time=elapsed)
        except Exception as e:
            errors.append(ParseError(0, "", f"Failed to read file: {e}"))
            elapsed = time.perf_counter() - start_time
            return ParseResult(data=None, errors=errors, processing_time=elapsed)

        if not entries:
            elapsed = time.perf_counter() - start_time
            return ParseResult(data=None, errors=errors, processing_time=elapsed)

        if not self.USE_CHRONO_DETECTION or out_of_order:
            entries.sort(key=lambda e: e.timestamp)

        parsed = ParsedLog(entries=entries, signals=signals, devices=devices)
        elapsed = time.perf_counter() - start_time
        return ParseResult(data=parsed, errors=errors, processing_time=elapsed)

    # ---------- Concurrent path (thread or process) ----------
    def _parse_concurrent(
        self, file_path: str, workers: int, *, engine: str = "thread"
    ) -> ParseResult:
        """
        Batch parsing with threads or processes.
        For CPU-bound logs, prefer engine="process".
        """
        import time
        start_time = time.perf_counter()
        
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
            parser_name=self.name,
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
            elapsed = time.perf_counter() - start_time
            return ParseResult(data=None, errors=errors, processing_time=elapsed)
        except Exception as e:
            errors.append(ParseError(0, "", f"Failed during concurrent parse: {e}"))
            elapsed = time.perf_counter() - start_time
            return ParseResult(data=None, errors=errors, processing_time=elapsed)

        if not all_entries:
            elapsed = time.perf_counter() - start_time
            return ParseResult(data=None, errors=errors, processing_time=elapsed)

        if not self.USE_CHRONO_DETECTION or out_of_order:
            all_entries.sort(key=lambda e: e.timestamp)

        parsed = ParsedLog(entries=all_entries, signals=all_signals, devices=all_devices)
        elapsed = time.perf_counter() - start_time
        return ParseResult(data=parsed, errors=errors, processing_time=elapsed)

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

    def _fast_parse_line(
        self, line: str, did_re: re.Pattern
    ) -> Optional[LogEntry]:
        """
        Ultra-fast delimiter-indexed parser hook for subclasses.

        Override this method to implement custom high-performance parsing
        using string operations (find, split, slice) instead of regex.

        Performance benefits: 5-50x faster than regex for well-formed lines.

        Returns:
            LogEntry if successfully parsed, None to fall back to regex

        Raises:
            Any exception will trigger graceful fallback to regex parsing

        Example (tab-delimited):
            parts = line.split('\\t')
            if len(parts) < 9:
                return None  # fall back to regex
            timestamp = self._parse_ts(parts[0].strip())
            # ... extract other fields
            return LogEntry(...)
        """
        return None  # Default: no fast path, use regex

    def _parse_line_hot(
        self, line: str, did_re: re.Pattern, tpl_compiled
    ) -> LogEntry:
        """
        Hot-path line parser. Tries fast delimiter parsing first, then regex/template.

        Parsing priority:
        1. _fast_parse_line() - Ultra-fast delimiter/index-based (if overridden)
        2. LINE_RE - Regex pattern matching
        3. TEMPLATE - Parse module template matching
        """
        # Try ultra-fast delimiter parsing first (if subclass provides it)
        try:
            entry = self._fast_parse_line(line, did_re)
            if entry is not None:
                return entry
        except Exception:
            # Any error in fast path: fall through to regex safety net
            pass

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

def _try_fast_parse_worker(
    line: str, parser_name: str, did_re: re.Pattern, type_map: Dict[str, SignalType],
    infer_types: bool, has_float: bool
) -> Optional[Tuple[str, str, str, str, str, str]]:
    """
    Module-level fast parse dispatcher for worker processes.
    Returns (device_id, signal, ts_str, raw_value, dtype_token, path) or None.
    """
    if parser_name == "plc_tab":
        # Fast parse for tab-delimited format
        # Format: "YYYY-MM-DD HH:MM:SS.fff [] path\tsignal\tdirection\tvalue\t..."
        if '\t' not in line:
            return None

        bracket_idx = line.find(' [] ')
        if bracket_idx == -1:
            return None

        ts_str = line[:bracket_idx].strip()
        if len(ts_str) < 19:
            return None

        remainder = line[bracket_idx + 4:]
        parts = remainder.split('\t')

        if len(parts) < 8:
            return None

        path = parts[0].strip()
        signal = parts[1].strip()
        value_str = parts[3].strip()

        md = did_re.search(path)
        if not md:
            return None
        device_id = md.group(1)

        # Return tuple: (device_id, signal, ts_str, raw_value, dtype_token, path)
        # dtype_token is empty for tab parser (inferred from value)
        return (device_id, signal, ts_str, value_str, "", path)

    elif parser_name == "plc_debug":
        # Fast parse for bracket-delimited format
        # Format: "YYYY-MM-DD HH:MM:SS.fff [Level] [path] [cat:signal] (dtype) : value"
        if '[' not in line or '(' not in line:
            return None

        # Extract timestamp
        bracket1 = line.find('[')
        if bracket1 == -1:
            return None
        ts_str = line[:bracket1].strip()
        if len(ts_str) < 19:
            return None

        # Skip [Level], find [path]
        bracket2 = line.find('[', bracket1 + 1)
        if bracket2 == -1:
            return None

        bracket2_close = line.find(']', bracket2)
        if bracket2_close == -1:
            return None
        path = line[bracket2 + 1:bracket2_close].strip()

        # Extract [category:signal]
        bracket3 = line.find('[', bracket2_close + 1)
        bracket3_close = line.find(']', bracket3)
        if bracket3 == -1 or bracket3_close == -1:
            return None
        cat_signal = line[bracket3 + 1:bracket3_close].strip()

        colon_idx = cat_signal.find(':')
        if colon_idx == -1:
            return None
        signal = cat_signal[colon_idx + 1:].strip()

        # Extract (dtype)
        paren_open = line.find('(', bracket3_close)
        paren_close = line.find(')', paren_open)
        if paren_open == -1 or paren_close == -1:
            return None
        dtype_token = line[paren_open + 1:paren_close].strip()

        # Extract value after ": "
        colon_space = line.find(':', paren_close)
        if colon_space == -1:
            return None
        value_str = line[colon_space + 1:].strip()

        md = did_re.search(path)
        if not md:
            return None
        device_id = md.group(1)

        return (device_id, signal, ts_str, value_str, dtype_token, path)

    elif parser_name == "mcs_log":
        # MCS format - special handling for multi-entry lines
        # Format: "YYYY-MM-DD HH:MM:SS.mmm [ACTION=ID] [Key=Value], [Key2=Value2], ..."
        # or: "YYYY-MM-DD HH:MM:SS.mmm [ACTION=ID1, ID2] [Key=Value], ..."
        
        # Return special marker indicating MCS multi-entry line
        # We'll use a special tuple format: (None, None, line, None, None, "MCS_MULTI_ENTRY")
        # The worker will recognize this and process it differently
        if '[' not in line or '=' not in line:
            return None
        
        # Quick validation - must start with timestamp and have [ACTION=...]
        if len(line) < 20:
            return None
        
        # Check for action pattern
        action_start = line.find('[', 19)
        if action_start == -1:
            return None
        
        action_content = line[action_start+1:action_start+10]  # Check first few chars
        if not any(act in action_content for act in ['ADD=', 'UPDATE=', 'REMOVE=']):
            return None
        
        # Return special marker with the full line
        return (None, None, line, None, None, "MCS_MULTI_ENTRY")

    # Add more parser types here as needed
    return None


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
        "parser_name",
    )

    def __init__(
        self,
        ts_format: str,
        type_map: Dict[str, SignalType],
        device_id_regex: str,
        infer_types: bool,
        has_float: bool,
        use_line_re: bool,
        parser_name: str = "base",
    ):
        self.ts_format = ts_format
        self.type_map = type_map
        self.device_id_regex = device_id_regex
        self.infer_types = infer_types
        self.has_float = has_float
        self.use_line_re = use_line_re
        self.parser_name = parser_name
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
            # Try fast parse first (if available for this parser type)
            fast_result = None
            try:
                fast_result = _try_fast_parse_worker(
                    line, cfg.parser_name, did_re, cfg.type_map,
                    cfg.infer_types, cfg.has_float
                )
            except Exception:
                pass  # Fall back to regex on any error

            if fast_result is not None:
                # Check if this is an MCS multi-entry line
                if len(fast_result) >= 6 and fast_result[5] == "MCS_MULTI_ENTRY":
                    # Import MCS parser's line parsing logic
                    try:
                        from plc_visualizer.parsers.mcs_parser import MCSLogParser
                        mcs_parser = MCSLogParser()
                        
                        # Parse the line to get multiple entries
                        line_entries = mcs_parser._parse_line_to_entries(fast_result[2])
                        
                        for device_id, signal, timestamp, value, signal_type in line_entries:
                            # Convert timestamp to string for pickling
                            ts_str = timestamp.strftime("%Y-%m-%d %H:%M:%S.%f")
                            entries.append((device_id, signal, ts_str, value, signal_type))
                            signals.add(f"{device_id}::{signal}")
                            devices.add(device_id)
                        
                        continue  # Skip regex parsing
                    except Exception as e:
                        # If MCS parsing fails, log error and continue
                        errors.append(ParseError(
                            line=line_no,
                            content=fast_result[2][:100],
                            reason=f"MCS multi-entry parsing failed: {e}"
                        ))
                        continue
                
                # Regular single-entry fast parse
                device_id, signal, ts_str, raw, dtype_token, path = fast_result

                st = cfg.type_map.get(dtype_token.lower()) if dtype_token else None
                if st is None and cfg.infer_types:
                    st = _infer_type_fast(raw, cfg.has_float)
                if st is None:
                    raise ValueError(f"Invalid/unknown type: {dtype_token or '<missing>'}")

                value = _parse_value_fast(raw, st, cfg.infer_types, cfg.has_float)
                entries.append((device_id, signal, ts_str, value, st))
                signals.add(f"{device_id}::{signal}")
                devices.add(device_id)
                continue  # Skip regex parsing

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
