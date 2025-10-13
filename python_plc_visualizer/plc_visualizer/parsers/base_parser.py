"""Base parser interface for PLC log files."""

from abc import ABC, abstractmethod
from typing import Iterator, Optional

from plc_visualizer.models import LogEntry, ParseResult


class BaseParser(ABC):
    """Abstract base class for log file parsers.

    All parsers must inherit from this class and implement the required methods.
    This enables a pluggable parser architecture where new formats can be added
    without modifying existing code.
    """

    name: str = "base"

    @abstractmethod
    def parse(self, file_path: str, num_workers: Optional[int] = None) -> ParseResult:
        """Parse a complete log file.

        Args:
            file_path: Path to the log file to parse
            num_workers: Number of worker processes for parallel parsing.
                        None or 1 = single-threaded
                        0 = use all available CPU cores
                        >1 = use specified number of workers
                        Default is None for backward compatibility.

        Returns:
            ParseResult containing parsed data and any errors
        """
        pass

    def can_parse(self, file_path: str) -> bool:
        """Check if this parser can handle the given file.

        This method can inspect the file to determine if it matches
        the expected format. Default implementation returns True.

        Args:
            file_path: Path to the file to check

        Returns:
            True if this parser can handle the file
        """
        return True

    def parse_streaming(self, file_path: str) -> Iterator[LogEntry]:
        """Parse a log file as a stream (generator).

        This method is optional but recommended for large files.
        It allows processing files that don't fit in memory.

        Args:
            file_path: Path to the log file to parse

        Yields:
            LogEntry objects as they are parsed
        """
        # Default implementation uses parse() and yields all entries
        result = self.parse(file_path)
        if result.data:
            yield from result.data.entries