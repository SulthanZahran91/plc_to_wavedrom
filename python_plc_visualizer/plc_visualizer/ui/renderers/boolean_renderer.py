"""Renderer for boolean signals as square waves."""

from datetime import datetime

from PySide6.QtGui import QPainterPath, QColor
from PySide6.QtCore import Qt

from plc_visualizer.utils import SignalData, SignalState
from .base_renderer import BaseRenderer


class BooleanRenderer(BaseRenderer):
    """Renders boolean signals as high/low square waves."""

    def __init__(self, signal_height: float = 60.0):
        super().__init__(signal_height)

        # Colors
        self.high_color = QColor("#4CAF50")  # Green for high
        self.low_color = QColor("#9E9E9E")   # Gray for low
        self.line_color = QColor("#212121")  # Dark line
        self.transition_color = QColor("#FB8C00")  # Orange for transition markers

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
        """Render boolean signal as square wave.

        High = top of track, Low = bottom of track
        """
        items = []
        if clipped_states is None:
            clipped_states = self.clip_states(signal_data, time_range)

        if not clipped_states:
            return items

        # Padding from top/bottom of track (increased for better spacing)
        high_y = y_offset + self.padding
        low_y = y_offset + self.signal_height - self.padding

        anchor = signal_data.time_anchor or time_range[0]
        range_start_offset = (time_range[0] - anchor).total_seconds()
        range_duration = max((time_range[1] - time_range[0]).total_seconds(), 1e-12)
        pixel_factor = width / range_duration

        # Create the waveform path
        path = QPainterPath()
        first_state = clipped_states[0]
        first_x = max(0.0, min(width, (first_state.start_offset - range_start_offset) * pixel_factor))
        current_y = high_y if first_state.value else low_y
        current_x = first_x

        path.moveTo(first_x, current_y)

        fill_path = QPainterPath()

        for state in clipped_states:
            x_start = max(0.0, min(width, (state.start_offset - range_start_offset) * pixel_factor))
            x_end = max(0.0, min(width, (state.end_offset - range_start_offset) * pixel_factor))

            state_y = high_y if state.value else low_y

            if x_start > current_x:
                path.lineTo(x_start, current_y)

            if state_y != current_y:
                path.lineTo(x_start, state_y)

            path.lineTo(x_end, state_y)

            current_x = x_end
            current_y = state_y

        # Add filled regions for high states
        for state in clipped_states:
            if state.value:  # High state
                x_start = max(0.0, min(width, (state.start_offset - range_start_offset) * pixel_factor))
                x_end = max(0.0, min(width, (state.end_offset - range_start_offset) * pixel_factor))

                # Create filled rectangle for high state
                box_width = x_end - x_start

                if box_width <= 0:
                    continue

                fill_path.addRect(x_start, high_y, box_width, low_y - high_y)

                # Semi-transparent green fill
        if not fill_path.isEmpty():
            fill_color = QColor(self.high_color)
            fill_color.setAlpha(50)
            brush = self.create_brush(fill_color)
            items.append((fill_path, self.create_pen(Qt.GlobalColor.transparent, 0), brush))

        # Add the waveform line
        pen = self.create_pen(self.line_color, 2.0)
        items.append((path, pen, None))

        return items
