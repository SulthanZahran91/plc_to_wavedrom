"""Default parser for SIGNAL_NAME HH:MM:SS value type format."""

import re
from datetime import datetime
from typing import Iterator

from plc_visualizer.models import (
    LogEntry,
    ParsedLog,
    ParseError,
    ParseResult,
    SignalType,
)
from .base_parser import BaseParser


class DefaultParser(BaseParser):
    """Parser for format: DEVICE_ID SIGNAL_NAME HH:MM:SS value type

    Example:
        DEVICE_A MOTOR_START 10:30:45 true boolean
        DEVICE_A SENSOR_A 10:30:46 ready string
        DEVICE_B COUNTER_1 10:30:47 100 integer
    """

    name = "default"

    # Regex for HH:MM:SS format
    TIME_PATTERN = re.compile(r'^(\d{1,2}):(\d{2}):(\d{2})$')

    def can_parse(self, file_path: str) -> bool:
        """Check if file matches the expected format.

        Samples first few lines to determine if they match.
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = []
                for _ in range(5):  # Check first 5 non-empty lines
                    line = f.readline()
                    if not line:
                        break
                    if line.strip():
                        lines.append(line.strip())

                if not lines:
                    return False

                matches = sum(1 for line in lines if self._is_valid_format(line))
                return matches / len(lines) >= 0.6  # 60% confidence

        except Exception:
            return False

    def parse(self, file_path: str) -> ParseResult:
        """Parse the entire file.

        For large files, consider using parse_streaming instead.
        """
        entries: list[LogEntry] = []
        signals: set[str] = set()
        devices: set[str] = set()
        errors: list[ParseError] = []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, start=1):
                    line = line.strip()
                    if not line:  # Skip empty lines
                        continue

                    try:
                        entry = self._parse_line(line)
                        entries.append(entry)
                        signals.add(f"{entry.device_id}::{entry.signal_name}")
                        devices.add(entry.device_id)
                    except ValueError as e:
                        errors.append(ParseError(
                            line=line_num,
                            content=line,
                            reason=str(e)
                        ))

        except FileNotFoundError:
            errors.append(ParseError(
                line=0,
                content="",
                reason=f"File not found: {file_path}"
            ))
            return ParseResult(data=None, errors=errors)
        except Exception as e:
            errors.append(ParseError(
                line=0,
                content="",
                reason=f"Failed to read file: {e}"
            ))
            return ParseResult(data=None, errors=errors)

        if not entries:
            return ParseResult(data=None, errors=errors)

        parsed_log = ParsedLog(entries=entries, signals=signals, devices=devices)
        return ParseResult(data=parsed_log, errors=errors)

    def parse_streaming(self, file_path: str) -> Iterator[LogEntry]:
        """Parse file as a stream for memory efficiency.

        Yields entries one at a time without loading entire file.
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                try:
                    entry = self._parse_line(line)
                    yield entry
                except ValueError:
                    # Skip invalid lines in streaming mode
                    continue

    def _is_valid_format(self, line: str) -> bool:
        """Quick check if line matches expected format."""
        parts = line.split()
        if len(parts) < 5:
            return False

        # Check if third part looks like a time
        if not self.TIME_PATTERN.match(parts[2]):
            return False

        # Check if fifth part is a valid type
        return parts[4] in ('boolean', 'string', 'integer')

    def _parse_line(self, line: str) -> LogEntry:
        """Parse a single line: DEVICE_ID SIGNAL_NAME HH:MM:SS value type"""
        parts = line.split(maxsplit=4)

        if len(parts) < 5:
            raise ValueError(
                "Invalid format: expected at least 5 parts "
                "(device, signal, time, value, type)"
            )

        device_id = parts[0]
        signal_name = parts[1]
        time_str = parts[2]
        value_str = parts[3]
        type_str = parts[4]

        # Parse timestamp
        timestamp = self._parse_timestamp(time_str)

        # Validate and parse type
        signal_type = self._parse_type(type_str)

        # Parse value based on type
        value = self._parse_value(value_str, signal_type)

        return LogEntry(
            device_id=device_id,
            signal_name=signal_name,
            timestamp=timestamp,
            value=value,
            signal_type=signal_type
        )

    def _parse_timestamp(self, time_str: str) -> datetime:
        """Parse HH:MM:SS timestamp."""
        match = self.TIME_PATTERN.match(time_str)
        if not match:
            raise ValueError(
                f"Invalid time format: {time_str}. Expected HH:MM:SS"
            )

        hours, minutes, seconds = match.groups()
        h, m, s = int(hours), int(minutes), int(seconds)

        # Validate ranges
        if h > 23 or m > 59 or s > 59:
            raise ValueError(
                f"Invalid time format: {time_str}. Expected HH:MM:SS"
            )

        # Create datetime with today's date
        now = datetime.now()
        return datetime(
            year=now.year,
            month=now.month,
            day=now.day,
            hour=h,
            minute=m,
            second=s
        )

    def _parse_type(self, type_str: str) -> SignalType:
        """Parse and validate signal type."""
        type_map = {
            'boolean': SignalType.BOOLEAN,
            'string': SignalType.STRING,
            'integer': SignalType.INTEGER,
        }

        signal_type = type_map.get(type_str.lower())
        if not signal_type:
            raise ValueError(
                f"Invalid type: {type_str}. "
                "Expected boolean, string, or integer"
            )

        return signal_type

    def _parse_value(
        self,
        value_str: str,
        signal_type: SignalType
    ) -> bool | str | int:
        """Parse value based on its type."""
        if signal_type == SignalType.BOOLEAN:
            lower_val = value_str.lower()
            if lower_val in ('true', '1'):
                return True
            elif lower_val in ('false', '0'):
                return False
            else:
                raise ValueError(f"Invalid boolean value: {value_str}")

        elif signal_type == SignalType.INTEGER:
            try:
                return int(value_str)
            except ValueError:
                raise ValueError(f"Invalid integer value: {value_str}")

        elif signal_type == SignalType.STRING:
            return value_str

        raise ValueError(f"Unknown type: {signal_type}")


# Register the default parser
from .parser_registry import parser_registry
parser_registry.register(DefaultParser(), is_default=True)
