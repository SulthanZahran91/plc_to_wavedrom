"""Pan controls widget for time navigation."""

from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QPushButton,
    QLineEdit,
    QLabel,
    QScrollBar,
)
from PyQt6.QtCore import Qt, pyqtSignal, QTime


class PanControls(QWidget):
    """Widget providing pan/navigation controls.

    Signals:
        pan_left_clicked: Emitted when pan left button is clicked
        pan_right_clicked: Emitted when pan right button is clicked
        jump_to_time: Emitted when user requests to jump to a specific time
        scroll_changed: Emitted when scrollbar position changes (0.0 to 1.0)
    """

    pan_left_clicked = pyqtSignal()
    pan_right_clicked = pyqtSignal()
    jump_to_time = pyqtSignal(datetime)
    scroll_changed = pyqtSignal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._full_start: datetime = None
        self._full_end: datetime = None
        self._init_ui()

    def _init_ui(self):
        """Initialize the user interface."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(8)

        # Pan left button
        self.pan_left_btn = QPushButton("◀")
        self.pan_left_btn.setFixedSize(32, 32)
        self.pan_left_btn.setToolTip("Pan left (←)")
        self.pan_left_btn.clicked.connect(self.pan_left_clicked)
        layout.addWidget(self.pan_left_btn)

        # Horizontal scrollbar for navigation
        self.scroll_bar = QScrollBar(Qt.Orientation.Horizontal)
        self.scroll_bar.setMinimum(0)
        self.scroll_bar.setMaximum(1000)  # High resolution
        self.scroll_bar.setValue(0)
        self.scroll_bar.setPageStep(100)
        self.scroll_bar.setSingleStep(10)
        self.scroll_bar.setToolTip("Drag to navigate through time")
        self.scroll_bar.valueChanged.connect(self._on_scroll_changed)
        layout.addWidget(self.scroll_bar, stretch=1)

        # Pan right button
        self.pan_right_btn = QPushButton("▶")
        self.pan_right_btn.setFixedSize(32, 32)
        self.pan_right_btn.setToolTip("Pan right (→)")
        self.pan_right_btn.clicked.connect(self.pan_right_clicked)
        layout.addWidget(self.pan_right_btn)

        # Jump to time input
        jump_label = QLabel("Jump to:")
        jump_label.setToolTip("Enter time in HH:MM:SS format")
        layout.addWidget(jump_label)

        self.time_input = QLineEdit()
        self.time_input.setPlaceholderText("HH:MM:SS")
        self.time_input.setFixedWidth(100)
        self.time_input.setToolTip("Enter time and press Enter to jump")
        self.time_input.returnPressed.connect(self._on_jump_to_time)
        layout.addWidget(self.time_input)

        # Go button
        self.go_btn = QPushButton("Go")
        self.go_btn.setFixedWidth(50)
        self.go_btn.setToolTip("Jump to specified time")
        self.go_btn.clicked.connect(self._on_jump_to_time)
        layout.addWidget(self.go_btn)

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
                color: #333;
            }
            QLineEdit {
                background-color: white;
                border: 1px solid #ccc;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 12px;
            }
            QLineEdit:focus {
                border: 1px solid #2196F3;
            }
            QScrollBar:horizontal {
                border: 1px solid #999999;
                background: white;
                height: 15px;
                margin: 0px 0px 0px 0px;
                border-radius: 3px;
            }
            QScrollBar::handle:horizontal {
                background: #2196F3;
                min-width: 20px;
                border-radius: 3px;
            }
            QScrollBar::handle:horizontal:hover {
                background: #1976D2;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                width: 0px;
            }
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
                background: #e0e0e0;
            }
        """)

    def _on_scroll_changed(self, value: int):
        """Handle scrollbar value change.

        Args:
            value: Scrollbar value (0-1000)
        """
        # Convert to 0.0 - 1.0 range
        position = value / 1000.0
        self.scroll_changed.emit(position)

    def _on_jump_to_time(self):
        """Handle jump to time request."""
        time_text = self.time_input.text().strip()

        if not time_text:
            return

        # Parse time input (HH:MM:SS)
        try:
            # Try parsing as QTime
            time_obj = QTime.fromString(time_text, "HH:mm:ss")
            if not time_obj.isValid():
                # Try without seconds
                time_obj = QTime.fromString(time_text, "HH:mm")

            if not time_obj.isValid():
                self.time_input.setStyleSheet("border: 2px solid red;")
                return

            # Create datetime with the parsed time
            if self._full_start is not None:
                # Use the date from full_start, but the time from input
                target = datetime.combine(
                    self._full_start.date(),
                    datetime.min.time()
                ).replace(
                    hour=time_obj.hour(),
                    minute=time_obj.minute(),
                    second=time_obj.second()
                )

                if self._full_end is not None:
                    # Clamp target within available range
                    if target < self._full_start:
                        target = self._full_start
                    elif target > self._full_end:
                        target = self._full_end

                self.jump_to_time.emit(target)
                self.time_input.setStyleSheet("")  # Clear error style
                self.time_input.clear()

        except Exception:
            self.time_input.setStyleSheet("border: 2px solid red;")

    def set_scroll_position(self, position: float, visible_fraction: float = 1.0):
        """Update scrollbar position and adjust handle size.

        Args:
            position: Position as fraction (0.0 to 1.0)
            visible_fraction: Fraction of the timeline currently visible (0.0-1.0)
        """
        position = max(0.0, min(1.0, position))
        visible_fraction = max(0.0, min(1.0, visible_fraction))

        value = int(position * 1000)
        page_step = max(1, min(1000, int(visible_fraction * 1000)))

        # Block signals to avoid feedback loop
        self.scroll_bar.blockSignals(True)
        self.scroll_bar.setPageStep(page_step)
        self.scroll_bar.setValue(value)
        self.scroll_bar.blockSignals(False)

    def set_time_range(self, start: datetime, end: datetime):
        """Set the full time range for validation.

        Args:
            start: Start time
            end: End time
        """
        self._full_start = start
        self._full_end = end

        # Update tooltip with time range
        time_range_str = f"{start.strftime('%H:%M:%S')} - {end.strftime('%H:%M:%S')}"
        self.time_input.setToolTip(f"Enter time between {time_range_str}")

    def set_enabled(self, enabled: bool):
        """Enable or disable all controls.

        Args:
            enabled: True to enable, False to disable
        """
        self.pan_left_btn.setEnabled(enabled)
        self.pan_right_btn.setEnabled(enabled)
        self.scroll_bar.setEnabled(enabled)
        self.time_input.setEnabled(enabled)
        self.go_btn.setEnabled(enabled)
