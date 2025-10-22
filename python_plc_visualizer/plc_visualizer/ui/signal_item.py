"""Graphics item for rendering a single signal waveform (no label)."""

from datetime import datetime

from PySide6.QtWidgets import QGraphicsItem, QGraphicsPathItem, QGraphicsSimpleTextItem
from PySide6.QtGui import QPainter, QColor, QPen, QFont, QBrush
from PySide6.QtCore import QRectF

from plc_visualizer.models import SignalType
from plc_visualizer.utils import SignalData, SignalState
from .renderers import BooleanRenderer, StateRenderer
from .transition_marker_item import TransitionMarkerItem


class SignalItem(QGraphicsItem):
    """Graphics item for displaying ONLY the signal waveform.

    The signal label is handled separately by SignalLabelItem.
    This item only renders the waveform within its bounding box.
    """

    SIGNAL_HEIGHT = 60.0  # Increased from 40.0 for better visibility
    MAX_TRANSITION_MARKERS = 1500

    def __init__(
        self,
        signal_data: SignalData,
        time_range: tuple[datetime, datetime],
        width: float,
        parent=None
    ):
        """Initialize signal waveform item.

        Args:
            signal_data: Signal data to visualize
            time_range: Time range to display
            width: Width of the waveform area (full width, no label area)
            parent: Parent graphics item
        """
        super().__init__(parent)

        self.signal_data = signal_data
        self.time_range = time_range
        self.width = width  # Full waveform width

        # Ensure child graphics (paths/text) stay within this bounding box
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemClipsChildrenToShape, True)

        # Create renderer based on signal type
        if signal_data.signal_type == SignalType.BOOLEAN:
            self.renderer = BooleanRenderer(self.SIGNAL_HEIGHT)
        else:  # STRING or INTEGER
            self.renderer = StateRenderer(self.SIGNAL_HEIGHT)

        # Graphics items
        self.path_items = []
        self.text_items = []
        self.transition_items = []
        self._active_transition_marker: TransitionMarkerItem | None = None
        self._last_clipped_states: list | None = None
        self._last_render_range: tuple[datetime, datetime] | None = None
        self._last_render_width: float | None = None

        self._create_items()

    def _create_items(self):
        """Create the graphics items for this signal."""
        # Clear existing items
        for item in self.path_items + self.text_items:
            if item.scene():
                item.scene().removeItem(item)

        self._clear_transition_markers()

        self.path_items.clear()
        self.text_items.clear()

        clipped_states = self.renderer.clip_states(self.signal_data, self.time_range)
        self._last_clipped_states = clipped_states

        if not clipped_states:
            self._clear_transition_markers()
            self._last_render_range = self.time_range
            self._last_render_width = self.width
            return

        # Render the waveform using full width (no offset needed)
        rendered = self.renderer.render(
            self.signal_data,
            self.time_range,
            self.width,
            0,
            clipped_states=clipped_states
        )

        # Create path items (no offset - starts at x=0 of this item)
        for path, pen, brush in rendered:
            item = QGraphicsPathItem(path, self)
            item.setPos(0, 0)  # No offset needed - this item IS the waveform area
            if pen:
                item.setPen(pen)
            if brush:
                item.setBrush(brush)
            self.path_items.append(item)

        # Add text labels for state renderer
        if isinstance(self.renderer, StateRenderer):
            text_data = self.renderer.get_text_items(
                self.signal_data,
                self.time_range,
                self.width,
                0,
                clipped_states=clipped_states
            )

            font = QFont("Arial", 10)
            for text, rect in text_data:
                text_item = QGraphicsSimpleTextItem(text, self)
                text_item.setFont(font)
                text_item.setBrush(QBrush(QColor("#FFFFFF")))

                # Center text in rectangle (no offset needed)
                text_rect = text_item.boundingRect()
                x = rect.x() + (rect.width() - text_rect.width()) / 2
                y = rect.y() + (rect.height() - text_rect.height()) / 2
                text_item.setPos(x, y)

                self.text_items.append(text_item)

        self._create_transition_markers(clipped_states)
        self._last_render_range = self.time_range
        self._last_render_width = self.width

    def boundingRect(self) -> QRectF:
        """Return the bounding rectangle (relative to item's position)."""
        return QRectF(0, 0, self.width, self.SIGNAL_HEIGHT)

    def paint(self, painter: QPainter, option, widget=None):
        """Paint the signal waveform area."""
        # Draw background
        bg_color = QColor("#FFFFFF")
        painter.fillRect(self.boundingRect(), bg_color)

        # Draw bottom border
        pen = QPen(QColor("#E0E0E0"))
        pen.setWidth(1)
        painter.setPen(pen)
        painter.drawLine(
            0,
            int(self.SIGNAL_HEIGHT - 1),
            int(self.width),
            int(self.SIGNAL_HEIGHT - 1)
        )

        # Child items (paths and text) are painted automatically

    def update_time_range(self, time_range: tuple[datetime, datetime]):
        """Update the time range and redraw."""
        if not time_range:
            return
        self.set_time_range(*time_range)

    def update_width(self, width: float):
        """Update the width and redraw."""
        if abs(self.width - width) < 0.5:
            return
        self.prepareGeometryChange()
        self.width = width
        self._create_items()
        self.update()

    def set_time_range(self, start: datetime, end: datetime):
        """Update the visible time range for viewport culling.

        Args:
            start: New start time
            end: New end time
        """
        new_range = (start, end)
        if (
            self._last_render_range == new_range
            and self._last_render_width is not None
            and abs(self._last_render_width - self.width) < 0.5
        ):
            self.time_range = new_range
            return

        self.time_range = new_range
        self._create_items()
        self.update()

    def _clear_transition_markers(self):
        """Remove existing transition markers."""
        for marker in self.transition_items:
            if marker.scene():
                marker.scene().removeItem(marker)

        self.transition_items.clear()
        self._active_transition_marker = None

    def _create_transition_markers(self, clipped_states: list):
        """Create clickable markers for value transitions."""
        if not self.time_range or not clipped_states:
            return

        if len(clipped_states) < 2:
            return

        padding = getattr(self.renderer, "padding", 12.0)
        track_top = padding
        track_bottom = self.renderer.signal_height - padding
        marker_height = track_bottom - track_top

        if marker_height <= 0:
            return

        marker_color = getattr(
            self.renderer,
            "transition_color",
            QColor("#FB8C00")
        )

        # Pre-compute scaling for marker placement
        anchor = self.signal_data.time_anchor or self.time_range[0]
        range_start_offset = (self.time_range[0] - anchor).total_seconds()
        range_duration = max((self.time_range[1] - self.time_range[0]).total_seconds(), 1e-12)
        pixel_factor = self.width / range_duration

        transitions: list[tuple[SignalState, SignalState]] = []
        prev_state = clipped_states[0]
        for state in clipped_states[1:]:
            if state.value == prev_state.value:
                prev_state = state
                continue
            transitions.append((prev_state, state))
            prev_state = state

        if not transitions:
            return

        total_transitions = len(transitions)
        stride = 1
        if total_transitions > self.MAX_TRANSITION_MARKERS:
            stride = max(1, total_transitions // self.MAX_TRANSITION_MARKERS)

        for index, (before_state, state) in enumerate(transitions):
            if stride > 1 and index % stride != 0 and index not in (0, total_transitions - 1):
                continue

            x_pos = max(
                0.0,
                min(
                    self.width,
                    (state.start_offset - range_start_offset) * pixel_factor
                )
            )

            before_val = self._format_value(before_state.value)
            after_val = self._format_value(state.value)
            time_text = self._format_timestamp(state.start_time)
            tooltip_text = f"{time_text}\n{before_val} -> {after_val}"

            marker = TransitionMarkerItem(
                marker_height=marker_height,
                color=marker_color,
                tooltip_text=tooltip_text,
                click_callback=self._on_transition_marker_clicked,
                parent=self
            )
            marker.setToolTip(tooltip_text)
            marker.setPos(x_pos, track_top)

            marker.transition_data = {
                "timestamp": state.start_time,
                "before": before_state.value,
                "after": state.value
            }

            self.transition_items.append(marker)

    def _on_transition_marker_clicked(self, marker: TransitionMarkerItem):
        """Toggle active highlight when a marker is clicked."""
        if self._active_transition_marker is marker:
            marker.set_active(False)
            self._active_transition_marker = None
            return

        if self._active_transition_marker:
            self._active_transition_marker.set_active(False)

        marker.set_active(True)
        self._active_transition_marker = marker

    def _format_value(self, value) -> str:
        """Convert transition value to display label."""
        if isinstance(self.renderer, BooleanRenderer):
            return "True (HIGH)" if bool(value) else "False (LOW)"
        return str(value)

    @staticmethod
    def _format_timestamp(timestamp: datetime) -> str:
        """Format timestamp with millisecond precision."""
        return timestamp.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
