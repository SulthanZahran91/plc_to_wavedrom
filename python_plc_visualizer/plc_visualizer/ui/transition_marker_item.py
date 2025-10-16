"""Graphics item representing a clickable transition marker on a waveform."""

from __future__ import annotations

from typing import Callable, Optional

from PyQt6.QtWidgets import QGraphicsPathItem, QToolTip
from PyQt6.QtGui import QPainterPath, QPen, QColor
from PyQt6.QtCore import Qt, QPoint, QPointF, QEvent


class TransitionMarkerItem(QGraphicsPathItem):
    """Thin vertical marker that responds to hover/click events."""

    def __init__(
        self,
        marker_height: float,
        color: QColor,
        tooltip_text: str,
        click_callback: Optional[Callable[["TransitionMarkerItem"], None]] = None,
        parent=None
    ):
        path = QPainterPath()
        path.moveTo(QPointF(0.0, 0.0))
        path.lineTo(QPointF(0.0, marker_height))
        super().__init__(path, parent)

        self._default_pen = QPen(color)
        self._default_pen.setWidthF(2.0)

        hover_color = QColor(color)
        hover_color.setAlpha(min(color.alpha() + 80, 255))
        self._hover_pen = QPen(hover_color)
        self._hover_pen.setWidthF(3.0)

        active_color = QColor(color)
        active_color = active_color.lighter(120)
        self._active_pen = QPen(active_color)
        self._active_pen.setWidthF(3.5)

        self._click_callback = click_callback
        self._info_text = tooltip_text
        self._active = False
        self._marker_height = marker_height

        self.setPen(self._default_pen)
        self.setAcceptHoverEvents(True)
        self.setAcceptedMouseButtons(Qt.MouseButton.LeftButton)
        self.setZValue(5.0)  # Ensure marker stays above waveform line

    def set_active(self, active: bool):
        """Toggle active highlight state."""
        self._active = active
        self.setPen(self._active_pen if active else self._default_pen)

    def is_active(self) -> bool:
        return self._active

    # Expand hit area beyond the 0-width line for easier interaction
    def shape(self) -> QPainterPath:  # noqa: D401 - overriding Qt method
        path = QPainterPath()
        path.addRect(-6.0, -6.0, 12.0, self._marker_height + 12.0)
        return path

    def hoverEnterEvent(self, event: QEvent):
        if not self._active:
            self.setPen(self._hover_pen)
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event: QEvent):
        if not self._active:
            self.setPen(self._default_pen)
        super().hoverLeaveEvent(event)

    def mousePressEvent(self, event):
        if self._info_text:
            screen_pos = event.screenPos()
            if isinstance(screen_pos, QPointF):
                tooltip_pos = screen_pos.toPoint()
            elif isinstance(screen_pos, QPoint):
                tooltip_pos = screen_pos
            else:
                try:
                    tooltip_pos = QPoint(int(screen_pos.x()), int(screen_pos.y()))
                except AttributeError:
                    tooltip_pos = QPoint()
            QToolTip.showText(tooltip_pos, self._info_text)

        if self._click_callback:
            self._click_callback(self)

        event.accept()
        super().mousePressEvent(event)
