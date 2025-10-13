"""Pluggable parser system for different log file formats."""

from .base_parser import BaseParser
from .parser_registry import ParserRegistry, parser_registry
from .default_parser import DefaultParser  # Import to trigger registration
from .plc_parser import PLCDebugParser as plc_parser

__all__ = [
    "BaseParser",
    "ParserRegistry",
    "parser_registry",
    "DefaultParser",
    "plc_parser"
]
