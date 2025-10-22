# plc_tab.py
import re
import sys
from datetime import datetime
from typing import Optional
from .base_parser import GenericTemplateLogParser
from plc_visualizer.models import LogEntry, ParseResult, ParsedLog, ParseError
from .base_parser import _infer_type_fast, _parse_value_fast

class PLCTabParser(GenericTemplateLogParser):
    name = "plc_tab"
    DEVICE_ID_REGEX = re.compile(r"([A-Za-z0-9_-]+)(?:@[^\]]+)?$")

    # # Keep TEMPLATE for can_parse() fallback if you want
    # TEMPLATE = (
    #     "{ts} [] {path}\t"
    #     "{signal}\t"
    #     "{direction}\t"
    #     "{value}\t"
    #     "{blank}\t"
    #     "{location}\t"
    #     "{flag1}\t"
    #     "{flag2}\t"
    #     "{ts2}"
    # )

    # FAST PATH: single regex that mirrors the template (no parse module on hot path)
    LINE_RE = re.compile(
        r'^(?P<ts>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d+)\s\[\]\s'
        r'(?P<path>[^\t]+)\t'
        r'(?P<signal>[^\t]+)\t'
        r'(?P<direction>[^\t]*)\t'
        r'(?P<value>[^\t]*)\t'
        r'(?P<blank>[^\t]*)\t'
        r'(?P<location>[^\t]*)\t'
        r'(?P<flag1>[^\t]*)'
        r'(?:\t(?P<flag2>[^\t]*))?'
        r'\t(?P<ts2>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d+)\s*$'
    )

    def _fast_parse_line(self, line: str, did_re: re.Pattern) -> Optional[LogEntry]:
        """
        Ultra-fast tab-delimited parser (~10-50x faster than regex).

        Format: "YYYY-MM-DD HH:MM:SS.fff [] path\\tsignal\\tdirection\\tvalue\\t..."
        """
        # Quick validation: check if line has tabs
        if '\t' not in line:
            return None

        # Find the " [] " separator between timestamp and path
        bracket_idx = line.find(' [] ')
        if bracket_idx == -1:
            return None

        # Extract timestamp (before " [] ")
        ts_str = line[:bracket_idx].strip()
        if len(ts_str) < 19:  # "YYYY-MM-DD HH:MM:SS" minimum
            return None

        # Rest of line after " [] " is tab-delimited
        remainder = line[bracket_idx + 4:]  # Skip " [] "
        parts = remainder.split('\t')

        # Need at least: path, signal, direction, value, blank, location, flag1, (optional flag2), ts2
        if len(parts) < 8:
            return None

        # Extract fields by index
        path = parts[0].strip()
        signal = parts[1].strip()
        # parts[2] is direction (not used for type inference)
        value_str = parts[3].strip()

        # Extract device_id from path
        md = did_re.search(path)
        if not md:
            return None
        device_id = sys.intern(md.group(1))

        # Infer type from value
        stype = _infer_type_fast(value_str, self._HAS_FLOAT) if self.INFER_TYPES else None
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
        """Optimized time-window parsing for tab-delimited format.

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

        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue

                    try:
                        # Try fast parse first
                        entry = self._fast_parse_line(line, self.DEVICE_ID_REGEX)

                        if not entry:
                            # Fallback to regex parse
                            entry = self._parse_line_hot(line, self.LINE_RE, self.DEVICE_ID_REGEX)

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
parser_registry.register(PLCTabParser())
