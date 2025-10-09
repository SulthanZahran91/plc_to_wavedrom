"""Graphics item for rendering a single signal waveform (no label)."""

from datetime import datetime

from PyQt6.QtWidgets import QGraphicsItem, QGraphicsPathItem, QGraphicsSimpleTextItem
from PyQt6.QtGui import QPainter, QColor, QPen, QFont, QBrush
from PyQt6.QtCore import QRectF

from plc_visualizer.models import SignalType
from plc_visualizer.utils import SignalData
from .renderers import BooleanRenderer, StateRenderer


class SignalItem(QGraphicsItem):
    """Graphics item for displaying ONLY the signal waveform.

    The signal label is handled separately by SignalLabelItem.
    This item only renders the waveform within its bounding box.
    """

    SIGNAL_HEIGHT = 60.0  # Increased from 40.0 for better visibility

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

        self._create_items()

    def _create_items(self):
        """Create the graphics items for this signal."""
        # Clear existing items
        for item in self.path_items + self.text_items:
            if item.scene():
                item.scene().removeItem(item)

        self.path_items.clear()
        self.text_items.clear()

        # Render the waveform using full width (no offset needed)
        rendered = self.renderer.render(
            self.signal_data,
            self.time_range,
            self.width,  # Use full width
            0  # y_offset is 0 since position is set by setPos()
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
                0  # y_offset is 0 since position is set by setPos()
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
        self.time_range = time_range
        self._create_items()
        self.update()

    def update_width(self, width: float):
        """Update the width and redraw."""
        self.width = width
        self._create_items()
        self.prepareGeometryChange()
        self.update()

    def set_time_range(self, start: datetime, end: datetime):
        """Update the visible time range for viewport culling.

        Args:
            start: New start time
            end: New end time
        """
        self.time_range = (start, end)
        self._create_items()
        self.update()
