# plc_tab.py
import re
import sys
from typing import Optional
from .base_parser import GenericTemplateLogParser
from plc_visualizer.models import LogEntry
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




# Register
from .parser_registry import parser_registry
parser_registry.register(PLCTabParser())
