"""Grid lines for waveform viewer."""

from datetime import datetime, timedelta

from PyQt6.QtWidgets import QGraphicsItem
from PyQt6.QtGui import QPainter, QColor, QPen
from PyQt6.QtCore import QRectF, Qt


class GridLinesItem(QGraphicsItem):
    """Graphics item for drawing vertical grid lines at time tick positions."""

    LABEL_WIDTH = 180.0  # Match time axis and signal label width
    GRID_LEFT_MARGIN = 10.0  # Match signal waveform margin

    def __init__(
        self,
        time_range: tuple[datetime, datetime],
        width: float,
        height: float
    ):
        super().__init__()

        self.time_range = time_range
        self.width = width
        self.height = height

        # Styling - subtle gray lines
        self.grid_color = QColor("#E8E8E8")

        # Make sure grid lines are behind other items
        self.setZValue(-1)

    def boundingRect(self) -> QRectF:
        """Return the bounding rectangle."""
        return QRectF(0, 0, self.width, self.height)

    def paint(self, painter: QPainter, option, widget=None):
        """Paint vertical grid lines."""
        start_time, end_time = self.time_range
        total_duration = (end_time - start_time).total_seconds()

        if total_duration == 0:
            return

        # Available width for timeline (after label area and margin)
        timeline_start_x = self.LABEL_WIDTH + self.GRID_LEFT_MARGIN
        timeline_width = self.width - timeline_start_x

        # Use same tick interval calculation as TimeAxisItem
        num_ticks = 10
        tick_interval_seconds = self._calculate_tick_interval(total_duration, num_ticks)

        # Draw vertical grid lines
        pen = QPen(self.grid_color)
        pen.setWidth(1)
        pen.setStyle(Qt.PenStyle.DotLine)  # Dotted lines for subtlety
        painter.setPen(pen)

        current_time = start_time
        while current_time <= end_time:
            # Calculate x position (offset by LABEL_WIDTH + margin)
            elapsed = (current_time - start_time).total_seconds()
            x = timeline_start_x + (elapsed / total_duration) * timeline_width

            # Draw vertical grid line
            painter.drawLine(int(x), 0, int(x), int(self.height))

            # Move to next tick
            current_time += timedelta(seconds=tick_interval_seconds)

    def _calculate_tick_interval(self, duration_seconds: float, target_ticks: int) -> float:
        """Calculate appropriate tick interval in seconds.

        Same logic as TimeAxisItem to keep grid aligned with time ticks.
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

    def update_dimensions(self, width: float, height: float):
        """Update dimensions and redraw."""
        self.width = width
        self.height = height
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
