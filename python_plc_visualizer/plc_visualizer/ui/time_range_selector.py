"""Time range selector widget with draggable handles."""

from datetime import datetime
from typing import Optional
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, pyqtSignal, QRectF, QPointF
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QFont


class TimeRangeSelector(QWidget):
    """Visual time range selector with draggable handles.

    Signals:
        time_range_changed: Emitted when the selected range changes (start, end)
    """

    time_range_changed = pyqtSignal(datetime, datetime)

    def __init__(self, parent=None):
        super().__init__(parent)

        # Time range
        self._full_start: Optional[datetime] = None
        self._full_end: Optional[datetime] = None
        self._visible_start: Optional[datetime] = None
        self._visible_end: Optional[datetime] = None

        # Interaction state
        self._dragging_start = False
        self._dragging_end = False
        self._dragging_viewport = False
        self._drag_start_x = 0

        # UI configuration
        self.setMinimumHeight(60)
        self.setMaximumHeight(80)
        self.setCursor(Qt.CursorShape.ArrowCursor)

        # Colors
        self.background_color = QColor("#f5f5f5")
        self.full_range_color = QColor("#e0e0e0")
        self.visible_range_color = QColor("#64B5F6")
        self.handle_color = QColor("#2196F3")
        self.text_color = QColor("#333333")

        # Handle size
        self.handle_width = 8
        self.handle_height = 40

    def set_full_time_range(self, start: datetime, end: datetime):
        """Set the full time range.

        Args:
            start: Start time of the full range
            end: End time of the full range
        """
        self._full_start = start
        self._full_end = end
        self._visible_start = start
        self._visible_end = end
        self.update()

    def set_visible_time_range(self, start: datetime, end: datetime):
        """Set the visible time range.

        Args:
            start: Start time of the visible range
            end: End time of the visible range
        """
        if self._full_start is None or self._full_end is None:
            return

        # Constrain to full range
        start = max(start, self._full_start)
        end = min(end, self._full_end)

        self._visible_start = start
        self._visible_end = end
        self.update()

    def _time_to_x(self, time: datetime) -> float:
        """Convert a time to an x coordinate.

        Args:
            time: Time to convert

        Returns:
            X coordinate in widget space
        """
        if self._full_start is None or self._full_end is None:
            return 0

        margin = 20
        usable_width = self.width() - 2 * margin

        total_duration = (self._full_end - self._full_start).total_seconds()
        if total_duration <= 0:
            return margin

        time_offset = (time - self._full_start).total_seconds()
        position = time_offset / total_duration

        return margin + position * usable_width

    def _x_to_time(self, x: float) -> datetime:
        """Convert an x coordinate to a time.

        Args:
            x: X coordinate in widget space

        Returns:
            Corresponding time
        """
        if self._full_start is None or self._full_end is None:
            return datetime.now()

        margin = 20
        usable_width = self.width() - 2 * margin

        position = (x - margin) / usable_width
        position = max(0.0, min(1.0, position))

        total_duration = (self._full_end - self._full_start).total_seconds()
        from datetime import timedelta
        return self._full_start + timedelta(seconds=position * total_duration)

    def paintEvent(self, event):
        """Paint the time range selector."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw background
        painter.fillRect(self.rect(), self.background_color)

        if self._full_start is None or self._full_end is None:
            return

        margin = 20
        bar_height = 20
        bar_y = (self.height() - bar_height) // 2

        # Draw full range bar
        full_rect = QRectF(
            margin,
            bar_y,
            self.width() - 2 * margin,
            bar_height
        )
        painter.fillRect(full_rect, self.full_range_color)

        # Draw visible range
        if self._visible_start is not None and self._visible_end is not None:
            start_x = self._time_to_x(self._visible_start)
            end_x = self._time_to_x(self._visible_end)

            visible_rect = QRectF(
                start_x,
                bar_y,
                end_x - start_x,
                bar_height
            )
            painter.fillRect(visible_rect, self.visible_range_color)

            # Draw handles
            handle_y = bar_y - (self.handle_height - bar_height) // 2

            # Start handle
            start_handle = QRectF(
                start_x - self.handle_width // 2,
                handle_y,
                self.handle_width,
                self.handle_height
            )
            painter.fillRect(start_handle, self.handle_color)

            # End handle
            end_handle = QRectF(
                end_x - self.handle_width // 2,
                handle_y,
                self.handle_width,
                self.handle_height
            )
            painter.fillRect(end_handle, self.handle_color)

        # Draw time labels
        painter.setPen(QPen(self.text_color))
        font = QFont()
        font.setPointSize(9)
        painter.setFont(font)

        # Full range labels
        start_label = self._full_start.strftime("%H:%M:%S")
        end_label = self._full_end.strftime("%H:%M:%S")

        painter.drawText(
            QPointF(margin, self.height() - 5),
            start_label
        )
        painter.drawText(
            QPointF(self.width() - margin - 60, self.height() - 5),
            end_label
        )

        # Visible range labels
        if self._visible_start is not None and self._visible_end is not None:
            visible_start_label = self._visible_start.strftime("%H:%M:%S")
            visible_end_label = self._visible_end.strftime("%H:%M:%S")

            start_x = self._time_to_x(self._visible_start)
            end_x = self._time_to_x(self._visible_end)

            # Draw visible start label above bar
            painter.drawText(
                QPointF(start_x - 30, bar_y - 5),
                visible_start_label
            )

            # Draw visible end label above bar
            painter.drawText(
                QPointF(end_x - 30, bar_y - 5),
                visible_end_label
            )

    def mousePressEvent(self, event):
        """Handle mouse press events."""
        if self._visible_start is None or self._visible_end is None:
            return

        x = event.position().x()
        start_x = self._time_to_x(self._visible_start)
        end_x = self._time_to_x(self._visible_end)

        # Check if clicking on start handle
        if abs(x - start_x) <= self.handle_width:
            self._dragging_start = True
            self._drag_start_x = x
            self.setCursor(Qt.CursorShape.SizeHorCursor)
            event.accept()
            return

        # Check if clicking on end handle
        if abs(x - end_x) <= self.handle_width:
            self._dragging_end = True
            self._drag_start_x = x
            self.setCursor(Qt.CursorShape.SizeHorCursor)
            event.accept()
            return

        # Check if clicking inside visible range (drag viewport)
        if start_x <= x <= end_x:
            self._dragging_viewport = True
            self._drag_start_x = x
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return

    def mouseMoveEvent(self, event):
        """Handle mouse move events."""
        if self._full_start is None or self._full_end is None:
            return
        if self._visible_start is None or self._visible_end is None:
            return

        x = event.position().x()

        if self._dragging_start:
            # Drag start handle
            new_start = self._x_to_time(x)
            new_start = max(new_start, self._full_start)
            new_start = min(new_start, self._visible_end)

            if new_start != self._visible_start:
                self._visible_start = new_start
                self.update()
                self.time_range_changed.emit(self._visible_start, self._visible_end)

        elif self._dragging_end:
            # Drag end handle
            new_end = self._x_to_time(x)
            new_end = max(new_end, self._visible_start)
            new_end = min(new_end, self._full_end)

            if new_end != self._visible_end:
                self._visible_end = new_end
                self.update()
                self.time_range_changed.emit(self._visible_start, self._visible_end)

        elif self._dragging_viewport:
            # Drag entire viewport
            delta_x = x - self._drag_start_x
            self._drag_start_x = x

            # Convert delta to time
            margin = 20
            usable_width = self.width() - 2 * margin
            total_duration = (self._full_end - self._full_start).total_seconds()
            delta_seconds = (delta_x / usable_width) * total_duration

            from datetime import timedelta
            delta_time = timedelta(seconds=delta_seconds)

            new_start = self._visible_start + delta_time
            new_end = self._visible_end + delta_time

            # Constrain to full range
            if new_start < self._full_start:
                diff = self._full_start - new_start
                new_start = self._full_start
                new_end = new_end + diff

            if new_end > self._full_end:
                diff = new_end - self._full_end
                new_end = self._full_end
                new_start = new_start - diff

            # Final bounds check
            new_start = max(new_start, self._full_start)
            new_end = min(new_end, self._full_end)

            if new_start != self._visible_start or new_end != self._visible_end:
                self._visible_start = new_start
                self._visible_end = new_end
                self.update()
                self.time_range_changed.emit(self._visible_start, self._visible_end)

        else:
            # Update cursor based on hover position
            start_x = self._time_to_x(self._visible_start)
            end_x = self._time_to_x(self._visible_end)

            if abs(x - start_x) <= self.handle_width or abs(x - end_x) <= self.handle_width:
                self.setCursor(Qt.CursorShape.SizeHorCursor)
            elif start_x <= x <= end_x:
                self.setCursor(Qt.CursorShape.OpenHandCursor)
            else:
                self.setCursor(Qt.CursorShape.ArrowCursor)

    def mouseReleaseEvent(self, event):
        """Handle mouse release events."""
        self._dragging_start = False
        self._dragging_end = False
        self._dragging_viewport = False
        self.setCursor(Qt.CursorShape.ArrowCursor)
