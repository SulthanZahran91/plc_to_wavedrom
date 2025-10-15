from PyQt6.QtWidgets import QLabel, QInputDialog
from PyQt6.QtCore import pyqtSignal




class ClickableLabel(QLabel):
    zoom_changed = pyqtSignal(float)

    def mousePressEvent(self, e):
        # parse current text like "Zoom: 1.0x"
        import re
        m = re.search(r"([0-9]*\.?[0-9]+)", self.text())
        current = float(m.group(1)) if m else 1.0

        val, ok = QInputDialog.getDouble(self, "Set Zoom", "Zoom (x):",
                                         current, 0.1, 1000.0, 1)
        if ok:
            self.setText(f"Zoom: {val:.1f}x")
            self.zoom_changed.emit(val)
        super().mousePressEvent(e)
