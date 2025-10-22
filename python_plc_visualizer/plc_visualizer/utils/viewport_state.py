"""Viewport state management for time navigation and zoom."""

from datetime import datetime, timedelta
from typing import Optional, Tuple
from PySide6.QtCore import QObject, Signal


class ViewportState(QObject):
    """Manages the viewport state for time range and visible duration.

    Signals:
        time_range_changed: Emitted when the visible time range changes
        duration_changed: Emitted when the visible duration changes (in seconds)
    """

    time_range_changed = Signal(datetime, datetime)
    duration_changed = Signal(float)  # Emits visible duration in seconds

    # Duration constraints
    MAX_VISIBLE_DURATION_SECONDS = 300.0  # 5 minutes maximum visible window
    MIN_VISIBLE_DURATION_SECONDS = 0.001  # 1 millisecond minimum (max zoom in)

    def __init__(self, parent=None):
        super().__init__(parent)

        # Full log time range
        self._full_start: Optional[datetime] = None
        self._full_end: Optional[datetime] = None

        # Current visible time range
        self._visible_start: Optional[datetime] = None
        self._visible_end: Optional[datetime] = None

        # Visible duration in seconds (replaces zoom_level)
        self._visible_duration_seconds: float = 300.0

        # Duration constraints (will be updated when data is loaded)
        self.min_visible_duration = self.MIN_VISIBLE_DURATION_SECONDS  # Minimum window (max zoom in)
        self.max_visible_duration = self.MAX_VISIBLE_DURATION_SECONDS  # Maximum window (max zoom out)

    def _update_duration_constraints(self):
        """Calculate and update duration constraints based on loaded data.

        This prevents over-compression of data when zoomed out and sets reasonable limits.

        Example: If full duration is 1 hour:
        - max_visible_duration = 5 minutes (prevents over-compression)
        - min_visible_duration = 1 millisecond (allows detailed inspection)

        If full duration is less than MAX_VISIBLE_DURATION, allow viewing the full range.
        """
        if self._full_start is None or self._full_end is None:
            self.max_visible_duration = self.MAX_VISIBLE_DURATION_SECONDS
            self.min_visible_duration = self.MIN_VISIBLE_DURATION_SECONDS
            return

        full_duration_seconds = (self._full_end - self._full_start).total_seconds()
        if full_duration_seconds <= 0:
            self.max_visible_duration = self.MAX_VISIBLE_DURATION_SECONDS
            self.min_visible_duration = self.MIN_VISIBLE_DURATION_SECONDS
            return

        # Max visible duration: smaller of full duration or MAX_VISIBLE_DURATION
        self.max_visible_duration = min(full_duration_seconds, self.MAX_VISIBLE_DURATION_SECONDS)

        # Min visible duration: ensure we can zoom in to at least 1ms
        self.min_visible_duration = self.MIN_VISIBLE_DURATION_SECONDS

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

        # Update duration constraints based on data
        self._update_duration_constraints()

        # Initialize visible range to max visible duration (most zoomed out view allowed)
        full_duration_seconds = (self._full_end - self._full_start).total_seconds()
        initial_duration_seconds = min(full_duration_seconds, self.max_visible_duration)

        self._visible_duration_seconds = initial_duration_seconds
        self._visible_start = start
        self._visible_end = start + timedelta(seconds=initial_duration_seconds)

        # self.time_range_changed.emit(self._visible_start, self._visible_end)
        # self.duration_changed.emit(self._visible_duration_seconds)

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
    def visible_duration_seconds(self) -> float:
        """Get the current visible duration in seconds."""
        return self._visible_duration_seconds

    @property
    def zoom_level(self) -> float:
        """Get the current zoom level (for backward compatibility).

        Calculated as full_duration / visible_duration.
        """
        if self._full_start is None or self._full_end is None:
            return 1.0
        full_duration_seconds = (self._full_end - self._full_start).total_seconds()
        if full_duration_seconds <= 0 or self._visible_duration_seconds <= 0:
            return 1.0
        return full_duration_seconds / self._visible_duration_seconds

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
        """Zoom in by decreasing the visible duration.

        Args:
            factor: Factor to divide duration by (default 2.0 = show half the time)
        """
        new_duration = max(self._visible_duration_seconds / factor, self.min_visible_duration)
        self._apply_duration_change(new_duration)

    def zoom_out(self, factor: float = 2.0):
        """Zoom out by increasing the visible duration.

        Args:
            factor: Factor to multiply duration by (default 2.0 = show twice the time)
        """
        new_duration = min(self._visible_duration_seconds * factor, self.max_visible_duration)
        self._apply_duration_change(new_duration)

    def set_visible_duration(self, duration_seconds: float):
        """Set the visible duration directly.

        Args:
            duration_seconds: Desired visible duration in seconds
        """
        duration_seconds = max(self.min_visible_duration, min(duration_seconds, self.max_visible_duration))
        self._apply_duration_change(duration_seconds)

    def set_zoom_level(self, zoom: float):
        """Set the zoom level (for backward compatibility).

        Converts zoom level to visible duration and applies it.

        Args:
            zoom: Desired zoom level (higher = more zoomed in)
        """
        if self._full_start is None or self._full_end is None:
            return
        full_duration_seconds = (self._full_end - self._full_start).total_seconds()
        if full_duration_seconds <= 0:
            return

        # Calculate visible duration from zoom level
        duration_seconds = full_duration_seconds / zoom
        self.set_visible_duration(duration_seconds)

    def reset_zoom(self):
        """Reset to show maximum allowed time range (most zoomed out)."""
        if self._full_start is None or self._full_end is None:
            return

        # Reset to max visible duration (or full duration if smaller)
        full_duration_seconds = (self._full_end - self._full_start).total_seconds()
        reset_duration = min(full_duration_seconds, self.max_visible_duration)

        self._visible_duration_seconds = reset_duration
        self._visible_start = self._full_start
        self._visible_end = self._full_start + timedelta(seconds=reset_duration)

        self.time_range_changed.emit(self._visible_start, self._visible_end)
        self.duration_changed.emit(self._visible_duration_seconds)

    def _apply_duration_change(self, new_duration_seconds: float):
        """Apply a new visible duration, maintaining the center point.

        Args:
            new_duration_seconds: The new visible duration in seconds
        """
        if self._full_start is None or self._full_end is None:
            return
        if self._visible_start is None or self._visible_end is None:
            return

        if abs(new_duration_seconds - self._visible_duration_seconds) < 0.0001:
            return  # No significant change

        # Calculate the center of the current visible range
        visible_duration = self._visible_end - self._visible_start
        center = self._visible_start + visible_duration / 2

        # Calculate new start and end, centered on the same point
        new_duration = timedelta(seconds=new_duration_seconds)
        new_start = center - new_duration / 2
        new_end = center + new_duration / 2

        # Constrain to full range
        if new_start < self._full_start:
            new_start = self._full_start
            new_end = new_start + new_duration
        if new_end > self._full_end:
            new_end = self._full_end
            new_start = new_end - new_duration

        # Ensure we don't exceed bounds
        new_start = max(new_start, self._full_start)
        new_end = min(new_end, self._full_end)

        # Update actual duration based on constrained range
        actual_duration = (new_end - new_start).total_seconds()

        self._visible_start = new_start
        self._visible_end = new_end
        self._visible_duration_seconds = actual_duration

        self.time_range_changed.emit(self._visible_start, self._visible_end)
        self.duration_changed.emit(self._visible_duration_seconds)

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

        start = max(start, self._full_start)
        end = min(end, self._full_end)

        full_duration_seconds = (self._full_end - self._full_start).total_seconds()
        max_allowed = min(self.max_visible_duration, full_duration_seconds)
        min_allowed = min(self.min_visible_duration, full_duration_seconds)
        if max_allowed <= 0:
            return

        requested_seconds = (end - start).total_seconds()
        if requested_seconds <= 0:
            requested_seconds = min_allowed

        requested_seconds = min(requested_seconds, max_allowed)
        requested_seconds = max(requested_seconds, min_allowed)

        new_duration = timedelta(seconds=requested_seconds)
        new_start = start
        new_end = new_start + new_duration

        if new_end > self._full_end:
            new_end = self._full_end
            new_start = new_end - new_duration

        if new_start < self._full_start:
            new_start = self._full_start
            new_end = new_start + new_duration
            if new_end > self._full_end:
                new_end = self._full_end
                new_start = new_end - new_duration

        self._visible_start = new_start
        self._visible_end = new_end
        self._visible_duration_seconds = (new_end - new_start).total_seconds()

        self.time_range_changed.emit(self._visible_start, self._visible_end)
        self.duration_changed.emit(self._visible_duration_seconds)

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
