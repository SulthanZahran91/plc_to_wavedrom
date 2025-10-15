"""Graphics view for displaying waveforms."""

from datetime import datetime
from typing import Optional
from PyQt6.QtWidgets import QGraphicsView
from PyQt6.QtCore import Qt, pyqtSignal, QRectF
from PyQt6.QtGui import QPainter, QWheelEvent

from .waveform_scene import WaveformScene


class WaveformView(QGraphicsView):
    """Graphics view for displaying the waveform scene.

    Signals:
        wheel_zoom: Emitted when mouse wheel zoom is requested (delta)
    """

    wheel_zoom = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)

        # Create scene
        self.waveform_scene = WaveformScene(self)
        self.setScene(self.waveform_scene)

        # Viewport state reference
        self._viewport_state = None

        # Configure view
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        # Scrolling behavior
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        # Interaction
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)

        # Style
        self.setStyleSheet("""
            QGraphicsView {
                border: 1px solid #ddd;
                background-color: #fafafa;
            }
        """)
        
    def _pin_time_axis(self):
        """Keep the time axis visually frozen at the top of the viewport."""
        scene = self.waveform_scene
        if scene and scene.time_axis:
            # Scene coords of viewport's top-left
            tl = self.mapToScene(0, 0)
            scene.time_axis.setPos(tl.x(), tl.y())
            scene.time_axis.setZValue(1_000_000)  # ensure on top
            # Prevent interactions on the axis (optional)
            scene.time_axis.setAcceptedMouseButtons(Qt.MouseButton.NoButton)


    def resizeEvent(self, event):
        """Handle resize events to update scene width."""
        super().resizeEvent(event)

        # Update scene width to match viewport width
        self.resetTransform()
        viewport_width = self.viewport().width()
        self.waveform_scene.update_width(viewport_width)
        self._pin_time_axis()

    def scrollContentsBy(self, dx: int, dy: int):
        """Called whenever the view scrolls; re-pin the axis."""
        super().scrollContentsBy(dx, dy)
        self._pin_time_axis()


    def set_data(self, parsed_log, signal_data_list=None):
        """Set the data to visualize.

        Args:
            parsed_log: ParsedLog containing entries to visualize
        """
        self.waveform_scene.set_data(parsed_log, signal_data_list)

        # Ensure the scene width matches the viewport so the waveform stretches
        viewport_width = self.viewport().width()
        if viewport_width > 0:
            self.waveform_scene.update_width(viewport_width)

        # Always use a 1:1 transform so the waveform fills the available space
        self.resetTransform()

        # Start the view at the top-left of the waveform area
        if self.waveform_scene.sceneRect().isValid():
            self.ensureVisible(QRectF(0, 0, 1, 1), 0, 0)
            
        self._pin_time_axis()

    def set_visible_signals(self, signal_names: list[str]):
        """Update which signals are visible in the view."""
        self.waveform_scene.set_visible_signals(signal_names)

        viewport_width = self.viewport().width()
        if viewport_width > 0:
            self.waveform_scene.update_width(viewport_width)

    def clear(self):
        """Clear the waveform display."""
        self.waveform_scene.clear()

    def set_viewport_state(self, viewport_state):
        """Set the viewport state manager.

        Args:
            viewport_state: ViewportState instance
        """
        self._viewport_state = viewport_state

        # Connect to viewport changes
        if viewport_state:
            viewport_state.time_range_changed.connect(self._on_time_range_changed)

    def _on_time_range_changed(self, start: datetime, end: datetime):
        """Handle time range changes from viewport state.

        Args:
            start: New visible start time
            end: New visible end time
        """
        # Update scene to render only visible time range
        if self.waveform_scene.parsed_log:
            self.waveform_scene.set_time_range(start, end)

        self._pin_time_axis()

    def wheelEvent(self, event: QWheelEvent):
        """Handle mouse wheel events for zooming.

        Args:
            event: Wheel event
        """
        # Check if Ctrl is pressed for zooming
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            # Emit signal for zoom
            delta = event.angleDelta().y()
            self.wheel_zoom.emit(delta)
            event.accept()
        else:
            # Default scrolling behavior
            super().wheelEvent(event)
