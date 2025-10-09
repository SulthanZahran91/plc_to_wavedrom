"""Renderer for string and integer signals as state boxes."""

from datetime import datetime

from PyQt6.QtGui import QPainterPath, QColor, QPen, QFont
from PyQt6.QtCore import Qt, QRectF

from plc_visualizer.utils import SignalData
from .base_renderer import BaseRenderer


class StateRenderer(BaseRenderer):
    """Renders string/integer signals as labeled state boxes."""

    def __init__(self, signal_height: float = 60.0):
        super().__init__(signal_height)

        # Colors
        self.box_color = QColor("#2196F3")      # Blue boxes
        self.line_color = QColor("#1976D2")     # Darker blue outline
        self.text_color = QColor("#FFFFFF")     # White text

    def render(
        self,
        signal_data: SignalData,
        time_range: tuple[datetime, datetime],
        width: float,
        y_offset: float = 0.0
    ) -> list[tuple[QPainterPath, object, object]]:
        """Render string/integer signal as state boxes with labels.

        Returns both the box paths and text items (stored separately).
        """
        items = []
        clipped_states = self.clip_states(signal_data.states, time_range)

        if not clipped_states:
            return items

        # Padding (increased for better spacing)
        padding = 12.0
        box_top = y_offset + padding
        box_height = self.signal_height - (2 * padding)

        for state in clipped_states:
            x_start = self.time_to_x(state.start_time, time_range, width)
            x_end = self.time_to_x(state.end_time, time_range, width)

            box_width = x_end - x_start

            # Don't render boxes that are too narrow
            if box_width < 1.0:
                continue

            # Create box path
            box_path = QPainterPath()
            box_path.addRect(x_start, box_top, box_width, box_height)

            # Fill color (semi-transparent)
            fill_color = QColor(self.box_color)
            fill_color.setAlpha(180)
            brush = self.create_brush(fill_color)
            pen = self.create_pen(self.line_color, 1.5)

            items.append((box_path, pen, brush))

        return items

    def get_text_items(
        self,
        signal_data: SignalData,
        time_range: tuple[datetime, datetime],
        width: float,
        y_offset: float = 0.0
    ) -> list[tuple[str, QRectF]]:
        """Get text labels for state boxes.

        Returns:
            List of (text, rect) tuples for rendering text
        """
        text_items = []
        clipped_states = self.clip_states(signal_data.states, time_range)

        if not clipped_states:
            return text_items

        padding = 12.0
        box_top = y_offset + padding
        box_height = self.signal_height - (2 * padding)

        for state in clipped_states:
            x_start = self.time_to_x(state.start_time, time_range, width)
            x_end = self.time_to_x(state.end_time, time_range, width)

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
