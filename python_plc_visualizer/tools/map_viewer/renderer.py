# map_viewer/renderer.py
import logging
import math
from typing import Dict, Any, Optional, Tuple

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QPen, QBrush, QFont, QPainterPath, QPolygonF
from PySide6.QtWidgets import QGraphicsView, QGraphicsScene, QLabel

from .config import (
    RENDER_AS_TEXT_TYPES, RENDER_AS_ARROW_TYPES, RENDER_AS_ARROWED_RECTANGLE_TYPES,
    TYPE_COLOR_MAPPING, TYPE_ZINDEX_MAPPING, FORECOLOR_MAPPING
)

logger = logging.getLogger(__name__)

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

def _parse_belt_direction(belt_direction_str: Optional[str]) -> float:
    """
    Parse BeltDirection (North, South, East, West) to angle in radians.
    North = 0° (up), East = 90° (right), South = 180° (down), West = 270° (left)
    Returns angle in radians for standard coordinate system.
    """
    if not belt_direction_str:
        return math.radians(0)  # Default North
    
    direction_map = {
        "North": 270,  # Up in screen coordinates
        "South": 90,   # Down in screen coordinates
        "East": 0,     # Right
        "West": 180,   # Left
    }
    
    deg = direction_map.get(belt_direction_str.strip(), 270)  # Default to North
    return math.radians(deg)

class MapRenderer(QGraphicsView):
    """
    Standalone renderer. Public API:
      - set_objects(objects: dict) -> None
      - update_rect_color_by_unit(unit_id: str, color: QColor, text_overlay_info: Optional[tuple]) -> int
        where text_overlay_info is (character, text_color) or None
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
        # index: UnitId -> text overlay item (if any)
        self._text_overlays_by_unit: Dict[str, Any] = {}
        # index: UnitId -> arrow overlay item (if any)
        self._arrow_overlays_by_unit: Dict[str, Any] = {}
        # object bounds cache for alignment debugging
        self._object_bounds: Dict[str, Dict[str, Any]] = {}
        
        # Reference to state model for carrier info display
        self._state_model: Optional[Any] = None

    # ---------- Public API ----------
    def set_objects(self, objects: Dict[str, Dict[str, Any]]) -> None:
        """Render parsed objects into the scene."""
        self.scene.clear()
        self._items_by_unit.clear()
        self._text_overlays_by_unit.clear()
        self._arrow_overlays_by_unit.clear()
        self._object_bounds.clear()

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
                    self._log_arrow_alignment(name, x, y, width, height, arrow_data)

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

            elif obj_type in RENDER_AS_ARROWED_RECTANGLE_TYPES:
                # Arrowed rectangle: rectangle + arrow overlay
                belt_direction = data.get("BeltDirection")
                rect = self.scene.addRect(x, y, width, height)
                rect.setPen(QPen(Qt.GlobalColor.black, 2))
                rect.setBrush(QBrush(color))
                rect.setZValue(z_index)
                payload = {
                    'name': name, 'type': obj_type, 'size': size_str, 'location': loc_str,
                    'render_type': 'arrowed_rectangle', 'UnitId': unit_id,
                    'BeltDirection': belt_direction
                }
                rect.setData(0, payload)
                rect.setFlag(rect.GraphicsItemFlag.ItemIsSelectable)
                self._index_unit_item(unit_id, rect)
                self._object_bounds[name] = {
                    "rect": (x, y, width, height),
                    "unit_id": unit_id,
                    "type": obj_type
                }
                
                # Create arrow overlay
                if belt_direction:
                    arrow_item = self._create_arrow_overlay(x, y, width, height, belt_direction, z_index + 0.5)
                    if arrow_item:
                        arrow_item.setData(0, payload)
                        arrow_item.setFlag(arrow_item.GraphicsItemFlag.ItemIsSelectable)
                        if unit_id:
                            self._arrow_overlays_by_unit[unit_id] = arrow_item
            
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
                self._object_bounds[name] = {
                    "rect": (x, y, width, height),
                    "unit_id": unit_id,
                    "type": obj_type
                }

        self.fitInView(self.scene.itemsBoundingRect(), Qt.AspectRatioMode.KeepAspectRatio)
    
    def set_state_model(self, state_model: Any) -> None:
        """Set the state model for carrier tracking info display.
        
        Args:
            state_model: UnitStateModel instance
        """
        self._state_model = state_model

    def update_rect_color_by_unit(self, unit_id: str, block_color: Optional[QColor] = None,
                                   arrow_color: Optional[QColor] = None,
                                   text_overlay_info: Optional[tuple[str, QColor]] = None) -> int:
        """
        Update the colors of rectangle(s) and arrow overlays sharing a UnitId.
        - block_color: color for rectangle background (None means no change)
        - arrow_color: color for arrow overlay (None means no change)
        - text_overlay_info: (character, text_color) or None
        Returns the number of items changed.
        """
        items = self._items_by_unit.get(unit_id) or []
        changed = 0
        rect_items = []

        for it in items:
            data = it.data(0) or {}
            render_type = data.get('render_type')
            if render_type in ('rectangle', 'arrowed_rectangle'):
                # Use block_color if provided, otherwise restore default gray
                color_to_use = block_color if block_color is not None else QColor(211, 211, 211)
                it.setBrush(QBrush(color_to_use))
                changed += 1
                rect_items.append(it)

        # Handle arrow overlay color for arrowed rectangles
        if arrow_color is not None and unit_id in self._arrow_overlays_by_unit:
            arrow_item = self._arrow_overlays_by_unit[unit_id]
            arrow_item.setPen(QPen(arrow_color, 3))
            changed += 1

        # Handle text overlay
        if text_overlay_info and rect_items:
            character, text_color = text_overlay_info
            # Use the first rectangle for overlay (typically only one per unit_id)
            self._add_or_update_text_overlay(unit_id, rect_items[0], character, text_color)
        else:
            # Remove text overlay if exists
            self._remove_text_overlay(unit_id)

        return changed
    
    def highlight_unit(self, unit_id: str) -> bool:
        """Highlight a unit by its UnitId and center the view on it.
        
        Args:
            unit_id: The UnitId to highlight
            
        Returns:
            True if unit was found and highlighted, False otherwise
        """
        items = self._items_by_unit.get(unit_id)
        if not items:
            return False
        
        # Clear previous selection
        if self.selected_item:
            self._unhighlight(self.selected_item)
        
        # Highlight the first item for this unit
        first_item = items[0]
        self._highlight(first_item)
        self.selected_item = first_item
        
        # Show info box
        self._show_info(first_item)
        
        # Center view on the item
        self.centerOn(first_item)
        
        return True

    # ---------- Internals ----------
    def _index_unit_item(self, unit_id: Optional[str], item):
        if not unit_id:
            return
        self._items_by_unit.setdefault(unit_id, []).append(item)

    def _add_or_update_text_overlay(self, unit_id: str, rect_item, character: str, text_color: QColor):
        """Create or update a text overlay for a rectangle item.
        
        Args:
            unit_id: The unit ID
            rect_item: The rectangle item to overlay text on
            character: The text to display (may contain newlines for multi-carrier)
            text_color: The color of the text
        """
        # Get rectangle bounds
        rect = rect_item.rect()
        rect_x = rect.x()
        rect_y = rect.y()
        rect_width = rect.width()
        rect_height = rect.height()

        # Remove existing overlay if any
        self._remove_text_overlay(unit_id)
        
        # Check if multi-line text
        lines = character.split('\n')
        num_lines = len(lines)
        
        # For multi-line, truncate each line from start (prioritize unique suffix)
        max_chars_per_line = 12  # Reasonable limit per line
        display_lines = []
        for line in lines:
            if len(line) > max_chars_per_line:
                display_lines.append('...' + line[-(max_chars_per_line-3):])
            else:
                display_lines.append(line)
        display_text = '\n'.join(display_lines)
        
        # Create text item
        font = QFont("Arial", 12)
        font.setBold(True)
        
        text_item = self.scene.addText(display_text)
        text_item.setDefaultTextColor(text_color)
        text_item.setFont(font)
        
        # Measure text
        text_bounds = text_item.boundingRect()
        
        # Scale to fit 90% of rectangle (leaving margin)
        available_width = rect_width * 0.9
        available_height = rect_height * 0.9
        
        scale_x = available_width / text_bounds.width() if text_bounds.width() > 0 else 1.0
        scale_y = available_height / text_bounds.height() if text_bounds.height() > 0 else 1.0
        
        # Use the smaller scale to maintain aspect ratio and fit within rectangle
        scale_factor = min(scale_x, scale_y, 2.0)  # Cap at 2x to prevent overly large text
        text_item.setScale(scale_factor)
        
        # Center the text in the rectangle
        scaled_width = text_bounds.width() * scale_factor
        scaled_height = text_bounds.height() * scale_factor
        center_x = rect_x + (rect_width - scaled_width) / 2
        center_y = rect_y + (rect_height - scaled_height) / 2
        text_item.setPos(center_x, center_y)

        # Set Z-index higher than rectangles
        text_item.setZValue(rect_item.zValue() + 1)

        # Store reference
        self._text_overlays_by_unit[unit_id] = text_item

    def _remove_text_overlay(self, unit_id: str):
        """Remove text overlay for a unit if it exists."""
        if unit_id in self._text_overlays_by_unit:
            text_item = self._text_overlays_by_unit[unit_id]
            self.scene.removeItem(text_item)
            del self._text_overlays_by_unit[unit_id]

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

    def _create_arrow_overlay(self, x: float, y: float, width: float, height: float, 
                              belt_direction: str, z_index: float) -> Any:
        """Create a directional arrow overlay for a belt rectangle."""
        angle_rad = _parse_belt_direction(belt_direction)
        
        # Arrow should be smaller than the rectangle to fit nicely
        # Use 60% of the smaller dimension for arrow length
        arrow_length = min(width, height) * 0.6
        arrow_width = arrow_length * 0.3  # Arrowhead width
        
        # Center of rectangle
        cx = x + width / 2.0
        cy = y + height / 2.0
        
        # Calculate arrow line endpoints based on direction
        dx = math.cos(angle_rad)
        dy = math.sin(angle_rad)
        
        # Start and end points of arrow (centered on rectangle)
        half_len = arrow_length / 2.0
        start = QPointF(cx - dx * half_len, cy - dy * half_len)
        end = QPointF(cx + dx * half_len, cy + dy * half_len)
        
        # Create arrow path
        path = QPainterPath()
        path.moveTo(start)
        path.lineTo(end)
        
        # Create arrow with a visible but subtle style
        pen = QPen(QColor(100, 100, 100), 3)  # Default gray, will be updated by color rules
        arrow_item = self.scene.addPath(path, pen)
        arrow_item.setZValue(z_index)
        
        # Add arrowhead
        arrow_size = arrow_width
        theta = math.atan2(end.y() - start.y(), end.x() - start.x())
        wing = math.radians(30)
        left_ang = theta + math.pi - wing
        right_ang = theta + math.pi + wing
        p_left = QPointF(end.x() + arrow_size * math.cos(left_ang),
                         end.y() + arrow_size * math.sin(left_ang))
        p_right = QPointF(end.x() + arrow_size * math.cos(right_ang),
                          end.y() + arrow_size * math.sin(right_ang))
        head = QPolygonF([end, p_left, p_right])
        head_item = self.scene.addPolygon(head, pen, QBrush(QColor(100, 100, 100)))
        head_item.setZValue(z_index)
        
        # Group arrow line and head together (we'll just track the main arrow_item)
        # In a more sophisticated implementation, we'd use QGraphicsItemGroup
        return arrow_item

    def _closest_rect(self, point: QPointF) -> Optional[Tuple[str, Dict[str, Any], float, float]]:
        best: Optional[Tuple[str, Dict[str, Any], float, float, float]] = None
        px, py = point.x(), point.y()
        for name, info in self._object_bounds.items():
            bx, by, bw, bh = info["rect"]
            if bw <= 0 or bh <= 0:
                continue

            gap_x = 0.0
            if px < bx:
                gap_x = bx - px
            elif px > bx + bw:
                gap_x = px - (bx + bw)

            gap_y = 0.0
            if py < by:
                gap_y = by - py
            elif py > by + bh:
                gap_y = py - (by + bh)

            metric = max(gap_x, gap_y)
            if best is None or metric < best[4] or (
                metric == best[4] and (gap_x + gap_y) < (best[2] + best[3])
            ):
                best = (name, info, gap_x, gap_y, metric)

        if best is None:
            return None
        name, info, gap_x, gap_y, _ = best
        return name, info, gap_x, gap_y

    def _format_point_info(self, info: Optional[Tuple[str, Dict[str, Any], float, float]]) -> str:
        if not info:
            return "None"
        name, rect_info, gap_x, gap_y = info
        bx, by, bw, bh = rect_info["rect"]
        unit = rect_info.get("unit_id") or "—"
        inside = gap_x == 0.0 and gap_y == 0.0
        return (
            f"{name}(unit={unit}) rect=({bx}, {by}, {bw}, {bh}) "
            f"gap_x={gap_x:.1f} gap_y={gap_y:.1f} inside={inside}"
        )

    def _log_arrow_alignment(self, name: str, x: float, y: float, width: float,
                             height: float, data: Dict[str, Any]) -> None:
        flow_direction = data.get("FlowDirection", "Angle_0") or "Angle_0"
        angle_rad, axis = _parse_flow_direction(flow_direction)
        cx = x + width / 2.0
        cy = y + height / 2.0

        if axis == "right":
            start = QPointF(x, cy)
            end = QPointF(x + width, cy)
        elif axis == "left":
            start = QPointF(x + width, cy)
            end = QPointF(x, cy)
        elif axis == "down":
            start = QPointF(cx, y)
            end = QPointF(cx, y + height)
        elif axis == "up":
            start = QPointF(cx, y + height)
            end = QPointF(cx, y)
        else:
            dx = math.cos(angle_rad)
            dy = math.sin(angle_rad)
            L = math.hypot(width, height)
            center = QPointF(cx, cy)
            start = QPointF(center.x() - dx * L, center.y() - dy * L)
            end = QPointF(center.x() + dx * L, center.y() + dy * L)

        tail = self._closest_rect(start)
        head = self._closest_rect(end)
        logger.info(
            "Arrow %s axis=%s start=(%.1f, %.1f) end=(%.1f, %.1f) tail=%s head=%s",
            name,
            axis,
            start.x(), start.y(),
            end.x(), end.y(),
            self._format_point_info(tail),
            self._format_point_info(head)
        )

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
        if rt in ('rectangle', 'arrowed_rectangle'):
            item.setPen(QPen(Qt.GlobalColor.red, 3))
        elif rt == 'text':
            item.setDefaultTextColor(Qt.GlobalColor.red)
        elif rt == 'arrow':
            item.setPen(QPen(Qt.GlobalColor.red, item.pen().width() + 2))

    def _unhighlight(self, item):
        data = item.data(0) or {}
        rt = data.get('render_type')
        if rt in ('rectangle', 'arrowed_rectangle'):
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
        if data.get('UnitId'): 
            unit_id = data.get('UnitId')
            info.append(f"<b>UnitId:</b> {unit_id}")
            
            # Show carrier information if carrier tracking is enabled
            if self._state_model and hasattr(self._state_model, 'enable_carrier_tracking'):
                if self._state_model.enable_carrier_tracking:
                    carriers = self._state_model.get_carriers_at_unit(unit_id)
                    if carriers:
                        # Show carrier list
                        carrier_list = ", ".join(carriers)
                        info.append(f"<b>Carriers:</b> {carrier_list}")
                        # Show count if multiple
                        if len(carriers) > 1:
                            info.append(f"<b>Carrier Count:</b> {len(carriers)}")
        
        if data.get('render_type') == 'arrow':
            for k in ("FlowDirection","LineThick","EndCap","ForeColor"):
                if data.get(k): info.append(f"<b>{k}:</b> {data.get(k)}")
        self.info_box.setText("<br>".join(info))
        self.info_box.adjustSize()
        margin = 10
        self.info_box.move(self.width() - self.info_box.width() - margin, margin)
        self.info_box.show()
