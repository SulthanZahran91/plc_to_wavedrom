"""Base renderer interface for signal visualization."""

from abc import ABC, abstractmethod
from datetime import datetime

from PyQt6.QtGui import QPainterPath, QPen, QBrush, QColor
from PyQt6.QtCore import QRectF

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
        states: list[SignalState],
        time_range: tuple[datetime, datetime]
    ) -> list[SignalState]:
        """Clip signal states to the visible time range.

        Args:
            states: Full list of signal states
            time_range: Visible time range (start, end)

        Returns:
            List of SignalState objects covering the visible range
        """
        start_time, end_time = time_range

        if start_time >= end_time or not states:
            return []

        clipped: list[SignalState] = []
        last_value_before_range = None

        for state in states:
            if state.end_time <= start_time:
                last_value_before_range = state.value
                continue

            if state.start_time >= end_time:
                break

            segment_start = max(state.start_time, start_time)
            segment_end = min(state.end_time, end_time)

            if segment_end <= segment_start:
                continue

            clipped.append(SignalState(
                start_time=segment_start,
                end_time=segment_end,
                value=state.value
            ))

        if not clipped:
            value = last_value_before_range
            if value is None:
                value = states[0].value

            return [SignalState(
                start_time=start_time,
                end_time=end_time,
                value=value
            )]

        first = clipped[0]
        if first.start_time > start_time:
            filler_value = last_value_before_range if last_value_before_range is not None else first.value
            clipped.insert(0, SignalState(
                start_time=start_time,
                end_time=first.start_time,
                value=filler_value
            ))

        last = clipped[-1]
        if last.end_time < end_time:
            clipped.append(SignalState(
                start_time=last.end_time,
                end_time=end_time,
                value=last.value
            ))

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
