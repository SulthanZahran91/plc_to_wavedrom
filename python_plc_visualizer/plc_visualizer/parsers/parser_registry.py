"""Registry for managing multiple log file parsers."""

from typing import Optional

from plc_visualizer.models import ParseResult
from .base_parser import BaseParser


class ParserRegistry:
    """Registry for managing pluggable log file parsers.

    Allows registration of multiple parsers and auto-detection
    of the appropriate parser for a given file.
    """

    def __init__(self):
        self._parsers: dict[str, BaseParser] = {}
        self._default_parser: Optional[BaseParser] = None

    def register(self, parser: BaseParser, is_default: bool = False) -> None:
        """Register a parser.

        Args:
            parser: The parser instance to register
            is_default: Whether this should be the default parser
        """
        self._parsers[parser.name] = parser
        if is_default:
            self._default_parser = parser

    def get_parser(self, name: str) -> Optional[BaseParser]:
        """Get a parser by name.

        Args:
            name: Name of the parser

        Returns:
            Parser instance or None if not found
        """
        return self._parsers.get(name)

    def get_default_parser(self) -> Optional[BaseParser]:
        """Get the default parser.

        Returns:
            Default parser or None if not set
        """
        return self._default_parser

    def detect_parser(self, file_path: str) -> Optional[BaseParser]:
        """Auto-detect which parser can handle the file.

        Returns the first parser that can handle it, or the default parser.

        Args:
            file_path: Path to the file

        Returns:
            Suitable parser or None
        """
        for parser in self._parsers.values():
            if parser.can_parse(file_path):
                return parser
        return self._default_parser

    def parse(
        self,
        file_path: str,
        parser_name: Optional[str] = None
    ) -> ParseResult:
        """Parse a file using auto-detection or specified parser.

        Args:
            file_path: Path to the file to parse
            parser_name: Optional name of parser to use

        Returns:
            ParseResult containing parsed data and errors
        """
        from plc_visualizer.models import ParseError

        parser: Optional[BaseParser] = None

        if parser_name:
            parser = self.get_parser(parser_name)
            if not parser:
                return ParseResult(
                    data=None,
                    errors=[ParseError(
                        line=0,
                        content="",
                        reason=f"Parser '{parser_name}' not found"
                    )]
                )
        else:
            parser = self.detect_parser(file_path)

        if not parser:
            return ParseResult(
                data=None,
                errors=[ParseError(
                    line=0,
                    content="",
                    reason="No suitable parser found"
                )]
            )

        return parser.parse(file_path)

    def get_parser_names(self) -> list[str]:
        """Get all registered parser names.

        Returns:
            List of parser names
        """
        return list(self._parsers.keys())


# Singleton instance
parser_registry = ParserRegistry()
