"""Pluggable parser system for different log file formats."""

from .base_parser import BaseParser
from .parser_registry import ParserRegistry, parser_registry
from .default_parser import DefaultParser  # Import to trigger registration

__all__ = [
    "BaseParser",
    "ParserRegistry",
    "parser_registry",
    "DefaultParser",
]
