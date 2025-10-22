"""Data processing utilities for waveform visualization."""

from array import array
from dataclasses import dataclass, field
from datetime import datetime
from typing import Union

from plc_visualizer.models import LogEntry, ParsedLog, SignalType


@dataclass
class SignalState:
    """Represents a state/value over a time period."""
    start_time: datetime
    end_time: datetime
    value: Union[bool, str, int]
    start_offset: float = field(default=0.0, repr=False)
    end_offset: float = field(default=0.0, repr=False)

    @property
    def duration(self) -> float:
        """Duration in seconds."""
        return (self.end_time - self.start_time).total_seconds()


@dataclass
class SignalData:
    """Processed signal data for visualization.

    Memory optimization: entries are NOT stored here to avoid duplication.
    States are computed lazily when needed for rendering.
    """
    name: str
    device_id: str
    key: str
    signal_type: SignalType
    states: list[SignalState] = field(default_factory=list)
    time_anchor: datetime | None = None
    start_offsets: array = field(default_factory=lambda: array("d"), repr=False)
    end_offsets: array = field(default_factory=lambda: array("d"), repr=False)
    _entries_count: int = 0  # Track count for stats without storing entries

    @property
    def has_transitions(self) -> bool:
        """Check if signal has any transitions."""
        return len(self.states) > 1

    @property
    def display_label(self) -> str:
        """Combined label for device and signal."""
        return f"{self.device_id} -> {self.name}"

    @property
    def entry_count(self) -> int:
        """Number of entries for this signal (for stats)."""
        return self._entries_count

    def build_time_index(self, anchor: datetime):
        """Pre-compute numeric offsets for fast viewport clipping."""
        self.time_anchor = anchor

        if not self.states:
            self.start_offsets = array("d")
            self.end_offsets = array("d")
            return

        # States already carry offsets relative to the global start; however, if
        # the provided anchor differs we recompute.
        start_offsets = array("d")
        end_offsets = array("d")
        for state in self.states:
            start_seconds = (state.start_time - anchor).total_seconds()
            end_seconds = (state.end_time - anchor).total_seconds()

            state.start_offset = start_seconds
            state.end_offset = end_seconds

            start_offsets.append(start_seconds)
            end_offsets.append(end_seconds)

        self.start_offsets = start_offsets
        self.end_offsets = end_offsets

    def clear_states(self):
        """Clear computed states to free memory when signal is hidden.

        This is a memory optimization - states can be recomputed on-demand
        when the signal becomes visible again.
        """
        self.states.clear()
        self.start_offsets = array("d")
        self.end_offsets = array("d")


def group_by_signal(parsed_log: ParsedLog) -> dict[tuple[str, str], list[LogEntry]]:
    """Group log entries by (device, signal) pair.

    Args:
        parsed_log: ParsedLog containing entries to group

    Returns:
        Dictionary mapping (device_id, signal_name) to their entries (sorted by time)
    """
    grouped: dict[tuple[str, str], list[LogEntry]] = {}

    for entry in parsed_log.entries:
        key = (entry.device_id, entry.signal_name)
        if key not in grouped:
            grouped[key] = []
        grouped[key].append(entry)

    # Sort entries by timestamp for each signal
    for key in grouped:
        grouped[key].sort(key=lambda e: e.timestamp)

    return grouped


def calculate_signal_states(
    entries: list[LogEntry],
    time_range: tuple[datetime, datetime]
) -> list[SignalState]:
    """Calculate signal states with durations.

    Args:
        entries: List of log entries for a signal (must be sorted by time)
        time_range: Overall time range (start, end)

    Returns:
        List of SignalState objects representing value changes over time
    """
    if not entries:
        return []

    states = []
    overall_start, overall_end = time_range

    for i, entry in enumerate(entries):
        start_time = entry.timestamp

        # End time is either the next entry's timestamp or the overall end
        if i < len(entries) - 1:
            end_time = entries[i + 1].timestamp
        else:
            end_time = overall_end

        state = SignalState(
            start_time=start_time,
            end_time=end_time,
            value=entry.value
        )
        state.start_offset = (start_time - overall_start).total_seconds()
        state.end_offset = (end_time - overall_start).total_seconds()
        states.append(state)

    return states


def process_signals_for_waveform(
    parsed_log: ParsedLog,
    lazy: bool = False
) -> list[SignalData]:
    """Process parsed log data into signal data ready for visualization.

    Memory optimization: Entries are NOT duplicated in SignalData.
    States can be computed lazily to save memory.

    Args:
        parsed_log: ParsedLog containing all entries
        lazy: If True, don't compute states immediately (saves memory)

    Returns:
        List of SignalData objects, one per signal
    """
    grouped = group_by_signal(parsed_log)
    signal_data_list = []
    range_start = parsed_log.time_range[0] if parsed_log.time_range else None

    for (device_id, signal_name), entries in grouped.items():
        if not entries:
            continue

        # Get signal type from first entry
        signal_type = entries[0].signal_type

        # Calculate states (unless lazy mode)
        states = [] if lazy else calculate_signal_states(entries, parsed_log.time_range)

        signal_data = SignalData(
            name=signal_name,
            device_id=device_id,
            key=f"{device_id}::{signal_name}",
            signal_type=signal_type,
            states=states,
            _entries_count=len(entries)  # Store count, not entries
        )

        if not lazy:
            anchor = range_start or entries[0].timestamp
            signal_data.build_time_index(anchor)

        signal_data_list.append(signal_data)

    # Sort by device then signal name for consistent display
    signal_data_list.sort(key=lambda s: (s.device_id, s.name))

    return signal_data_list


def compute_signal_states(
    signal_data: SignalData,
    parsed_log: ParsedLog
):
    """Lazily compute states for a signal from the original ParsedLog.

    This allows on-demand state calculation without storing duplicate entries.

    Args:
        signal_data: SignalData object to populate with states
        parsed_log: Original parsed log containing all entries
    """
    # Extract entries for this signal from the main entry list
    entries = [
        entry for entry in parsed_log.entries
        if entry.device_id == signal_data.device_id
        and entry.signal_name == signal_data.name
    ]

    if not entries:
        return

    # Sort by timestamp
    entries.sort(key=lambda e: e.timestamp)

    # Calculate states
    signal_data.states = calculate_signal_states(entries, parsed_log.time_range)

    # Build time index
    anchor = parsed_log.time_range[0] if parsed_log.time_range else entries[0].timestamp
    signal_data.build_time_index(anchor)
    signal_data._entries_count = len(entries)
