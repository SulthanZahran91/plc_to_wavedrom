"""Chunked log data structure for memory-efficient large file handling."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, Dict, Set, List, Tuple
from collections import OrderedDict

from .data_types import LogEntry


@dataclass
class TimeChunk:
    """A time-based chunk of log entries.

    Represents entries within a specific time window.
    """
    start_time: datetime
    end_time: datetime
    entries: List[LogEntry] = field(default_factory=list)
    signals: Set[str] = field(default_factory=set)
    devices: Set[str] = field(default_factory=set)

    @property
    def entry_count(self) -> int:
        """Number of entries in this chunk."""
        return len(self.entries)

    @property
    def duration(self) -> timedelta:
        """Duration of this chunk."""
        return self.end_time - self.start_time

    def __post_init__(self):
        """Calculate signals and devices if not provided."""
        if not self.signals and self.entries:
            self.signals = {
                f"{entry.device_id}::{entry.signal_name}"
                for entry in self.entries
            }

        if not self.devices and self.entries:
            self.devices = {entry.device_id for entry in self.entries}


class ChunkedParsedLog:
    """Memory-efficient log storage using time-based chunks.

    Designed for gigabyte-scale files by keeping only relevant time windows in memory.
    Chunks are loaded on-demand and evicted using LRU policy.

    Features:
    - Time-window based queries
    - Automatic chunk loading/unloading
    - LRU cache for accessed chunks
    - Prefetching for smooth panning

    Args:
        chunk_duration: Duration of each chunk in seconds (default: 300 = 5 minutes)
        max_chunks_in_memory: Maximum chunks to keep in memory (default: 5)
    """

    def __init__(
        self,
        time_range: Optional[Tuple[datetime, datetime]] = None,
        chunk_duration_seconds: float = 300.0,  # 5 minutes per chunk
        max_chunks_in_memory: int = 5,
    ):
        self.full_time_range = time_range
        self.chunk_duration = timedelta(seconds=chunk_duration_seconds)
        self.max_chunks_in_memory = max_chunks_in_memory

        # Chunk storage: {chunk_start_time: TimeChunk}
        # Uses OrderedDict for LRU tracking (most recently accessed = last)
        self._chunks: OrderedDict[datetime, TimeChunk] = OrderedDict()

        # Global metadata (aggregated from all seen chunks)
        self._all_signals: Set[str] = set()
        self._all_devices: Set[str] = set()
        self._total_entry_count: int = 0

        # Chunk loader callback: (start_time, end_time) -> TimeChunk
        # This will be set by the chunk manager
        self._chunk_loader: Optional[callable] = None

    def set_chunk_loader(self, loader: callable):
        """Set the callback function for loading chunks on-demand.

        Args:
            loader: Function(start_time, end_time) -> TimeChunk
        """
        self._chunk_loader = loader

    def _get_chunk_key(self, timestamp: datetime) -> datetime:
        """Calculate which chunk a timestamp belongs to.

        Args:
            timestamp: Timestamp to find chunk for

        Returns:
            Chunk start time (aligned to chunk boundaries)
        """
        if not self.full_time_range:
            return timestamp

        full_start, _ = self.full_time_range

        # Calculate time offset from start
        offset = timestamp - full_start
        offset_seconds = offset.total_seconds()
        chunk_seconds = self.chunk_duration.total_seconds()

        # Round down to nearest chunk boundary
        chunk_index = int(offset_seconds // chunk_seconds)
        chunk_start = full_start + timedelta(seconds=chunk_index * chunk_seconds)

        return chunk_start

    def _ensure_chunk_loaded(self, chunk_key: datetime) -> Optional[TimeChunk]:
        """Ensure a chunk is loaded, fetching it if necessary.

        Args:
            chunk_key: Chunk start time

        Returns:
            TimeChunk or None if loading failed
        """
        # Check if already loaded
        if chunk_key in self._chunks:
            # Move to end (mark as most recently used)
            self._chunks.move_to_end(chunk_key)
            return self._chunks[chunk_key]

        # Need to load chunk
        if not self._chunk_loader:
            return None

        # Calculate chunk time range
        chunk_end = chunk_key + self.chunk_duration

        # Load chunk
        try:
            chunk = self._chunk_loader(chunk_key, chunk_end)

            # Add to cache
            self._chunks[chunk_key] = chunk

            # Update global metadata
            self._all_signals.update(chunk.signals)
            self._all_devices.update(chunk.devices)
            self._total_entry_count += chunk.entry_count

            # Evict old chunks if over limit
            evicted_count = 0
            while len(self._chunks) > self.max_chunks_in_memory:
                # Remove least recently used (first item)
                old_key, old_chunk = self._chunks.popitem(last=False)
                evicted_count += 1
                # Note: We don't decrement _total_entry_count as it tracks
                # total entries seen, not currently in memory

            if evicted_count > 0:
                print(f"♻️  Evicted {evicted_count} old chunk(s) (LRU cache limit: {self.max_chunks_in_memory})")

            return chunk

        except Exception as e:
            print(f"❌ Error loading chunk {chunk_key}: {e}")
            return None

    def get_entries_in_range(
        self,
        start_time: datetime,
        end_time: datetime
    ) -> List[LogEntry]:
        """Get all entries within a time range.

        Automatically loads required chunks and filters entries.

        Args:
            start_time: Start of time range
            end_time: End of time range

        Returns:
            List of LogEntry objects in the time range
        """
        if not self.full_time_range:
            return []

        # Find all chunks that overlap with requested range
        chunk_keys = self._get_overlapping_chunks(start_time, end_time)

        entries = []
        for chunk_key in chunk_keys:
            chunk = self._ensure_chunk_loaded(chunk_key)
            if not chunk:
                continue

            # Filter entries in this chunk to the requested range
            for entry in chunk.entries:
                if start_time <= entry.timestamp < end_time:
                    entries.append(entry)

        # Sort by timestamp
        entries.sort(key=lambda e: e.timestamp)

        return entries

    def _get_overlapping_chunks(
        self,
        start_time: datetime,
        end_time: datetime
    ) -> List[datetime]:
        """Get list of chunk keys that overlap with time range.

        Args:
            start_time: Start of time range
            end_time: End of time range

        Returns:
            List of chunk start times
        """
        if not self.full_time_range:
            return []

        chunk_keys = []

        # Start at first chunk overlapping start_time
        current_chunk_key = self._get_chunk_key(start_time)

        # Iterate through chunks until we pass end_time
        while current_chunk_key < end_time:
            chunk_end = current_chunk_key + self.chunk_duration

            # Check if this chunk overlaps with requested range
            if chunk_end > start_time:
                chunk_keys.append(current_chunk_key)

            # Move to next chunk
            current_chunk_key += self.chunk_duration

        return chunk_keys

    def prefetch_chunks(self, start_time: datetime, end_time: datetime):
        """Prefetch chunks in a time range (for smooth panning).

        Args:
            start_time: Start of time range to prefetch
            end_time: End of time range to prefetch
        """
        chunk_keys = self._get_overlapping_chunks(start_time, end_time)
        for chunk_key in chunk_keys:
            self._ensure_chunk_loaded(chunk_key)

    def clear_cache(self):
        """Clear all cached chunks from memory."""
        self._chunks.clear()

    @property
    def signals(self) -> Set[str]:
        """Get all signals seen across all loaded chunks."""
        return self._all_signals

    @property
    def devices(self) -> Set[str]:
        """Get all devices seen across all loaded chunks."""
        return self._all_devices

    @property
    def time_range(self) -> Optional[Tuple[datetime, datetime]]:
        """Get the full time range of the log."""
        return self.full_time_range

    @property
    def entry_count(self) -> int:
        """Get total number of entries seen (not necessarily in memory)."""
        return self._total_entry_count

    @property
    def signal_count(self) -> int:
        """Number of unique signals."""
        return len(self._all_signals)

    @property
    def device_count(self) -> int:
        """Number of unique devices."""
        return len(self._all_devices)

    @property
    def chunks_in_memory(self) -> int:
        """Number of chunks currently in memory."""
        return len(self._chunks)
