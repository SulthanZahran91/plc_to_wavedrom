"""Zoom controls widget for waveform visualization."""

from PySide6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QPushButton,
    QSlider,
    QLabel,
    QToolButton,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon
from ..clickable_label import ClickableLabel


def format_duration(seconds: float) -> str:
    """Format duration in seconds to a human-readable string.

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted string (e.g., "5.0s", "2m 30s", "1h 15m")
    """
    if seconds < 1.0:
        # Milliseconds
        return f"{seconds * 1000:.0f}ms"
    elif seconds < 60:
        # Seconds
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        # Minutes and seconds
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        if secs == 0:
            return f"{minutes}m"
        return f"{minutes}m {secs}s"
    else:
        # Hours and minutes
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        if minutes == 0:
            return f"{hours}h"
        return f"{hours}h {minutes}m"

class ZoomControls(QWidget):
    """Widget providing zoom controls (buttons, slider, display).

    Signals:
        zoom_in_clicked: Emitted when zoom in button is clicked
        zoom_out_clicked: Emitted when zoom out button is clicked
        reset_zoom_clicked: Emitted when reset zoom button is clicked
        duration_changed: Emitted when slider is moved (duration in seconds)
    """

    zoom_in_clicked = Signal()
    zoom_out_clicked = Signal()
    reset_zoom_clicked = Signal()
    duration_changed = Signal(float)  # Emits visible duration in seconds

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        """Initialize the user interface."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(8)

        # Zoom out button
        self.zoom_out_btn = QPushButton("-")
        self.zoom_out_btn.setFixedSize(32, 32)
        self.zoom_out_btn.setToolTip("Zoom out (Ctrl+-)")
        self.zoom_out_btn.clicked.connect(self.zoom_out_clicked)
        layout.addWidget(self.zoom_out_btn)

        # Zoom slider
        slider_container = QVBoxLayout()
        slider_container.setSpacing(2)

        self.zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self.zoom_slider.setMinimum(0)  # Will map to min_zoom
        self.zoom_slider.setMaximum(1000)  # Will map to max_zoom
        self.zoom_slider.setValue(0)  # Start at minimum (1x)
        self.zoom_slider.setFixedWidth(200)
        self.zoom_slider.setToolTip("Zoom level (1x to 100x)")
        self.zoom_slider.valueChanged.connect(self._on_slider_changed)
        slider_container.addWidget(self.zoom_slider)

        layout.addLayout(slider_container)

        # Zoom in button
        self.zoom_in_btn = QPushButton("+")
        self.zoom_in_btn.setFixedSize(32, 32)
        self.zoom_in_btn.setToolTip("Zoom in (Ctrl++)")
        self.zoom_in_btn.clicked.connect(self.zoom_in_clicked)
        layout.addWidget(self.zoom_in_btn)

        # Visible duration display
        self.zoom_label = ClickableLabel("Window: 5m")
        self.zoom_label.setMinimumWidth(100)
        self.zoom_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.zoom_label.setToolTip("Visible time window duration")
        self.zoom_label.zoom_changed.connect(lambda d: self.duration_changed.emit(d))
        layout.addWidget(self.zoom_label)

        # Reset button
        self.reset_btn = QPushButton("Reset")
        self.reset_btn.setToolTip("Reset zoom to fit all (Ctrl+0)")
        self.reset_btn.clicked.connect(self.reset_zoom_clicked)
        layout.addWidget(self.reset_btn)

        layout.addStretch()

        # Apply styling
        self.setStyleSheet("""
            QWidget {
                background-color: #f5f5f5;
                border-radius: 4px;
            }
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #0D47A1;
            }
            QPushButton:disabled {
                background-color: #BDBDBD;
            }
            QLabel {
                background-color: transparent;
                font-size: 12px;
                font-weight: bold;
                color: #333;
            }
            QSlider::groove:horizontal {
                border: 1px solid #999999;
                height: 6px;
                background: white;
                margin: 2px 0;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #2196F3;
                border: 1px solid #1976D2;
                width: 16px;
                height: 16px;
                margin: -6px 0;
                border-radius: 8px;
            }
            QSlider::handle:horizontal:hover {
                background: #1976D2;
            }
            QSlider::sub-page:horizontal {
                background: #64B5F6;
                border: 1px solid #999999;
                height: 6px;
                border-radius: 3px;
            }
        """)

    def _on_slider_changed(self, value: int):
        """Handle slider value change.

        Args:
            value: Slider value (0-1000)
        """
        # Map slider value (0-1000) to duration (max to min)
        # Slider at 0 = max duration (most zoomed out)
        # Slider at 1000 = min duration (most zoomed in)
        # Using logarithmic scale for better control

        import math
        min_duration = 0.001  # 1ms
        max_duration = 300.0  # 5 minutes

        if value == 0:
            duration = max_duration
        elif value == 1000:
            duration = min_duration
        else:
            # Logarithmic scale from max to min
            # Invert the slider so left = more time (zoomed out), right = less time (zoomed in)
            inverted_value = 1000 - value
            duration = max_duration * math.pow(min_duration / max_duration, (1000 - inverted_value) / 1000.0)

        self.duration_changed.emit(duration)

    def set_visible_duration(self, duration_seconds: float, min_duration: float = 0.001, max_duration: float = 300.0):
        """Update the display to show the current visible duration.

        Args:
            duration_seconds: Current visible duration in seconds
            min_duration: Minimum duration constraint (for slider mapping)
            max_duration: Maximum duration constraint (for slider mapping)
        """
        # Update label with formatted duration
        self.zoom_label.setText(f"Window: {format_duration(duration_seconds)}")

        # Update slider position (without triggering signal)
        import math

        # Constrain duration to bounds
        duration_seconds = max(min_duration, min(duration_seconds, max_duration))

        if duration_seconds >= max_duration:
            slider_value = 0  # Most zoomed out
        elif duration_seconds <= min_duration:
            slider_value = 1000  # Most zoomed in
        else:
            # Inverse logarithmic scale
            # Calculate how far we are from max_duration to min_duration
            ratio = math.log(duration_seconds / max_duration) / math.log(min_duration / max_duration)
            slider_value = int(ratio * 1000.0)

        # Block signals to avoid feedback loop
        self.zoom_slider.blockSignals(True)
        self.zoom_slider.setValue(slider_value)
        self.zoom_slider.blockSignals(False)

        # Update button states
        self.zoom_in_btn.setEnabled(duration_seconds > min_duration)
        self.zoom_out_btn.setEnabled(duration_seconds < max_duration)

    def set_zoom_level(self, zoom: float):
        """Update display using zoom level (for backward compatibility).

        Converts zoom level to duration for display.

        Args:
            zoom: Current zoom level
        """
        # This is for backward compatibility - convert zoom to duration
        # Assuming a reference duration (e.g., 300 seconds at zoom=1.0)
        reference_duration = 300.0
        duration_seconds = reference_duration / zoom
        self.set_visible_duration(duration_seconds)

    def set_enabled(self, enabled: bool):
        """Enable or disable all controls.

        Args:
            enabled: True to enable, False to disable
        """
        self.zoom_in_btn.setEnabled(enabled)
        self.zoom_out_btn.setEnabled(enabled)
        self.zoom_slider.setEnabled(enabled)
        self.reset_btn.setEnabled(enabled)
