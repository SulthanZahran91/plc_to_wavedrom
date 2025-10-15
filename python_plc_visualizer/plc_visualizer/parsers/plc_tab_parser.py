# plc_tab.py
import re
from .base_parser import GenericTemplateLogParser

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




# Register
from .parser_registry import parser_registry
parser_registry.register(PLCTabParser())
