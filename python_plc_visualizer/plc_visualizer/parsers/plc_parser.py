import re
from .base_parser import GenericTemplateLogParser

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

# Register
from .parser_registry import parser_registry
parser_registry.register(PLCDebugParser())