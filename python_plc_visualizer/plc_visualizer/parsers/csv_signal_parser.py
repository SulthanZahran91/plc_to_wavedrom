import re
from .base_parser import GenericTemplateLogParser

class CSVSignalParser(GenericTemplateLogParser):
    """Parser for CSV signal logs with format: Timestamp,DeviceID,Signal,Value

    Example:
        2025-10-21 23:08:27.995,B1ACNV13309-104@D19,B,62
        2025-10-21 23:08:27.995,B1ACPT15001-104@D19,Status,Error
    """
    name = "csv_signal"

    # Regex pattern for CSV format: Timestamp,DeviceID,Signal,Value
    LINE_RE = re.compile(
        r'^(?P<ts>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d+)\s*,\s*'  # timestamp
        r'(?P<path>[^,]+)\s*,\s*'                                     # device_id (path)
        r'(?P<signal>[^,]+)\s*,\s*'                                   # signal name
        r'(?P<value>.*?)\s*$'                                         # value
    )


# Register
from .parser_registry import parser_registry
parser_registry.register(CSVSignalParser())
