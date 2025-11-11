"""Chunk manager for loading time-windowed log data on-demand."""

from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Callable

from plc_visualizer.models import TimeChunk, ChunkedParsedLog
from plc_visualizer.parsers import parser_registry


class ChunkManager:
    """Manages loading and caching of time-windowed log chunks.

    Responsibilities:
    - Parse specific time windows from log files on-demand
    - Provide chunks to ChunkedParsedLog
    - Handle parser selection and error handling
    - Prefetch adjacent chunks for smooth panning

    Args:
        file_path: Path to the log file
        chunked_log: ChunkedParsedLog instance to manage
    """

    def __init__(
        self,
        file_path: str,
        chunked_log: ChunkedParsedLog
    ):
        self.file_path = Path(file_path)
        self.chunked_log = chunked_log

        # Detect parser for this file
        self.parser = parser_registry.detect_parser(str(self.file_path))

        if not self.parser:
            raise ValueError(f"No parser found for file: {self.file_path}")

        # Set ourselves as the chunk loader
        self.chunked_log.set_chunk_loader(self._load_chunk)

        # Prefetch configuration
        self.prefetch_enabled = True
        self.prefetch_chunks_ahead = 1  # Prefetch 1 chunk ahead when panning

    def _load_chunk(self, start_time: datetime, end_time: datetime) -> TimeChunk:
        """Load a time chunk from the log file.

        This is called by ChunkedParsedLog when a chunk is needed.

        Args:
            start_time: Start of time window
            end_time: End of time window

        Returns:
            TimeChunk with entries in the specified time range
        """
        # Loading indicator
        if self.chunked_log.chunks_in_memory == 0:
            print(f" Loading initial chunk: {start_time.strftime('%H:%M:%S')} - {end_time.strftime('%H:%M:%S')}")

        # Check if parser supports time-windowed parsing
        if hasattr(self.parser, 'parse_time_window'):
            # Use optimized time-window parsing
            result = self.parser.parse_time_window(
                str(self.file_path),
                start_time,
                end_time
            )

            if result.success and result.data:
                # Convert ParsedLog to TimeChunk
                return TimeChunk(
                    start_time=start_time,
                    end_time=end_time,
                    entries=result.data.entries,
                    signals=result.data.signals,
                    devices=result.data.devices
                )

        # Fallback: Parse entire file and filter
        # This is inefficient but ensures compatibility
        result = self.parser.parse(str(self.file_path))

        if not result.success or not result.data:
            # Return empty chunk on error
            return TimeChunk(
                start_time=start_time,
                end_time=end_time,
                entries=[],
                signals=set(),
                devices=set()
            )

        # Filter entries to time window
        filtered_entries = [
            entry for entry in result.data.entries
            if start_time <= entry.timestamp < end_time
        ]

        # Build chunk
        chunk = TimeChunk(
            start_time=start_time,
            end_time=end_time,
            entries=filtered_entries
        )

        return chunk

    def get_entries_in_range(
        self,
        start_time: datetime,
        end_time: datetime,
        with_prefetch: bool = True
    ) -> list:
        """Get entries in a time range, with optional prefetching.

        Args:
            start_time: Start of time range
            end_time: End of time range
            with_prefetch: If True, prefetch adjacent chunks for smooth panning

        Returns:
            List of LogEntry objects
        """
        # Get entries from chunked log
        entries = self.chunked_log.get_entries_in_range(start_time, end_time)

        # Prefetch adjacent chunks if enabled
        if with_prefetch and self.prefetch_enabled:
            self._prefetch_adjacent(start_time, end_time)

        return entries

    def _prefetch_adjacent(self, start_time: datetime, end_time: datetime):
        """Prefetch chunks adjacent to the current time range.

        Args:
            start_time: Current start time
            end_time: Current end time
        """
        # Prefetch chunks ahead (in the direction user is likely to pan)
        duration = end_time - start_time
        prefetch_count = 0

        for i in range(1, self.prefetch_chunks_ahead + 1):
            # Prefetch forward
            prefetch_start = start_time + (duration * i)
            prefetch_end = end_time + (duration * i)

            # Check if within bounds
            if self.chunked_log.full_time_range:
                _, full_end = self.chunked_log.full_time_range
                if prefetch_start < full_end:
                    self.chunked_log.prefetch_chunks(prefetch_start, prefetch_end)
                    prefetch_count += 1

            # Prefetch backward
            prefetch_start = start_time - (duration * i)
            prefetch_end = end_time - (duration * i)

            # Check if within bounds
            if self.chunked_log.full_time_range:
                full_start, _ = self.chunked_log.full_time_range
                if prefetch_end > full_start:
                    self.chunked_log.prefetch_chunks(prefetch_start, prefetch_end)
                    prefetch_count += 1

        if prefetch_count > 0:
            print(f" Prefetched {prefetch_count} adjacent chunk(s) | Chunks in memory: {self.chunked_log.chunks_in_memory}")

    def clear_cache(self):
        """Clear all cached chunks."""
        self.chunked_log.clear_cache()

    @property
    def chunks_in_memory(self) -> int:
        """Number of chunks currently in memory."""
        return self.chunked_log.chunks_in_memory


def create_chunked_log(
    file_path: str,
    time_range: tuple[datetime, datetime],
    chunk_duration_seconds: float = 300.0,
    max_chunks_in_memory: int = 5
) -> tuple[ChunkedParsedLog, ChunkManager]:
    """Factory function to create a chunked log with manager.

    Args:
        file_path: Path to log file
        time_range: Full time range of the log
        chunk_duration_seconds: Duration of each chunk (default: 5 minutes)
        max_chunks_in_memory: Maximum chunks to keep in memory (default: 5)

    Returns:
        Tuple of (ChunkedParsedLog, ChunkManager)
    """
    chunked_log = ChunkedParsedLog(
        time_range=time_range,
        chunk_duration_seconds=chunk_duration_seconds,
        max_chunks_in_memory=max_chunks_in_memory
    )

    manager = ChunkManager(file_path, chunked_log)

    return chunked_log, manager
