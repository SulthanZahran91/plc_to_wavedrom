# map_viewer/media_controls.py
from PySide6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QSlider, QLineEdit, QComboBox, QLabel
from PySide6.QtCore import Qt

class MediaControls(QWidget):
    """Pure UI (no functionality). Exposes controls as public attributes."""
    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(10, 8, 10, 8)
        lay.setSpacing(10)

        self.btn_back_10s = QPushButton("⏪ 10s", self)
        self.btn_play     = QPushButton("▶", self); self.btn_play.setMinimumWidth(40)
        self.btn_fwd_10s  = QPushButton("10s ⏩", self)

        self.media_slider = QSlider(Qt.Orientation.Horizontal, self)
        self.media_slider.setRange(0, 100)
        self.media_slider.setSingleStep(1)
        self.media_slider.setPageStep(5)
        self.media_slider.setMinimumWidth(300)

        self.lbl_current_time = QLabel("00:00:00.000", self)
        self.lbl_current_time.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.lbl_current_time.setMinimumWidth(110)
        self.lbl_current_time.setToolTip("Current timestamp")

        self.cmb_date = QComboBox(self)
        self.cmb_date.setToolTip("Select the date to preview")
        self.cmb_date.setFixedWidth(130)

        self.txt_time = QLineEdit(self)
        self.txt_time.setPlaceholderText("HH:MM:SS.mmm")
        self.txt_time.setFixedWidth(120)
        self.txt_time.setToolTip("Enter a time of day for the selected date")

        self.cmb_speed = QComboBox(self)
        self.cmb_speed.addItems(["0.25×", "0.5×", "1.0×", "1.25×", "1.5×", "2.0×", "4.0×", "8.0×", "16.0×"])
        self.cmb_speed.setCurrentText("1.0×")
        self.cmb_speed.setFixedWidth(90)

        lay.addWidget(self.btn_back_10s)
        lay.addWidget(self.btn_play)
        lay.addWidget(self.btn_fwd_10s)
        lay.addWidget(self.media_slider, 1)
        lay.addWidget(self.lbl_current_time)
        lay.addWidget(self.cmb_date)
        lay.addWidget(self.txt_time)
        lay.addWidget(self.cmb_speed)
