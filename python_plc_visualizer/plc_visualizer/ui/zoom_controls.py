"""Zoom controls widget for waveform visualization."""

from PyQt6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QPushButton,
    QSlider,
    QLabel,
    QToolButton,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QIcon
from .ClickableLabel import ClickableLabel

class ZoomControls(QWidget):
    """Widget providing zoom controls (buttons, slider, display).

    Signals:
        zoom_in_clicked: Emitted when zoom in button is clicked
        zoom_out_clicked: Emitted when zoom out button is clicked
        reset_zoom_clicked: Emitted when reset zoom button is clicked
        zoom_level_changed: Emitted when slider is moved (float value)
    """

    zoom_in_clicked = pyqtSignal()
    zoom_out_clicked = pyqtSignal()
    reset_zoom_clicked = pyqtSignal()
    zoom_level_changed = pyqtSignal(float)

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

        # Zoom level display
        self.zoom_label = ClickableLabel("Zoom: 1.0x")
        self.zoom_label.setMinimumWidth(90)
        self.zoom_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.zoom_label.setToolTip("Current zoom level")
        self.zoom_label.zoom_changed.connect(lambda z: self.zoom_level_changed.emit(z))
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
            value: Slider value (0-100)
        """
        # Map slider value (0-100) to zoom level (1.0-100.0)
        # Using logarithmic scale for better control
        min_zoom = 1.0
        max_zoom = 1000.0

        if value == 0:
            zoom = min_zoom
        else:
            # Logarithmic scale
            import math
            zoom = min_zoom * math.pow(max_zoom / min_zoom, value / 1000.0)

        self.zoom_level_changed.emit(zoom)

    def set_zoom_level(self, zoom: float):
        """Update the display to show the current zoom level.

        Args:
            zoom: Current zoom level (1.0 to 100.0)
        """
        # Update label
        self.zoom_label.setText(f"Zoom: {zoom:.1f}x")

        # Update slider position (without triggering signal)
        import math
        min_zoom = 1.0
        max_zoom = 1000.0

        if zoom <= min_zoom:
            slider_value = 0
        else:
            # Inverse logarithmic scale
            slider_value = int(1000.0 * math.log(zoom / min_zoom) / math.log(max_zoom / min_zoom))

        # Block signals to avoid feedback loop
        self.zoom_slider.blockSignals(True)
        self.zoom_slider.setValue(slider_value)
        self.zoom_slider.blockSignals(False)

        # Update button states
        self.zoom_in_btn.setEnabled(zoom < max_zoom)
        self.zoom_out_btn.setEnabled(zoom > min_zoom)

    def set_enabled(self, enabled: bool):
        """Enable or disable all controls.

        Args:
            enabled: True to enable, False to disable
        """
        self.zoom_in_btn.setEnabled(enabled)
        self.zoom_out_btn.setEnabled(enabled)
        self.zoom_slider.setEnabled(enabled)
        self.reset_btn.setEnabled(enabled)
