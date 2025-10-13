"""Optimized default parser for SIGNAL_NAME HH:MM:SS value type format."""

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
    
    # Optimized buffer size for file reading (256KB)
    BUFFER_SIZE = 256 * 1024
    
    # Batch size for set operations
    BATCH_SIZE = 1000

    # Pre-compiled regex for HH:MM:SS format with ASCII-only matching
    TIME_PATTERN = re.compile(r'^(\d{1,2}):(\d{2}):(\d{2})$', re.ASCII)
    
    # Pre-built type mapping (avoid recreating dict each time)
    TYPE_MAP = {
        'boolean': SignalType.BOOLEAN,
        'string': SignalType.STRING,
        'integer': SignalType.INTEGER,
    }
    
    # Pre-built boolean value sets for O(1) lookup
    BOOL_TRUE = frozenset(['true', '1'])
    BOOL_FALSE = frozenset(['false', '0'])
    
    # Valid type strings set for fast validation
    VALID_TYPES = frozenset(['boolean', 'string', 'integer'])
    
    # Cache for datetime objects (reuse current date)
    _date_cache = None
    _date_cache_day = None

    def can_parse(self, file_path: str) -> bool:
        """Check if file matches the expected format."""
        try:
            with open(file_path, 'r', encoding='utf-8', buffering=self.BUFFER_SIZE) as f:
                valid_count = 0
                total_count = 0
                
                for line in f:
                    if not line or line.isspace():
                        continue
                    
                    if self._is_valid_format_fast(line):
                        valid_count += 1
                    
                    total_count += 1
                    if total_count >= 5:
                        break
                
                return total_count > 0 and (valid_count / total_count) >= 0.6

        except Exception:
            return False

    def parse(self, file_path: str) -> ParseResult:
        """Parse the entire file with optimized performance."""
        entries: list[LogEntry] = []
        signals: set[str] = set()
        devices: set[str] = set()
        errors: list[ParseError] = []
        
        # Batch accumulators
        signal_batch: list[str] = []
        device_batch: list[str] = []

        try:
            with open(file_path, 'r', encoding='utf-8', buffering=self.BUFFER_SIZE) as f:
                for line_num, line in enumerate(f, start=1):
                    # Skip empty lines efficiently
                    if not line or line.isspace():
                        continue

                    try:
                        entry = self._parse_line_fast(line)
                        entries.append(entry)
                        
                        # Batch set operations
                        signal_batch.append(f"{entry.device_id}::{entry.signal_name}")
                        device_batch.append(entry.device_id)
                        
                        if len(signal_batch) >= self.BATCH_SIZE:
                            signals.update(signal_batch)
                            devices.update(device_batch)
                            signal_batch.clear()
                            device_batch.clear()
                            
                    except ValueError as e:
                        errors.append(ParseError(
                            line=line_num,
                            content=line.rstrip('\n\r'),
                            reason=str(e)
                        ))

                # Flush remaining batches
                if signal_batch:
                    signals.update(signal_batch)
                    devices.update(device_batch)

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
        """Parse file as a stream for memory efficiency."""
        with open(file_path, 'r', encoding='utf-8', buffering=self.BUFFER_SIZE) as f:
            for line in f:
                if not line or line.isspace():
                    continue

                try:
                    entry = self._parse_line_fast(line)
                    yield entry
                except ValueError:
                    continue

    def _is_valid_format_fast(self, line: str) -> bool:
        """Optimized format check with minimal string operations."""
        # Quick length check first
        if len(line) < 20:  # Minimum realistic line length
            return False
        
        # Find positions of spaces (faster than split)
        space_positions = []
        for i, char in enumerate(line):
            if char == ' ':
                space_positions.append(i)
                if len(space_positions) >= 4:
                    break
        
        if len(space_positions) < 4:
            return False
        
        # Extract time part (third field)
        time_start = space_positions[1] + 1
        time_end = space_positions[2]
        time_str = line[time_start:time_end]
        
        if not self.TIME_PATTERN.match(time_str):
            return False
        
        # Extract and check type (fifth field)
        type_start = space_positions[3] + 1
        # Find next space or end of line
        type_end = line.find(' ', type_start)
        if type_end == -1:
            type_end = line.find('\n', type_start)
            if type_end == -1:
                type_end = len(line)
        
        type_str = line[type_start:type_end].strip().lower()
        return type_str in self.VALID_TYPES

    def _parse_line_fast(self, line: str) -> LogEntry:
        """Optimized line parsing: DEVICE_ID SIGNAL_NAME HH:MM:SS value type"""
        # Use split with maxsplit for efficiency
        parts = line.split(maxsplit=4)

        if len(parts) < 5:
            raise ValueError("Invalid format: expected at least 5 parts")

        device_id, signal_name, time_str, value_str, type_str = parts

        # Parse timestamp
        timestamp = self._parse_timestamp_fast(time_str)

        # Parse type using pre-built mapping
        signal_type = self.TYPE_MAP.get(type_str.lower().strip())
        if not signal_type:
            raise ValueError(f"Invalid type: {type_str}")

        # Parse value
        value = self._parse_value_fast(value_str, signal_type)

        return LogEntry(
            device_id=device_id,
            signal_name=signal_name,
            timestamp=timestamp,
            value=value,
            signal_type=signal_type
        )

    def _parse_timestamp_fast(self, time_str: str) -> datetime:
        """Optimized HH:MM:SS timestamp parsing with caching."""
        match = self.TIME_PATTERN.match(time_str)
        if not match:
            raise ValueError(f"Invalid time format: {time_str}")

        h, m, s = int(match.group(1)), int(match.group(2)), int(match.group(3))

        # Validate ranges
        if h > 23 or m > 59 or s > 59:
            raise ValueError(f"Invalid time format: {time_str}")

        # Cache current date to avoid repeated datetime.now() calls
        now = datetime.now()
        current_day = now.day
        
        if self._date_cache_day != current_day:
            self._date_cache = (now.year, now.month, now.day)
            self._date_cache_day = current_day
        
        year, month, day = self._date_cache
        return datetime(year=year, month=month, day=day, hour=h, minute=m, second=s)

    def _parse_value_fast(
        self,
        value_str: str,
        signal_type: SignalType
    ) -> bool | str | int:
        """Optimized value parsing."""
        if signal_type == SignalType.BOOLEAN:
            lower_val = value_str.lower()
            if lower_val in self.BOOL_TRUE:
                return True
            elif lower_val in self.BOOL_FALSE:
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