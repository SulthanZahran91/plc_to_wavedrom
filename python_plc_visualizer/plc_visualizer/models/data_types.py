"""Core data types for PLC log parsing and visualization."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Union


class SignalType(Enum):
    """Types of signals in PLC logs."""
    BOOLEAN = "boolean"
    STRING = "string"
    INTEGER = "integer"


@dataclass
class LogEntry:
    """A single entry in a PLC log file."""
    device_id: str
    signal_name: str
    timestamp: datetime
    value: Union[bool, str, int]
    signal_type: SignalType

    def __repr__(self) -> str:
        return (
            f"LogEntry(device={self.device_id}, signal={self.signal_name}, "
            f"time={self.timestamp.strftime('%H:%M:%S')}, "
            f"value={self.value}, type={self.signal_type.value})"
        )


@dataclass
class ParsedLog:
    """Result of successfully parsing a log file."""
    entries: list[LogEntry]
    signals: set[str] = field(default_factory=set)
    devices: set[str] = field(default_factory=set)
    time_range: tuple[datetime, datetime] | None = None

    def __post_init__(self):
        """Calculate signals and time_range if not provided."""
        if not self.signals:
            self.signals = {
                f"{entry.device_id}::{entry.signal_name}"
                for entry in self.entries
            }

        if not self.devices:
            self.devices = {entry.device_id for entry in self.entries}

        if not self.time_range and self.entries:
            timestamps = [entry.timestamp for entry in self.entries]
            self.time_range = (min(timestamps), max(timestamps))

    @property
    def entry_count(self) -> int:
        """Total number of log entries."""
        return len(self.entries)

    @property
    def signal_count(self) -> int:
        """Number of unique signals."""
        return len(self.signals)

    @property
    def device_count(self) -> int:
        """Number of unique devices."""
        return len(self.devices)


@dataclass
class ParseError:
    """An error encountered during log parsing."""
    line: int
    content: str
    reason: str
    file_path: str | None = None

    def __repr__(self) -> str:
        file_info = f", file={self.file_path}" if self.file_path else ""
        return f"ParseError(line={self.line}{file_info}, reason={self.reason})"


@dataclass
class ParseResult:
    """Complete result of parsing a log file, including errors."""
    data: ParsedLog | None
    errors: list[ParseError] = field(default_factory=list)

    @property
    def success(self) -> bool:
        """Whether parsing was successful (has data)."""
        return self.data is not None

    @property
    def has_errors(self) -> bool:
        """Whether any parsing errors occurred."""
        return len(self.errors) > 0

    @property
    def error_count(self) -> int:
        """Number of parsing errors."""
        return len(self.errors)
