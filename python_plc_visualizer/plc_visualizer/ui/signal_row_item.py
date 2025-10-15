# signal_row_item.py
from PyQt6.QtWidgets import QGraphicsObject
from PyQt6.QtCore import QRectF, QPointF, pyqtSignal

class SignalRowItem(QGraphicsObject):
    dropped = pyqtSignal(object)

    def __init__(self, label_item, waveform_item, row_height: float,
                 top_margin: float, total_width: float, parent=None):
        super().__init__(parent)
        self.label_item = label_item
        self.waveform_item = waveform_item
        self.row_height = row_height
        self.top_margin = top_margin
        self._total_width = total_width  # NEW: track full width

        self.label_item.setParentItem(self)
        self.waveform_item.setParentItem(self)

        self.setFlag(self.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(self.GraphicsItemFlag.ItemSendsGeometryChanges, True)
        self.setFlag(self.GraphicsItemFlag.ItemHasNoContents, True)  # no own painting

        self._dragging = False

    def update_width(self, total_width: float):
        self._total_width = total_width
        # tell the scene our geometry changed, so it refreshes culling/index
        self.prepareGeometryChange()

    def set_row_index(self, idx: int):
        y = self.top_margin + idx * self.row_height
        self.setPos(QPointF(0.0, y))

    def row_index_from_y(self) -> int:
        y = self.pos().y() - self.top_margin
        return max(0, round(y / self.row_height))

    # Important: bounding rect must cover the children’s painted area
    def boundingRect(self) -> QRectF:
        return QRectF(0, 0, self._total_width, self.row_height)

    def paint(self, painter, option, widget=None):
        pass

    def mousePressEvent(self, event):
        self._dragging = True
        self.setZValue(10_000)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        new_pos = self.pos() + event.scenePos() - event.lastScenePos()
        self.setPos(QPointF(0.0, new_pos.y()))
        event.accept()

    def mouseReleaseEvent(self, event):
        self._dragging = False
        self.setZValue(0)
        self.dropped.emit(self)
        super().mouseReleaseEvent(event)
