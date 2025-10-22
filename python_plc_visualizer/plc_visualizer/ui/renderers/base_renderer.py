"""Base renderer interface for signal visualization."""

from abc import ABC, abstractmethod
from bisect import bisect_left, bisect_right
from datetime import datetime

from PySide6.QtGui import QPainterPath, QPen, QBrush, QColor
from PySide6.QtCore import QRectF

from plc_visualizer.utils import SignalData, SignalState


class BaseRenderer(ABC):
    """Abstract base class for signal renderers.

    Each signal type (boolean, string, integer) has its own renderer
    that knows how to draw that type of signal as a waveform.
    """

    def __init__(self, signal_height: float = 40.0):
        """Initialize the renderer.

        Args:
            signal_height: Height in pixels for the signal track
        """
        self.signal_height = signal_height

    @abstractmethod
    def render(
        self,
        signal_data: SignalData,
        time_range: tuple[datetime, datetime],
        width: float,
        y_offset: float = 0.0
    ) -> list[tuple[QPainterPath, QPen, QBrush]]:
        """Render the signal as graphics items.

        Args:
            signal_data: The signal data to render
            time_range: Visible time range (start, end)
            width: Width in pixels for the waveform
            y_offset: Vertical offset for this signal

        Returns:
            List of (path, pen, brush) tuples to draw
        """
        pass

    def time_to_x(
        self,
        timestamp: datetime,
        time_range: tuple[datetime, datetime],
        width: float
    ) -> float:
        """Convert timestamp to x-coordinate.

        Args:
            timestamp: The timestamp to convert
            time_range: Overall time range (start, end)
            width: Total width in pixels

        Returns:
            X-coordinate in pixels
        """
        start_time, end_time = time_range
        total_duration = (end_time - start_time).total_seconds()

        if total_duration == 0:
            return 0.0

        elapsed = (timestamp - start_time).total_seconds()
        return (elapsed / total_duration) * width

    def create_pen(self, color: QColor, width: float = 2.0) -> QPen:
        """Create a QPen with the given color and width."""
        pen = QPen(color)
        pen.setWidthF(width)
        return pen

    def create_brush(self, color: QColor) -> QBrush:
        """Create a QBrush with the given color."""
        return QBrush(color)

    def clip_states(
        self,
        signal_data: SignalData,
        time_range: tuple[datetime, datetime]
    ) -> list[SignalState]:
        """Clip signal states to the visible time range.

        Args:
            signal_data: Signal data containing states and cached offsets
            time_range: Visible time range (start, end)

        Returns:
            List of SignalState objects covering the visible range
        """
        states = signal_data.states
        if not states or not time_range:
            return []

        start_time, end_time = time_range
        if start_time >= end_time:
            return []

        anchor = signal_data.time_anchor or start_time
        start_seconds = (start_time - anchor).total_seconds()
        end_seconds = (end_time - anchor).total_seconds()

        start_offsets = signal_data.start_offsets
        end_offsets = signal_data.end_offsets

        start_idx = 0
        end_idx = len(states)
        last_value_before_range = None

        if start_offsets and end_offsets:
            start_idx = bisect_right(end_offsets, start_seconds)
            if start_idx > 0:
                last_value_before_range = states[start_idx - 1].value
            if start_idx >= len(states):
                filler = SignalState(start_time=start_time, end_time=end_time, value=states[-1].value)
                filler.start_offset = start_seconds
                filler.end_offset = end_seconds
                return [filler]

            end_idx = bisect_left(start_offsets, end_seconds, lo=start_idx)
            if end_idx <= start_idx:
                end_idx = min(start_idx + 1, len(states))

        candidates = states[start_idx:end_idx]

        clipped: list[SignalState] = []
        for state in candidates:
            segment_start = max(state.start_time, start_time)
            segment_end = min(state.end_time, end_time)

            if segment_end <= segment_start:
                continue

            clipped_state = SignalState(
                start_time=segment_start,
                end_time=segment_end,
                value=state.value
            )
            clipped_state.start_offset = max(state.start_offset, start_seconds)
            clipped_state.end_offset = min(state.end_offset, end_seconds)
            clipped.append(clipped_state)

        if not clipped:
            value = last_value_before_range if last_value_before_range is not None else states[0].value
            filler = SignalState(start_time=start_time, end_time=end_time, value=value)
            filler.start_offset = start_seconds
            filler.end_offset = end_seconds
            return [filler]

        first = clipped[0]
        if first.start_time > start_time:
            filler_value = last_value_before_range if last_value_before_range is not None else first.value
            filler = SignalState(
                start_time=start_time,
                end_time=first.start_time,
                value=filler_value
            )
            filler.start_offset = start_seconds
            filler.end_offset = (first.start_time - anchor).total_seconds()
            clipped.insert(0, filler)

        last = clipped[-1]
        if last.end_time < end_time:
            filler = SignalState(
                start_time=last.end_time,
                end_time=end_time,
                value=last.value
            )
            filler.start_offset = (last.end_time - anchor).total_seconds()
            filler.end_offset = end_seconds
            clipped.append(filler)

        return clipped

    def value_at_time(
        self,
        states: list[SignalState],
        timestamp: datetime
    ):
        """Get the signal value at a specific time."""
        if not states:
            return None

        for state in states:
            if state.start_time <= timestamp < state.end_time:
                return state.value

        if timestamp >= states[-1].end_time:
            return states[-1].value

        return states[0].value
