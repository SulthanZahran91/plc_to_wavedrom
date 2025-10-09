"""Time axis display for waveform viewer."""

from datetime import datetime, timedelta

from PyQt6.QtWidgets import QGraphicsItem
from PyQt6.QtGui import QPainter, QColor, QPen, QFont
from PyQt6.QtCore import QRectF, Qt


class TimeAxisItem(QGraphicsItem):
    """Graphics item for displaying the time axis with labels."""

    LABEL_WIDTH = 180.0  # Match signal label width
    TIMELINE_LEFT_MARGIN = 10.0  # Match signal waveform margin

    def __init__(self, time_range: tuple[datetime, datetime], width: float, height: float = 30.0):
        super().__init__()

        self.time_range = time_range
        self.width = width
        self.height = height

        # Styling
        self.bg_color = QColor("#F5F5F5")
        self.line_color = QColor("#757575")
        self.text_color = QColor("#212121")

    def boundingRect(self) -> QRectF:
        """Return the bounding rectangle."""
        return QRectF(0, 0, self.width, self.height)

    def paint(self, painter: QPainter, option, widget=None):
        """Paint the time axis."""
        # Draw background
        painter.fillRect(self.boundingRect(), self.bg_color)

        # Draw vertical separator after label area
        pen = QPen(self.line_color)
        pen.setWidth(1)
        painter.setPen(pen)
        painter.drawLine(
            int(self.LABEL_WIDTH),
            0,
            int(self.LABEL_WIDTH),
            int(self.height)
        )

        # Draw bottom border
        painter.drawLine(0, int(self.height - 1), int(self.width), int(self.height - 1))

        # Calculate time labels
        start_time, end_time = self.time_range
        total_duration = (end_time - start_time).total_seconds()

        if total_duration == 0:
            return

        # Available width for timeline (after label area and margin)
        timeline_start_x = self.LABEL_WIDTH + self.TIMELINE_LEFT_MARGIN
        timeline_width = self.width - timeline_start_x

        # Determine appropriate tick interval
        num_ticks = 10  # Target number of ticks
        tick_interval_seconds = self._calculate_tick_interval(total_duration, num_ticks)

        # Draw ticks and labels
        font = QFont("Arial", 9)
        painter.setFont(font)
        painter.setPen(self.text_color)

        current_time = start_time
        while current_time <= end_time:
            # Calculate x position (offset by LABEL_WIDTH + margin)
            elapsed = (current_time - start_time).total_seconds()
            x = timeline_start_x + (elapsed / total_duration) * timeline_width

            # Draw tick mark
            painter.setPen(self.line_color)
            painter.drawLine(int(x), int(self.height - 10), int(x), int(self.height - 1))

            # Draw time label
            time_str = current_time.strftime("%H:%M:%S")
            painter.setPen(self.text_color)
            painter.drawText(
                int(x - 30), 5, 60, 15,
                Qt.AlignmentFlag.AlignCenter,
                time_str
            )

            # Move to next tick
            current_time += timedelta(seconds=tick_interval_seconds)

    def _calculate_tick_interval(self, duration_seconds: float, target_ticks: int) -> float:
        """Calculate appropriate tick interval in seconds.

        Args:
            duration_seconds: Total duration in seconds
            target_ticks: Target number of ticks

        Returns:
            Tick interval in seconds
        """
        raw_interval = duration_seconds / target_ticks

        # Round to nice intervals
        if raw_interval < 1:
            return 1
        elif raw_interval < 5:
            return 5
        elif raw_interval < 10:
            return 10
        elif raw_interval < 30:
            return 30
        elif raw_interval < 60:
            return 60
        elif raw_interval < 300:
            return 300
        elif raw_interval < 600:
            return 600
        else:
            return 3600

    def update_time_range(self, time_range: tuple[datetime, datetime]):
        """Update the time range and redraw."""
        self.time_range = time_range
        self.update()

    def update_width(self, width: float):
        """Update the width and redraw."""
        self.width = width
        self.prepareGeometryChange()
        self.update()

    def set_time_range(self, start: datetime, end: datetime):
        """Update the visible time range.

        Args:
            start: New start time
            end: New end time
        """
        self.time_range = (start, end)
        self.update()
