import re
import sys
from datetime import datetime
from typing import Optional
from .base_parser import GenericTemplateLogParser
from plc_visualizer.models import LogEntry, ParseResult, ParsedLog, ParseError
from .base_parser import _infer_type_fast, _parse_value_fast

class PLCDebugParser(GenericTemplateLogParser):
    name = "plc_debug"

    # Robust, fast regex that mirrors:
    # 2025-09-22 13:00:00.199 [Debug] [<path>] [INPUT2:I_MOVE_IN] (Boolean) : ON
    LINE_RE = re.compile(
        r'^(?P<ts>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d+)\s+'            # ts
        r'\[(?P<level>[^\]]+)\]\s+'                                         # [level]
        r'\[(?P<path>[^\]]+)\]\s+'                                          # [path]
        r'\[(?P<category>[^:\]]+):(?P<signal>[^\]]+)\]\s+'                  # [category:signal]
        r'\((?P<dtype>[^)]+)\)\s*:\s*(?P<value>.*)\s*$'                     # (dtype) : value
    )

    def _fast_parse_line(self, line: str, did_re: re.Pattern) -> Optional[LogEntry]:
        """
        Ultra-fast bracket-delimited parser (~5-20x faster than regex).

        Format: "YYYY-MM-DD HH:MM:SS.fff [Level] [path] [cat:signal] (dtype) : value"
        """
        # Quick validation: check for required delimiters
        if '[' not in line or '(' not in line:
            return None

        # 1. Extract timestamp (before first '[')
        bracket1 = line.find('[')
        if bracket1 == -1:
            return None
        ts_str = line[:bracket1].strip()
        if len(ts_str) < 19:
            return None

        # 2. Skip [Level] - find second '['
        bracket2 = line.find('[', bracket1 + 1)
        if bracket2 == -1:
            return None

        # 3. Extract path from [path]
        bracket2_close = line.find(']', bracket2)
        if bracket2_close == -1:
            return None
        path = line[bracket2 + 1:bracket2_close].strip()

        # 4. Extract category:signal from [category:signal]
        bracket3 = line.find('[', bracket2_close + 1)
        bracket3_close = line.find(']', bracket3)
        if bracket3 == -1 or bracket3_close == -1:
            return None
        cat_signal = line[bracket3 + 1:bracket3_close].strip()

        # Split category:signal
        colon_idx = cat_signal.find(':')
        if colon_idx == -1:
            return None
        signal = cat_signal[colon_idx + 1:].strip()

        # 5. Extract dtype from (dtype)
        paren_open = line.find('(', bracket3_close)
        paren_close = line.find(')', paren_open)
        if paren_open == -1 or paren_close == -1:
            return None
        dtype_token = line[paren_open + 1:paren_close].strip()

        # 6. Extract value after ": "
        colon_space = line.find(':', paren_close)
        if colon_space == -1:
            return None
        value_str = line[colon_space + 1:].strip()

        # Extract device_id from path
        md = did_re.search(path)
        if not md:
            return None
        device_id = sys.intern(md.group(1))

        # Get signal type from TYPE_MAP or infer
        stype = self.TYPE_MAP.get(dtype_token.lower())
        if stype is None and self.INFER_TYPES:
            stype = _infer_type_fast(value_str, self._HAS_FLOAT)
        if stype is None:
            return None

        # Parse value
        value = _parse_value_fast(value_str, stype, self.INFER_TYPES, self._HAS_FLOAT)

        # Parse timestamp
        timestamp = self._parse_ts(ts_str)

        return LogEntry(
            device_id=device_id,
            signal_name=sys.intern(signal),
            timestamp=timestamp,
            value=value,
            signal_type=stype,
        )

    def parse_time_window(
        self,
        file_path: str,
        start_time: datetime,
        end_time: datetime
    ) -> ParseResult:
        """Optimized time-window parsing for bracket-delimited format.

        Only parses lines within the specified time range instead of the entire file.
        Assumes log entries are roughly chronologically sorted (typical for PLC logs).

        Args:
            file_path: Path to log file
            start_time: Start of time window
            end_time: End of time window

        Returns:
            ParseResult with entries in the time range
        """
        entries = []
        errors = []
        devices = set()
        signals = set()

        # Track if we've seen any entries in range yet
        seen_start = False
        consecutive_out_of_range = 0
        max_consecutive_out_of_range = 1000  # Stop after this many consecutive entries past end_time

        # Device ID regex for parsing
        device_id_re = re.compile(r"([A-Za-z0-9_-]+)(?:@[^\]]+)?$")

        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue

                    try:
                        # Try fast parse first
                        entry = self._fast_parse_line(line, device_id_re)

                        if not entry:
                            # Fallback to regex parse
                            entry = self._parse_line_hot(line, self.LINE_RE, device_id_re)

                        if not entry:
                            continue

                        # Check if entry is in time window
                        if entry.timestamp < start_time:
                            # Before window - skip
                            consecutive_out_of_range = 0
                            continue
                        elif entry.timestamp >= end_time:
                            # After window
                            consecutive_out_of_range += 1

                            # If we've seen entries in range and now we're consistently past it,
                            # we can stop (assumes chronological order)
                            if seen_start and consecutive_out_of_range > max_consecutive_out_of_range:
                                print(f"   ⚡ Early stop at line {line_num} (entries chronologically past time window)")
                                break
                            continue
                        else:
                            # In window!
                            seen_start = True
                            consecutive_out_of_range = 0
                            entries.append(entry)
                            devices.add(entry.device_id)
                            signals.add(f"{entry.device_id}::{entry.signal_name}")

                    except Exception as e:
                        errors.append(ParseError(
                            line=line_num,
                            content=line[:100],
                            reason=str(e)
                        ))

        except Exception as e:
            errors.append(ParseError(
                line=0,
                content="",
                reason=f"File read error: {e}"
            ))
            return ParseResult(data=None, errors=errors)

        # Create ParsedLog with filtered entries
        if entries:
            parsed_log = ParsedLog(
                entries=entries,
                signals=signals,
                devices=devices,
                time_range=(start_time, end_time)
            )
            return ParseResult(data=parsed_log, errors=errors)
        else:
            # No entries in range - return empty but valid result
            parsed_log = ParsedLog(
                entries=[],
                signals=signals,
                devices=devices,
                time_range=(start_time, end_time)
            )
            return ParseResult(data=parsed_log, errors=errors)

# Register
from .parser_registry import parser_registry
parser_registry.register(PLCDebugParser())