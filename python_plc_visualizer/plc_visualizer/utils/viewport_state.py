"""Viewport state management for time navigation and zoom."""

from datetime import datetime, timedelta
from typing import Optional, Tuple
from PyQt6.QtCore import QObject, pyqtSignal


class ViewportState(QObject):
    """Manages the viewport state for time range and zoom level.

    Signals:
        time_range_changed: Emitted when the visible time range changes
        zoom_level_changed: Emitted when the zoom level changes
    """

    time_range_changed = pyqtSignal(datetime, datetime)
    zoom_level_changed = pyqtSignal(float)

    def __init__(self, parent=None):
        super().__init__(parent)

        # Full log time range
        self._full_start: Optional[datetime] = None
        self._full_end: Optional[datetime] = None

        # Current visible time range
        self._visible_start: Optional[datetime] = None
        self._visible_end: Optional[datetime] = None

        # Zoom level (1.0 = full view, higher = zoomed in)
        self._zoom_level: float = 1.0

        # Zoom constraints
        self.min_zoom = 1.0
        self.max_zoom = 1000.0

    def set_full_time_range(self, start: datetime, end: datetime):
        """Set the full time range of the loaded log.

        Args:
            start: Start time of the log
            end: End time of the log
        """
        if start >= end:
            raise ValueError("Start time must be before end time")

        self._full_start = start
        self._full_end = end
        # self._visible_start = start
        # self._visible_end = end
        self._zoom_level = 1.0

        # self.time_range_changed.emit(self._visible_start, self._visible_end)
        # self.zoom_level_changed.emit(self._zoom_level)

    @property
    def full_time_range(self) -> Optional[Tuple[datetime, datetime]]:
        """Get the full time range."""
        if self._full_start is None or self._full_end is None:
            return None
        return (self._full_start, self._full_end)

    @property
    def visible_time_range(self) -> Optional[Tuple[datetime, datetime]]:
        """Get the current visible time range."""
        if self._visible_start is None or self._visible_end is None:
            return None
        return (self._visible_start, self._visible_end)

    @property
    def zoom_level(self) -> float:
        """Get the current zoom level."""
        return self._zoom_level

    @property
    def full_duration(self) -> Optional[timedelta]:
        """Get the full time duration."""
        if self._full_start is None or self._full_end is None:
            return None
        return self._full_end - self._full_start

    @property
    def visible_duration(self) -> Optional[timedelta]:
        """Get the visible time duration."""
        if self._visible_start is None or self._visible_end is None:
            return None
        return self._visible_end - self._visible_start

    def zoom_in(self, factor: float = 2.0):
        """Zoom in by the given factor.

        Args:
            factor: Zoom factor (default 2.0 = double the zoom)
        """
        new_zoom = min(self._zoom_level * factor, self.max_zoom)
        self._apply_zoom(new_zoom)

    def zoom_out(self, factor: float = 2.0):
        """Zoom out by the given factor.

        Args:
            factor: Zoom factor (default 2.0 = half the zoom)
        """
        new_zoom = max(self._zoom_level / factor, self.min_zoom)
        self._apply_zoom(new_zoom)

    def set_zoom_level(self, zoom: float):
        """Set the zoom level directly.

        Args:
            zoom: Desired zoom level (1.0 to max_zoom)
        """
        zoom = max(self.min_zoom, min(zoom, self.max_zoom))
        self._apply_zoom(zoom)

    def reset_zoom(self):
        """Reset zoom to show the full time range."""
        if self._full_start is None or self._full_end is None:
            return

        self._visible_start = self._full_start
        self._visible_end = self._full_end
        self._zoom_level = 1.0

        self.time_range_changed.emit(self._visible_start, self._visible_end)
        self.zoom_level_changed.emit(self._zoom_level)

    def _apply_zoom(self, new_zoom: float):
        """Apply a new zoom level, maintaining the center point.

        Args:
            new_zoom: The new zoom level to apply
        """
        if self._full_start is None or self._full_end is None:
            return
        if self._visible_start is None or self._visible_end is None:
            return

        if new_zoom == self._zoom_level:
            return

        # Calculate the center of the current visible range
        visible_duration = self._visible_end - self._visible_start
        center = self._visible_start + visible_duration / 2

        # Calculate new duration based on zoom level
        full_duration = self._full_end - self._full_start
        new_duration = full_duration / new_zoom

        # Calculate new start and end, centered on the same point
        new_start = center - new_duration / 2
        new_end = center + new_duration / 2

        # Constrain to full range
        if new_start < self._full_start:
            new_start = self._full_start
            new_end = new_start + new_duration
        if new_end > self._full_end:
            new_end = self._full_end
            new_start = new_end - new_duration

        # Ensure we don't exceed bounds (can happen at max zoom)
        new_start = max(new_start, self._full_start)
        new_end = min(new_end, self._full_end)

        self._visible_start = new_start
        self._visible_end = new_end
        self._zoom_level = new_zoom

        self.time_range_changed.emit(self._visible_start, self._visible_end)
        self.zoom_level_changed.emit(self._zoom_level)

    def pan(self, delta_seconds: float):
        """Pan the viewport by a time delta.

        Args:
            delta_seconds: Time delta in seconds (positive = forward, negative = backward)
        """
        if self._visible_start is None or self._visible_end is None:
            return
        if self._full_start is None or self._full_end is None:
            return

        delta = timedelta(seconds=delta_seconds)
        new_start = self._visible_start + delta
        new_end = self._visible_end + delta

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
            self.time_range_changed.emit(self._visible_start, self._visible_end)

    def set_time_range(self, start: datetime, end: datetime):
        """Set the visible time range directly.

        Args:
            start: New visible start time
            end: New visible end time
        """
        if self._full_start is None or self._full_end is None:
            return

        if start >= end:
            start, end = end, start
        elif start == end:
            start -= timedelta(seconds=1)


        # Constrain to full range
        start = max(start, self._full_start)
        end = min(end, self._full_end)

        # Calculate new zoom level
        full_duration = self._full_end - self._full_start
        visible_duration = end - start
        if visible_duration <= timedelta(0):
            # fix zero/negative span
            end = start + timedelta(microseconds=1)
            visible_duration = end - start
            
        new_zoom = full_duration / visible_duration

        self._visible_start = start
        self._visible_end = end
        self._zoom_level = new_zoom

        self.time_range_changed.emit(self._visible_start, self._visible_end)
        self.zoom_level_changed.emit(self._zoom_level)

    def jump_to_time(self, target_time: datetime):
        """Jump to a specific time, centering it in the viewport.

        Args:
            target_time: Time to jump to
        """
        if self._visible_start is None or self._visible_end is None:
            return
        if self._full_start is None or self._full_end is None:
            return

        # Constrain target to full range
        target_time = max(target_time, self._full_start)
        target_time = min(target_time, self._full_end)

        # Calculate new range centered on target
        visible_duration = self._visible_end - self._visible_start
        new_start = target_time - visible_duration / 2
        new_end = target_time + visible_duration / 2

        # Constrain to full range
        if new_start < self._full_start:
            new_start = self._full_start
            new_end = new_start + visible_duration
        if new_end > self._full_end:
            new_end = self._full_end
            new_start = new_end - visible_duration

        # Final bounds check
        new_start = max(new_start, self._full_start)
        new_end = min(new_end, self._full_end)

        if new_start != self._visible_start or new_end != self._visible_end:
            self._visible_start = new_start
            self._visible_end = new_end
            self.time_range_changed.emit(self._visible_start, self._visible_end)
