"""Graphics item for rendering signal name labels."""

from PyQt6.QtWidgets import QGraphicsItem
from PyQt6.QtGui import QPainter, QColor, QPen, QFont
from PyQt6.QtCore import QRectF, Qt


class SignalLabelItem(QGraphicsItem):
    """Graphics item for displaying a signal name label.

    This is separate from the waveform to ensure clean separation.
    """

    LABEL_WIDTH = 180.0
    SIGNAL_HEIGHT = 60.0

    def __init__(self, device_id: str, signal_name: str, parent=None):
        """Initialize signal label item.

        Args:
            device_id: Identifier of the device
            signal_name: Name of the signal to display
            parent: Parent graphics item
        """
        super().__init__(parent)
        self.device_id = device_id
        self.signal_name = signal_name

        # Colors
        self.bg_color = QColor("#F5F5F5")
        self.text_color = QColor("#212121")
        self.sub_text_color = QColor("#424242")
        self.border_color = QColor("#E0E0E0")

    def boundingRect(self) -> QRectF:
        """Return the bounding rectangle (relative to item's position)."""
        return QRectF(0, 0, self.LABEL_WIDTH, self.SIGNAL_HEIGHT)

    def paint(self, painter: QPainter, option, widget=None):
        """Paint the signal label."""
        # Draw background
        painter.fillRect(self.boundingRect(), self.bg_color)

        # Draw right border (separator from waveform area)
        pen = QPen(self.border_color)
        pen.setWidth(2)
        painter.setPen(pen)
        painter.drawLine(
            int(self.LABEL_WIDTH - 1),
            0,
            int(self.LABEL_WIDTH - 1),
            int(self.SIGNAL_HEIGHT)
        )

        # Draw bottom border
        painter.drawLine(
            0,
            int(self.SIGNAL_HEIGHT - 1),
            int(self.LABEL_WIDTH),
            int(self.SIGNAL_HEIGHT - 1)
        )

        # Draw device ID (top)
        device_font = QFont("Arial", 10, QFont.Weight.Bold)
        painter.setFont(device_font)
        painter.setPen(self.text_color)

        device_rect = QRectF(
            10,
            4,
            self.LABEL_WIDTH - 20,
            (self.SIGNAL_HEIGHT / 2) - 4
        )

        painter.drawText(
            device_rect,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom,
            self.device_id
        )

        # Draw signal name (bottom)
        signal_font = QFont("Arial", 10)
        painter.setFont(signal_font)
        painter.setPen(self.sub_text_color)

        signal_rect = QRectF(
            10,
            self.SIGNAL_HEIGHT / 2,
            self.LABEL_WIDTH - 20,
            (self.SIGNAL_HEIGHT / 2) - 6
        )

        painter.drawText(
            signal_rect,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
            self.signal_name
        )
