# map_viewer/renderer.py
import math
from typing import Dict, Any, Optional

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QPen, QBrush, QFont, QPainterPath, QPolygonF
from PySide6.QtWidgets import QGraphicsView, QGraphicsScene, QLabel

from .config import (
    RENDER_AS_TEXT_TYPES, RENDER_AS_ARROW_TYPES, TYPE_COLOR_MAPPING,
    TYPE_ZINDEX_MAPPING, FORECOLOR_MAPPING
)

def _parse_flow_direction(flow_direction_str: Optional[str]) -> tuple[float, str]:
    if not flow_direction_str or not flow_direction_str.startswith("Angle_"):
        return 0.0, "right"
    try:
        user_angle = int(flow_direction_str.split("_")[1])
    except (IndexError, ValueError):
        return 0.0, "right"
    standard_deg = user_angle - 90
    deg = (standard_deg % 360 + 360) % 360
    axis = {270: "up", 0: "right", 90: "down", 180: "left"}.get(deg, "diagonal")
    return math.radians(deg), axis

class MapRenderer(QGraphicsView):
    """
    Standalone renderer. Public API:
      - set_objects(objects: dict) -> None
      - update_rect_color_by_unit(unit_id: str, color: QColor) -> int
    """
    def __init__(self):
        super().__init__()
        self.scene = QGraphicsScene()
        self.setScene(self.scene)

        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)

        # zoom
        self.zoom_factor = 1.0
        self.zoom_min = 0.1
        self.zoom_max = 10.0

        # info box
        self.info_box = QLabel(self)
        self.info_box.setStyleSheet("""
            QLabel {
                background-color: rgba(255, 255, 255, 230);
                border: 2px solid #333;
                border-radius: 5px;
                padding: 10px;
                font-size: 11pt;
            }
        """)
        self.info_box.setWordWrap(True)
        self.info_box.hide()
        self.info_box.setMaximumWidth(400)

        self.selected_item = None
        self._is_panning = False
        self._pan_start_pos = None

        # index: UnitId -> [QGraphicsItem, ...]
        self._items_by_unit: Dict[str, list] = {}

    # ---------- Public API ----------
    def set_objects(self, objects: Dict[str, Dict[str, Any]]) -> None:
        """Render parsed objects into the scene."""
        self.scene.clear()
        self._items_by_unit.clear()

        for name, data in objects.items():
            size_str = data.get("Size")
            loc_str = data.get("Location")
            obj_type = data.get("type")
            text_content = data.get("Text")
            unit_id = data.get("UnitId")

            if not size_str or not loc_str:
                continue

            try:
                width, height = map(int, size_str.split(', '))
                x, y = map(int, loc_str.split(', '))
            except ValueError:
                continue

            color = TYPE_COLOR_MAPPING.get(obj_type, TYPE_COLOR_MAPPING["default"])
            z_index = TYPE_ZINDEX_MAPPING.get(obj_type, TYPE_ZINDEX_MAPPING["default"])

            if obj_type in RENDER_AS_ARROW_TYPES:
                arrow_data = {
                    'name': name, 'type': obj_type, 'size': size_str, 'location': loc_str,
                    'text': text_content, 'UnitId': unit_id,
                    'LineThick': data.get("LineThick"),
                    'FlowDirection': data.get("FlowDirection"),
                    'EndCap': data.get("EndCap"),
                    'ForeColor': data.get("ForeColor"),
                    'render_type': 'arrow'
                }
                item = self._create_arrow(x, y, width, height, arrow_data)
                if item:
                    item.setZValue(z_index)
                    item.setData(0, arrow_data)
                    item.setFlag(item.GraphicsItemFlag.ItemIsSelectable)
                    self._index_unit_item(unit_id, item)

            elif obj_type in RENDER_AS_TEXT_TYPES:
                txt = (text_content or "").strip()
                if not txt:
                    continue
                text_item = self.scene.addText(text_content or name)
                text_item.setPos(x, y)
                text_item.setDefaultTextColor(Qt.GlobalColor.black)
                text_item.setFont(QFont("Arial", 8))
                text_item.setZValue(z_index)
                payload = {
                    'name': name, 'type': obj_type, 'size': size_str, 'location': loc_str,
                    'text': text_content, 'UnitId': unit_id, 'render_type': 'text'
                }
                text_item.setData(0, payload)
                text_item.setFlag(text_item.GraphicsItemFlag.ItemIsSelectable)
                self._index_unit_item(unit_id, text_item)

            else:
                rect = self.scene.addRect(x, y, width, height)
                rect.setPen(QPen(Qt.GlobalColor.black, 2))
                rect.setBrush(QBrush(color))
                rect.setZValue(z_index)
                payload = {
                    'name': name, 'type': obj_type, 'size': size_str, 'location': loc_str,
                    'render_type': 'rectangle', 'UnitId': unit_id
                }
                rect.setData(0, payload)
                rect.setFlag(rect.GraphicsItemFlag.ItemIsSelectable)
                self._index_unit_item(unit_id, rect)

        self.fitInView(self.scene.itemsBoundingRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def update_rect_color_by_unit(self, unit_id: str, color: QColor) -> int:
        """
        Update the brush of rectangle(s) sharing a UnitId.
        Returns the number of items changed.
        """
        items = self._items_by_unit.get(unit_id) or []
        changed = 0
        for it in items:
            data = it.data(0) or {}
            if data.get('render_type') == 'rectangle':
                it.setBrush(QBrush(color))
                changed += 1
        return changed

    # ---------- Internals ----------
    def _index_unit_item(self, unit_id: Optional[str], item):
        if not unit_id:
            return
        self._items_by_unit.setdefault(unit_id, []).append(item)

    def _create_arrow(self, x, y, width, height, data):
        line_thick = int(data.get('LineThick', 1) or 1)
        flow_direction = data.get('FlowDirection', 'Angle_0') or 'Angle_0'
        end_cap = (data.get('EndCap') or 'Flat').strip()
        fore_color_name = (data.get('ForeColor') or 'Black').strip()
        angle_rad, axis = _parse_flow_direction(flow_direction)

        cx = x + width / 2.0
        cy = y + height / 2.0

        if axis == "right":
            start = QPointF(x,        cy); end = QPointF(x+width,  cy)
        elif axis == "left":
            start = QPointF(x+width,  cy); end = QPointF(x,        cy)
        elif axis == "down":
            start = QPointF(cx, y);       end = QPointF(cx, y+height)
        elif axis == "up":
            start = QPointF(cx, y+height); end = QPointF(cx, y)
        else:
            dx = math.cos(angle_rad); dy = math.sin(angle_rad)
            L = math.hypot(width, height)
            start = QPointF(cx - dx * L, cy - dy * L)
            end   = QPointF(cx + dx * L, cy + dy * L)

        path = QPainterPath()
        path.moveTo(start); path.lineTo(end)
        color = FORECOLOR_MAPPING.get(fore_color_name, FORECOLOR_MAPPING["default"])
        pen = QPen(color, line_thick)
        arrow_item = self.scene.addPath(path, pen)

        if end_cap == "ArrowAnchor":
            arrow_size = max(10, line_thick * 3)
            theta = math.atan2(end.y() - start.y(), end.x() - start.x())
            wing = math.radians(30)
            left_ang  = theta + math.pi - wing
            right_ang = theta + math.pi + wing
            p_left  = QPointF(end.x() + arrow_size * math.cos(left_ang),
                              end.y() + arrow_size * math.sin(left_ang))
            p_right = QPointF(end.x() + arrow_size * math.cos(right_ang),
                              end.y() + arrow_size * math.sin(right_ang))
            head = QPolygonF([end, p_left, p_right])
            head_item = self.scene.addPolygon(head, pen, QBrush(color))
            head_item.setZValue(arrow_item.zValue())
            head_item.setData(0, data)
            head_item.setFlag(head_item.GraphicsItemFlag.ItemIsSelectable)

        arrow_item.setData(0, data)
        arrow_item.setFlag(arrow_item.GraphicsItemFlag.ItemIsSelectable)
        return arrow_item

    # ---------- Interaction (trimmed) ----------
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            item = self.itemAt(event.position().toPoint())
            if item and hasattr(item, 'data') and item.data(0):
                self._show_info(item)
                if self.selected_item:
                    self._unhighlight(self.selected_item)
                self._highlight(item)
                self.selected_item = item
                event.accept(); return
            else:
                if self.selected_item:
                    self._unhighlight(self.selected_item)
                    self.selected_item = None
                self.info_box.hide()
        if event.button() == Qt.MouseButton.MiddleButton:
            self._is_panning = True
            self._pan_start_pos = event.position().toPoint()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._is_panning and self._pan_start_pos is not None:
            delta = event.position().toPoint() - self._pan_start_pos
            self._pan_start_pos = event.position().toPoint()
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta.y())
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.MiddleButton:
            self._is_panning = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        zoom_in = 1.15
        factor = zoom_in if delta > 0 else 1 / zoom_in
        new_zoom = self.zoom_factor * factor
        if self.zoom_min <= new_zoom <= self.zoom_max:
            self.scale(factor, factor)
            self.zoom_factor = new_zoom

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_R:
            self.resetTransform()
            self.zoom_factor = 1.0
            self.fitInView(self.scene.itemsBoundingRect(), Qt.AspectRatioMode.KeepAspectRatio)
        elif event.key() in (Qt.Key.Key_Plus, Qt.Key.Key_Equal):
            if self.zoom_factor * 1.15 <= self.zoom_max:
                self.scale(1.15, 1.15); self.zoom_factor *= 1.15
        elif event.key() == Qt.Key.Key_Minus:
            if self.zoom_factor / 1.15 >= self.zoom_min:
                self.scale(1/1.15, 1/1.15); self.zoom_factor /= 1.15
        elif event.key() == Qt.Key.Key_Escape:
            if self.selected_item:
                self._unhighlight(self.selected_item)
                self.selected_item = None
            self.info_box.hide()
        else:
            super().keyPressEvent(event)

    def _highlight(self, item):
        data = item.data(0) or {}
        rt = data.get('render_type')
        if rt == 'rectangle':
            item.setPen(QPen(Qt.GlobalColor.red, 3))
        elif rt == 'text':
            item.setDefaultTextColor(Qt.GlobalColor.red)
        elif rt == 'arrow':
            item.setPen(QPen(Qt.GlobalColor.red, item.pen().width() + 2))

    def _unhighlight(self, item):
        data = item.data(0) or {}
        rt = data.get('render_type')
        if rt == 'rectangle':
            item.setPen(QPen(Qt.GlobalColor.black, 2))
        elif rt == 'text':
            item.setDefaultTextColor(Qt.GlobalColor.black)
        elif rt == 'arrow':
            color = FORECOLOR_MAPPING.get(data.get('ForeColor', 'Black'), FORECOLOR_MAPPING["default"])
            line_thick = int((data.get('LineThick') or 1))
            item.setPen(QPen(color, line_thick))

    def _show_info(self, item):
        data = item.data(0) or {}
        full_type = data.get('type', 'Unknown')
        type_name = full_type.split(',')[0].split('.')[-1] if full_type else 'Unknown'
        info = [
            f"<b>Object Name:</b> {data.get('name','N/A')}",
            f"<b>Type:</b> {type_name}",
            f"<b>Render As:</b> {data.get('render_type','N/A')}",
            f"<b>Location:</b> {data.get('location','N/A')}",
            f"<b>Size:</b> {data.get('size','N/A')}",
        ]
        if data.get('text'):   info.append(f"<b>Text:</b> {data.get('text')}")
        if data.get('UnitId'): info.append(f"<b>UnitId:</b> {data.get('UnitId')}")
        if data.get('render_type') == 'arrow':
            for k in ("FlowDirection","LineThick","EndCap","ForeColor"):
                if data.get(k): info.append(f"<b>{k}:</b> {data.get(k)}")
        self.info_box.setText("<br>".join(info))
        self.info_box.adjustSize()
        margin = 10
        self.info_box.move(self.width() - self.info_box.width() - margin, margin)
        self.info_box.show()
