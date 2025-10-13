"""Optimized parser for PLC debug log format with bracketed structure."""

import re
import os
from datetime import datetime
from typing import Iterator, Optional
from multiprocessing import Pool, cpu_count

from plc_visualizer.models import (
    LogEntry,
    ParsedLog,
    ParseError,
    ParseResult,
    SignalType,
)
from .base_parser import BaseParser


class PLCDebugParser(BaseParser):
    """Parser for PLC debug log format.

    Example:
        2025-09-22 13:34:46.877 [Debug] [B1ACNV13301_NND-AZS#3.B1ACNV13301_NND-AZS#3.Belts.B1ACNV13301-102@B13] [OUTPUT2:O_MOVE_IN_ACK] (Boolean) : ON
    """

    name = "plc_debug"
    
    # Optimized buffer size for file reading (256KB)
    BUFFER_SIZE = 256 * 1024
    
    # Batch size for set operations to reduce overhead
    BATCH_SIZE = 1000

    # Pre-compiled regex pattern (class variable - compiled once)
    LOG_PATTERN = re.compile(
        r'^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\.\d{3})\s+'  # Timestamp
        r'\[.*?\]\s+'  # Log level [Debug]
        r'\[.*?([A-Z0-9]+-\d+)(?:@[^\]]+)?\]\s+'  # Device path, extract device ID
        r'\[(INPUT2|OUTPUT2|PARAMETER2):([^\]]+)\]\s+'  # Signal category and name
        r'\((\w+)\)\s*:\s*(.*)$',  # Type and value
        re.ASCII  # Use ASCII-only matching for better performance
    )
    
    # Pre-built type mapping (avoid recreating dict each time)
    TYPE_MAP = {
        'boolean': SignalType.BOOLEAN,
        'string': SignalType.STRING,
        'integer': SignalType.INTEGER,
        'int': SignalType.INTEGER,
        'short': SignalType.INTEGER,
    }
    
    # Pre-built boolean value sets for faster lookup
    BOOL_TRUE = frozenset(['ON', 'TRUE', '1'])
    BOOL_FALSE = frozenset(['OFF', 'FALSE', '0'])

    def can_parse(self, file_path: str) -> bool:
        """Check if file matches the PLC debug log format."""
        try:
            with open(file_path, 'r', encoding='utf-8-sig', buffering=self.BUFFER_SIZE) as f:
                # Check only first 5 non-empty lines for efficiency
                valid_count = 0
                total_count = 0
                
                for line in f:
                    if not line or line.isspace():
                        continue
                    
                    if self.LOG_PATTERN.match(line):
                        valid_count += 1
                    
                    total_count += 1
                    if total_count >= 5:
                        break
                
                return total_count > 0 and (valid_count / total_count) >= 0.6

        except Exception:
            return False

    def parse(self, file_path: str, num_workers: Optional[int] = None) -> ParseResult:
        """Parse the entire file with optimized performance.
        
        Args:
            file_path: Path to the file to parse
            num_workers: Number of worker processes. If None or 1, uses single-threaded.
                        If 0, uses all available CPU cores. If > 1, uses that many workers.
        """
        # Use multiprocessing for large files if num_workers specified
        if num_workers is not None and num_workers != 1:
            return self._parse_parallel(file_path, num_workers)
        
        # Single-threaded parsing
        return self._parse_single_threaded(file_path)
    
    def _parse_single_threaded(self, file_path: str) -> ParseResult:
        """Single-threaded parsing implementation."""
        entries: list[LogEntry] = []
        signals: set[str] = set()
        devices: set[str] = set()
        errors: list[ParseError] = []
        
        # Batch accumulators to reduce set operation overhead
        signal_batch: list[str] = []
        device_batch: list[str] = []

        try:
            with open(file_path, 'r', encoding='utf-8-sig', buffering=self.BUFFER_SIZE) as f:
                for line_num, line in enumerate(f, start=1):
                    # Skip empty lines without creating new strings
                    if not line or line.isspace():
                        continue

                    try:
                        entry = self._parse_line_fast(line)
                        entries.append(entry)
                        
                        # Batch set operations
                        signal_batch.append(f"{entry.device_id}::{entry.signal_name}")
                        device_batch.append(entry.device_id)
                        
                        # Flush batches periodically to avoid excessive memory
                        if len(signal_batch) >= self.BATCH_SIZE:
                            signals.update(signal_batch)
                            devices.update(device_batch)
                            signal_batch.clear()
                            device_batch.clear()
                            
                    except ValueError as e:
                        errors.append(ParseError(
                            line=line_num,
                            content=line.rstrip('\n\r'),  # Only strip trailing newlines
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
    
    def _parse_parallel(self, file_path: str, num_workers: int) -> ParseResult:
        """Parse file using multiple processes for better performance.
        
        Args:
            file_path: Path to the file to parse
            num_workers: Number of worker processes (0 = all CPUs)
        """
        if num_workers == 0:
            num_workers = cpu_count()
        
        # Get file chunks
        chunks = self._get_file_chunks(file_path, num_workers)
        
        if not chunks:
            return ParseResult(
                data=None,
                errors=[ParseError(line=0, content="", reason="Failed to chunk file")]
            )
        
        # Parse chunks in parallel
        with Pool(processes=num_workers) as pool:
            chunk_results = pool.starmap(
                _parse_chunk_worker,
                [(file_path, start, end, self.name) for start, end in chunks]
            )
        
        # Merge results
        all_entries: list[LogEntry] = []
        all_signals: set[str] = set()
        all_devices: set[str] = set()
        all_errors: list[ParseError] = []
        
        for entries, signals, devices, errors in chunk_results:
            all_entries.extend(entries)
            all_signals.update(signals)
            all_devices.update(devices)
            all_errors.extend(errors)
        
        # Sort entries by timestamp for consistency
        all_entries.sort(key=lambda e: e.timestamp)
        
        if not all_entries:
            return ParseResult(data=None, errors=all_errors)
        
        parsed_log = ParsedLog(entries=all_entries, signals=all_signals, devices=all_devices)
        return ParseResult(data=parsed_log, errors=all_errors)
    
    def _get_file_chunks(self, file_path: str, num_chunks: int) -> list[tuple[int, int]]:
        """Divide file into chunks at line boundaries.
        
        Returns:
            List of (start_byte, end_byte) tuples
        """
        try:
            file_size = os.path.getsize(file_path)
            
            if file_size == 0:
                return []
            
            chunk_size = file_size // num_chunks
            chunks = []
            
            with open(file_path, 'rb') as f:
                start = 0
                
                for i in range(num_chunks):
                    if i == num_chunks - 1:
                        # Last chunk goes to end of file
                        end = file_size
                    else:
                        # Seek to approximate chunk boundary
                        f.seek(start + chunk_size)
                        # Read until next newline to ensure we're at a line boundary
                        f.readline()
                        end = f.tell()
                    
                    if start < end:
                        chunks.append((start, end))
                    start = end
            
            return chunks
            
        except Exception:
            return []

    def parse_streaming(self, file_path: str) -> Iterator[LogEntry]:
        """Parse file as a stream for memory efficiency."""
        with open(file_path, 'r', encoding='utf-8-sig', buffering=self.BUFFER_SIZE) as f:
            for line in f:
                # Skip empty lines efficiently
                if not line or line.isspace():
                    continue

                try:
                    entry = self._parse_line_fast(line)
                    yield entry
                except ValueError:
                    # Skip invalid lines in streaming mode
                    continue

    def _parse_line_fast(self, line: str) -> LogEntry:
        """Optimized line parsing with minimal string operations."""
        match = self.LOG_PATTERN.match(line)
        
        if not match:
            raise ValueError("Line does not match PLC debug log format")

        # Extract all groups at once (faster than individual access)
        timestamp_str, device_id, _, signal_name, type_str, value_str = match.groups()

        # Parse timestamp (most expensive operation, unavoidable)
        timestamp = self._parse_timestamp_fast(timestamp_str)

        # Parse type using pre-built mapping
        signal_type = self.TYPE_MAP.get(type_str.lower())
        if not signal_type:
            raise ValueError(f"Invalid type: {type_str}")

        # Parse value with minimal string operations
        value = self._parse_value_fast(value_str, signal_type)

        return LogEntry(
            device_id=device_id,
            signal_name=signal_name,
            timestamp=timestamp,
            value=value,
            signal_type=signal_type
        )

    def _parse_timestamp_fast(self, timestamp_str: str) -> datetime:
        """Optimized timestamp parsing."""
        try:
            # strptime is already quite optimized in Python
            return datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S.%f")
        except ValueError:
            raise ValueError(f"Invalid timestamp format: {timestamp_str}")

    def _parse_value_fast(
        self,
        value_str: str,
        signal_type: SignalType
    ) -> bool | str | int:
        """Optimized value parsing with minimal overhead."""
        if signal_type == SignalType.BOOLEAN:
            # Strip only once and convert to uppercase
            val = value_str.strip().upper()
            if val in self.BOOL_TRUE:
                return True
            elif val in self.BOOL_FALSE:
                return False
            else:
                raise ValueError(f"Invalid boolean value: {value_str}")

        elif signal_type == SignalType.INTEGER:
            # int() is already optimized, just strip whitespace
            try:
                return int(value_str.strip())
            except ValueError:
                raise ValueError(f"Invalid integer value: {value_str}")

        elif signal_type == SignalType.STRING:
            # Return as-is, strip only trailing whitespace
            return value_str.strip()

        raise ValueError(f"Unknown type: {signal_type}")


def _parse_chunk_worker(
    file_path: str,
    start_byte: int,
    end_byte: int,
    parser_name: str
) -> tuple[list[LogEntry], set[str], set[str], list[ParseError]]:
    """Worker function for parallel chunk parsing.
    
    Must be at module level for multiprocessing.
    
    Args:
        file_path: Path to the file
        start_byte: Starting byte position
        end_byte: Ending byte position
        parser_name: Name of parser (for recreating instance)
    
    Returns:
        Tuple of (entries, signals, devices, errors)
    """
    # Create parser instance (can't pickle class methods easily)
    parser = PLCDebugParser()
    
    entries: list[LogEntry] = []
    signals: set[str] = set()
    devices: set[str] = set()
    errors: list[ParseError] = []
    
    try:
        with open(file_path, 'r', encoding='utf-8-sig', buffering=parser.BUFFER_SIZE) as f:
            f.seek(start_byte)
            
            # Calculate approximate line number for error reporting
            # (not exact but close enough)
            approx_line_start = start_byte // 100  # Assume ~100 chars per line
            
            bytes_read = 0
            line_num = approx_line_start
            
            while bytes_read < (end_byte - start_byte):
                line = f.readline()
                if not line:
                    break
                
                bytes_read += len(line.encode('utf-8'))
                line_num += 1
                
                if not line or line.isspace():
                    continue
                
                try:
                    entry = parser._parse_line_fast(line)
                    entries.append(entry)
                    signals.add(f"{entry.device_id}::{entry.signal_name}")
                    devices.add(entry.device_id)
                except ValueError as e:
                    errors.append(ParseError(
                        line=line_num,
                        content=line.rstrip('\n\r'),
                        reason=str(e)
                    ))
    
    except Exception as e:
        errors.append(ParseError(
            line=0,
            content="",
            reason=f"Chunk parsing error: {e}"
        ))
    
    return entries, signals, devices, errors


# Register the PLC debug parser
from .parser_registry import parser_registry
parser_registry.register(PLCDebugParser())