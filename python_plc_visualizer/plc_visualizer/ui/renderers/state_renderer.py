"""Renderer for string and integer signals as state boxes."""

from datetime import datetime

from PySide6.QtGui import QPainterPath, QColor, QPen, QFont
from PySide6.QtCore import Qt, QRectF

from plc_visualizer.utils import SignalData, SignalState
from .base_renderer import BaseRenderer


class StateRenderer(BaseRenderer):
    """Renders string/integer signals as labeled state boxes."""

    def __init__(self, signal_height: float = 60.0):
        super().__init__(signal_height)

        # Colors
        self.box_color = QColor("#2196F3")      # Blue boxes
        self.line_color = QColor("#1976D2")     # Darker blue outline
        self.text_color = QColor("#FFFFFF")     # White text
        self.transition_color = QColor("#FFCA28")  # Amber markers for transitions

        # Layout
        self.padding = 12.0

    def render(
        self,
        signal_data: SignalData,
        time_range: tuple[datetime, datetime],
        width: float,
        y_offset: float = 0.0,
        clipped_states: list[SignalState] | None = None
    ) -> list[tuple[QPainterPath, object, object]]:
        """Render string/integer signal as state boxes with labels.

        Returns both the box paths and text items (stored separately).
        """
        items = []
        if clipped_states is None:
            clipped_states = self.clip_states(signal_data, time_range)

        if not clipped_states:
            return items

        # Padding (increased for better spacing)
        box_top = y_offset + self.padding
        box_height = self.signal_height - (2 * self.padding)
        anchor = signal_data.time_anchor or time_range[0]
        range_start_offset = (time_range[0] - anchor).total_seconds()
        range_duration = max((time_range[1] - time_range[0]).total_seconds(), 1e-12)
        pixel_factor = width / range_duration

        boxes_path = QPainterPath()

        for state in clipped_states:
            x_start = max(0.0, min(width, (state.start_offset - range_start_offset) * pixel_factor))
            x_end = max(0.0, min(width, (state.end_offset - range_start_offset) * pixel_factor))

            box_width = x_end - x_start

            # Don't render boxes that are too narrow
            if box_width < 1.0:
                continue

            boxes_path.addRect(x_start, box_top, box_width, box_height)

        if boxes_path.isEmpty():
            return items

        fill_color = QColor(self.box_color)
        fill_color.setAlpha(180)
        brush = self.create_brush(fill_color)
        pen = self.create_pen(self.line_color, 1.5)
        items.append((boxes_path, pen, brush))

        return items

    def get_text_items(
        self,
        signal_data: SignalData,
        time_range: tuple[datetime, datetime],
        width: float,
        y_offset: float = 0.0,
        clipped_states: list[SignalState] | None = None
    ) -> list[tuple[str, QRectF]]:
        """Get text labels for state boxes.

        Returns:
            List of (text, rect) tuples for rendering text
        """
        text_items = []
        if clipped_states is None:
            clipped_states = self.clip_states(signal_data, time_range)

        if not clipped_states:
            return text_items

        box_top = y_offset + self.padding
        box_height = self.signal_height - (2 * self.padding)
        anchor = signal_data.time_anchor or time_range[0]
        range_start_offset = (time_range[0] - anchor).total_seconds()
        range_duration = max((time_range[1] - time_range[0]).total_seconds(), 1e-12)
        pixel_factor = width / range_duration

        for state in clipped_states:
            x_start = max(0.0, min(width, (state.start_offset - range_start_offset) * pixel_factor))
            x_end = max(0.0, min(width, (state.end_offset - range_start_offset) * pixel_factor))

            box_width = x_end - x_start

            # Only show text if box is wide enough
            if box_width < 30.0:
                continue

            # Prepare text
            text = str(state.value)

            # Truncate long text
            if len(text) > 15:
                text = text[:12] + "..."

            # Create rectangle for text positioning
            text_rect = QRectF(x_start, box_top, box_width, box_height)

            text_items.append((text, text_rect))

        return text_items
