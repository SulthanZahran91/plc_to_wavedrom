"""Custom tab widget with drag-to-split functionality."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, Signal, QPoint, QRect
from PySide6.QtGui import QDrag, QPainter, QColor, QPen, QMouseEvent
from PySide6.QtWidgets import QTabWidget, QTabBar, QWidget, QMenu


class ViewTabBar(QTabBar):
    """Custom tab bar that enables drag detection for splitting."""

    drag_started = Signal(int, QPoint)  # tab_index, global_pos

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setMovable(True)
        self._drag_start_pos: Optional[QPoint] = None
        self._dragging_tab_index: int = -1

    def mousePressEvent(self, event: QMouseEvent):
        """Capture the starting position for drag detection."""
        if event.button() == Qt.LeftButton:
            self._drag_start_pos = event.pos()
            self._dragging_tab_index = self.tabAt(event.pos())
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        """Detect drag motion and emit signal if threshold exceeded."""
        if not (event.buttons() & Qt.LeftButton):
            super().mouseMoveEvent(event)
            return

        if self._drag_start_pos is None:
            super().mouseMoveEvent(event)
            return

        # Check if we've moved enough to start a drag
        if (event.pos() - self._drag_start_pos).manhattanLength() < 20:
            super().mouseMoveEvent(event)
            return

        # Only emit drag signal if we have a valid tab
        if self._dragging_tab_index >= 0:
            self.drag_started.emit(self._dragging_tab_index, event.globalPosition().toPoint())

        self._drag_start_pos = None
        self._dragging_tab_index = -1
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        """Reset drag state on release."""
        self._drag_start_pos = None
        self._dragging_tab_index = -1
        super().mouseReleaseEvent(event)


class ViewTabWidget(QTabWidget):
    """Tab widget with drag-to-split capabilities and drop zone indicators."""

    tab_drag_to_edge = Signal(Qt.Orientation, QWidget, int)  # orientation, widget, original_tab_index
    tab_closed = Signal(QWidget)  # widget
    drop_zone_entered = Signal(Qt.Orientation)  # orientation
    drop_zone_exited = Signal()

    # Drop zone size in pixels
    DROP_ZONE_SIZE = 40

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTabsClosable(True)
        self.setMovable(True)
        self.setAcceptDrops(True)
        self.setDocumentMode(True)

        # Use custom tab bar
        custom_bar = ViewTabBar(self)
        self.setTabBar(custom_bar)
        custom_bar.drag_started.connect(self._on_tab_drag_started)

        # Connect close signal
        self.tabCloseRequested.connect(self._on_tab_close_requested)

        # Drop zone state
        self._drop_zone_active: Optional[Qt.Orientation] = None
        self._drag_widget: Optional[QWidget] = None
        self._drag_tab_index: int = -1

    def _on_tab_drag_started(self, tab_index: int, global_pos: QPoint):
        """Handle when a tab drag is initiated."""
        if tab_index < 0 or tab_index >= self.count():
            return

        self._drag_widget = self.widget(tab_index)
        self._drag_tab_index = tab_index

    def _on_tab_close_requested(self, index: int):
        """Handle tab close button click."""
        widget = self.widget(index)
        if widget:
            self.removeTab(index)
            self.tab_closed.emit(widget)

    def dragEnterEvent(self, event):
        """Accept drag events."""
        event.accept()

    def dragMoveEvent(self, event):
        """Track drag position and highlight drop zones."""
        pos = event.position().toPoint()
        rect = self.rect()

        # Determine which drop zone we're in
        new_zone = None
        if pos.x() < self.DROP_ZONE_SIZE:
            new_zone = Qt.Vertical  # Left edge = vertical split
        elif pos.x() > rect.width() - self.DROP_ZONE_SIZE:
            new_zone = Qt.Vertical  # Right edge = vertical split
        elif pos.y() < self.DROP_ZONE_SIZE:
            new_zone = Qt.Horizontal  # Top edge = horizontal split
        elif pos.y() > rect.height() - self.DROP_ZONE_SIZE:
            new_zone = Qt.Horizontal  # Bottom edge = horizontal split

        # Update drop zone state
        if new_zone != self._drop_zone_active:
            if new_zone is not None:
                self.drop_zone_entered.emit(new_zone)
            else:
                self.drop_zone_exited.emit()
            self._drop_zone_active = new_zone
            self.update()

        event.accept()

    def dragLeaveEvent(self, event):
        """Clear drop zone highlighting when drag leaves."""
        if self._drop_zone_active is not None:
            self.drop_zone_exited.emit()
            self._drop_zone_active = None
            self.update()
        event.accept()

    def dropEvent(self, event):
        """Handle drop and emit split signal if in a drop zone."""
        if self._drop_zone_active is not None and self._drag_widget is not None:
            # Emit signal to split this pane
            self.tab_drag_to_edge.emit(
                self._drop_zone_active,
                self._drag_widget,
                self._drag_tab_index
            )
            event.accept()
        else:
            event.ignore()

        # Reset state
        self._drop_zone_active = None
        self._drag_widget = None
        self._drag_tab_index = -1
        self.update()

    def paintEvent(self, event):
        """Draw drop zone indicators when active."""
        super().paintEvent(event)

        if self._drop_zone_active is not None:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)

            # Semi-transparent blue overlay
            color = QColor(66, 133, 244, 80)  # Google Blue with alpha
            painter.fillRect(self._get_drop_zone_rect(), color)

            # Border
            pen = QPen(QColor(66, 133, 244), 2)
            painter.setPen(pen)
            painter.drawRect(self._get_drop_zone_rect())

            painter.end()

    def _get_drop_zone_rect(self) -> QRect:
        """Get the rectangle for the current drop zone."""
        rect = self.rect()
        zone_size = self.DROP_ZONE_SIZE

        if self._drop_zone_active == Qt.Vertical:
            # Left or right edge
            if self.mapFromGlobal(self.cursor().pos()).x() < rect.width() / 2:
                return QRect(0, 0, zone_size, rect.height())
            else:
                return QRect(rect.width() - zone_size, 0, zone_size, rect.height())
        elif self._drop_zone_active == Qt.Horizontal:
            # Top or bottom edge
            if self.mapFromGlobal(self.cursor().pos()).y() < rect.height() / 2:
                return QRect(0, 0, rect.width(), zone_size)
            else:
                return QRect(0, rect.height() - zone_size, rect.width(), zone_size)

        return QRect()

    def contextMenuEvent(self, event):
        """Show context menu on right-click."""
        tab_index = self.tabBar().tabAt(event.pos())
        if tab_index < 0:
            return

        widget = self.widget(tab_index)
        if not widget:
            return

        menu = QMenu(self)
        close_action = menu.addAction("Close Tab")
        close_other_action = menu.addAction("Close Other Tabs")
        close_all_action = menu.addAction("Close All Tabs")

        action = menu.exec(event.globalPos())

        if action == close_action:
            self.removeTab(tab_index)
            self.tab_closed.emit(widget)
        elif action == close_other_action:
            # Close all except this one
            for i in range(self.count() - 1, -1, -1):
                if i != tab_index:
                    w = self.widget(i)
                    self.removeTab(i)
                    if w:
                        self.tab_closed.emit(w)
        elif action == close_all_action:
            # Close all tabs
            for i in range(self.count() - 1, -1, -1):
                w = self.widget(i)
                self.removeTab(i)
                if w:
                    self.tab_closed.emit(w)

