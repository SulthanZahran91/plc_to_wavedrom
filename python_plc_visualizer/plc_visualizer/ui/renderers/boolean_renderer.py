"""Renderer for boolean signals as square waves."""

from datetime import datetime

from PyQt6.QtGui import QPainterPath, QColor
from PyQt6.QtCore import Qt

from plc_visualizer.utils import SignalData
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
        y_offset: float = 0.0
    ) -> list[tuple[QPainterPath, object, object]]:
        """Render boolean signal as square wave.

        High = top of track, Low = bottom of track
        """
        items = []
        clipped_states = self.clip_states(signal_data.states, time_range)

        if not clipped_states:
            return items

        # Padding from top/bottom of track (increased for better spacing)
        high_y = y_offset + self.padding
        low_y = y_offset + self.signal_height - self.padding

        # Create the waveform path
        path = QPainterPath()
        first_state = clipped_states[0]
        current_y = high_y if first_state.value else low_y
        current_x = 0.0

        path.moveTo(0.0, current_y)

        for state in clipped_states:
            x_start = self.time_to_x(state.start_time, time_range, width)
            x_end = self.time_to_x(state.end_time, time_range, width)

            state_y = high_y if state.value else low_y

            if x_start > current_x:
                path.lineTo(x_start, current_y)

            if state_y != current_y:
                path.lineTo(x_start, state_y)

            path.lineTo(x_end, state_y)

            current_x = x_end
            current_y = state_y

        # Add the waveform line
        pen = self.create_pen(self.line_color, 2.0)
        items.append((path, pen, None))

        # Add filled regions for high states
        for state in clipped_states:
            if state.value:  # High state
                x_start = self.time_to_x(state.start_time, time_range, width)
                x_end = self.time_to_x(state.end_time, time_range, width)

                # Create filled rectangle for high state
                box_width = x_end - x_start

                if box_width <= 0:
                    continue

                fill_path = QPainterPath()
                fill_path.addRect(
                    x_start,
                    high_y,
                    box_width,
                    low_y - high_y
                )

                # Semi-transparent green fill
                fill_color = QColor(self.high_color)
                fill_color.setAlpha(50)
                brush = self.create_brush(fill_color)
                pen = self.create_pen(Qt.GlobalColor.transparent, 0)

                items.append((fill_path, pen, brush))

        return items
