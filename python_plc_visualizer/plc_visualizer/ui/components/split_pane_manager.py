"""Split pane manager for organizing multiple views in a tabbed/split layout."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout, QSplitter, QMessageBox

from .view_tab_widget import ViewTabWidget


class SplitPaneManager(QWidget):
    """Manages up to 4 panes with tabbed views and split functionality.
    
    Supports various configurations:
    - 1 pane (full window)
    - 2 panes (horizontal or vertical split)
    - 3 panes (various combinations)
    - 4 panes (2x2 grid or other layouts)
    """

    active_pane_changed = Signal(int)  # pane_index
    view_closed = Signal(QWidget)  # view_widget

    MAX_PANES = 4

    def __init__(self, parent=None):
        super().__init__(parent)
        self._panes: list[ViewTabWidget] = []
        self._active_pane_index: int = 0
        self._root_splitter: Optional[QSplitter] = None
        
        self._init_ui()

    def _init_ui(self):
        """Initialize the UI with a single pane."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Start with a single pane
        initial_pane = self._create_pane()
        self._panes.append(initial_pane)
        layout.addWidget(initial_pane)

    def _create_pane(self) -> ViewTabWidget:
        """Create a new tab widget pane."""
        pane = ViewTabWidget(self)
        pane.tab_drag_to_edge.connect(self._on_tab_drag_to_edge)
        pane.tab_closed.connect(self._on_tab_closed)
        pane.currentChanged.connect(lambda: self._on_pane_focused(pane))
        return pane

    def add_view(self, view_widget: QWidget, title: str, pane_index: Optional[int] = None) -> bool:
        """Add a view to the specified pane (or active pane if None).
        
        Args:
            view_widget: The widget to add as a tab
            title: Tab title
            pane_index: Target pane index, or None for active pane
            
        Returns:
            True if added successfully, False otherwise
        """
        if pane_index is None:
            pane_index = self._active_pane_index

        if pane_index < 0 or pane_index >= len(self._panes):
            return False

        pane = self._panes[pane_index]
        tab_index = pane.addTab(view_widget, title)
        pane.setCurrentIndex(tab_index)
        self._active_pane_index = pane_index
        self.active_pane_changed.emit(pane_index)
        return True

    def get_active_pane_index(self) -> int:
        """Get the index of the currently active pane."""
        return self._active_pane_index

    def get_pane_count(self) -> int:
        """Get the number of panes currently displayed."""
        return len(self._panes)

    def get_all_views(self) -> list[QWidget]:
        """Get all view widgets across all panes."""
        views = []
        for pane in self._panes:
            for i in range(pane.count()):
                widget = pane.widget(i)
                if widget:
                    views.append(widget)
        return views

    def get_active_view(self) -> Optional[QWidget]:
        """Get the currently active view widget."""
        if self._active_pane_index < 0 or self._active_pane_index >= len(self._panes):
            return None
        
        pane = self._panes[self._active_pane_index]
        return pane.currentWidget()

    def split_pane(self, orientation: Qt.Orientation, source_pane_index: int) -> bool:
        """Split the specified pane into two panes.
        
        Args:
            orientation: Qt.Horizontal (top/bottom) or Qt.Vertical (left/right)
            source_pane_index: Index of pane to split
            
        Returns:
            True if split successful, False if max panes reached
        """
        if len(self._panes) >= self.MAX_PANES:
            QMessageBox.warning(
                self,
                "Maximum Panes Reached",
                f"Cannot split further. Maximum of {self.MAX_PANES} panes allowed."
            )
            return False

        if source_pane_index < 0 or source_pane_index >= len(self._panes):
            return False

        # Create new pane
        new_pane = self._create_pane()
        
        # If we only have one pane, create the initial split
        if len(self._panes) == 1:
            self._create_initial_split(orientation, new_pane)
        else:
            # Find and split the existing pane
            self._split_existing_pane(source_pane_index, orientation, new_pane)

        self._panes.append(new_pane)
        self._active_pane_index = len(self._panes) - 1
        self.active_pane_changed.emit(self._active_pane_index)
        return True

    def _create_initial_split(self, orientation: Qt.Orientation, new_pane: ViewTabWidget):
        """Create the first split from a single pane."""
        # Remove the single pane from layout
        old_pane = self._panes[0]
        layout = self.layout()
        layout.removeWidget(old_pane)

        # Create splitter
        self._root_splitter = QSplitter(orientation, self)
        self._root_splitter.addWidget(old_pane)
        self._root_splitter.addWidget(new_pane)
        self._root_splitter.setChildrenCollapsible(False)
        
        # Set equal sizes
        self._root_splitter.setSizes([500, 500])
        
        layout.addWidget(self._root_splitter)

    def _split_existing_pane(self, source_index: int, orientation: Qt.Orientation, new_pane: ViewTabWidget):
        """Split an existing pane within the current splitter hierarchy."""
        source_pane = self._panes[source_index]
        
        # Find parent splitter
        parent = source_pane.parent()
        if not isinstance(parent, QSplitter):
            return

        # Get index of source pane in parent splitter
        pane_index_in_splitter = parent.indexOf(source_pane)
        if pane_index_in_splitter < 0:
            return

        # Create new splitter for this split
        new_splitter = QSplitter(orientation, parent)
        new_splitter.setChildrenCollapsible(False)
        
        # Remove source pane from parent
        source_pane.setParent(None)
        
        # Add source and new pane to new splitter
        new_splitter.addWidget(source_pane)
        new_splitter.addWidget(new_pane)
        new_splitter.setSizes([500, 500])
        
        # Insert new splitter at the same position
        parent.insertWidget(pane_index_in_splitter, new_splitter)

    def merge_pane(self, pane_index: int) -> bool:
        """Remove a pane and merge its tabs into another pane.
        
        Args:
            pane_index: Index of pane to remove
            
        Returns:
            True if merged successfully, False otherwise
        """
        if len(self._panes) <= 1:
            # Can't merge the last pane
            return False

        if pane_index < 0 or pane_index >= len(self._panes):
            return False

        pane_to_remove = self._panes[pane_index]
        
        # Move all tabs to the first remaining pane (that isn't the one being removed)
        target_pane_index = 0 if pane_index != 0 else 1
        target_pane = self._panes[target_pane_index]
        
        # Transfer tabs
        while pane_to_remove.count() > 0:
            widget = pane_to_remove.widget(0)
            title = pane_to_remove.tabText(0)
            pane_to_remove.removeTab(0)
            if widget:
                target_pane.addTab(widget, title)

        # Remove pane from list
        self._panes.pop(pane_index)
        
        # Remove widget from UI hierarchy
        parent = pane_to_remove.parent()
        if isinstance(parent, QSplitter):
            # If parent splitter now has only one child, collapse it
            if parent.count() == 1:
                self._collapse_splitter(parent)

        pane_to_remove.deleteLater()
        
        # Update active pane
        if self._active_pane_index >= len(self._panes):
            self._active_pane_index = len(self._panes) - 1
        self.active_pane_changed.emit(self._active_pane_index)
        
        return True

    def _collapse_splitter(self, splitter: QSplitter):
        """Remove a splitter that has only one child."""
        if splitter.count() != 1:
            return

        remaining_widget = splitter.widget(0)
        parent = splitter.parent()

        if isinstance(parent, QSplitter):
            # Get index in grandparent
            index_in_parent = parent.indexOf(splitter)
            if index_in_parent >= 0:
                remaining_widget.setParent(None)
                splitter.deleteLater()
                parent.insertWidget(index_in_parent, remaining_widget)
        elif isinstance(parent, QWidget):
            # Root splitter case
            layout = parent.layout()
            if layout:
                remaining_widget.setParent(None)
                layout.removeWidget(splitter)
                splitter.deleteLater()
                layout.addWidget(remaining_widget)
                self._root_splitter = None

    def _on_tab_drag_to_edge(self, orientation: Qt.Orientation, widget: QWidget, tab_index: int):
        """Handle tab dragged to edge of pane - create a split."""
        # Find which pane emitted this signal
        sender_pane = self.sender()
        if not isinstance(sender_pane, ViewTabWidget):
            return

        try:
            source_pane_index = self._panes.index(sender_pane)
        except ValueError:
            return

        # Remove tab from source pane
        sender_pane.removeTab(tab_index)

        # Create split
        if self.split_pane(orientation, source_pane_index):
            # Add widget to new pane
            new_pane = self._panes[-1]
            new_pane.addTab(widget, widget.windowTitle() or "View")

    def _on_tab_closed(self, widget: QWidget):
        """Handle tab close event."""
        self.view_closed.emit(widget)
        
        # Check if any pane is now empty and remove it
        for i in range(len(self._panes) - 1, -1, -1):
            if self._panes[i].count() == 0 and len(self._panes) > 1:
                self.merge_pane(i)

    def _on_pane_focused(self, pane: ViewTabWidget):
        """Update active pane when user interacts with it."""
        try:
            self._active_pane_index = self._panes.index(pane)
            self.active_pane_changed.emit(self._active_pane_index)
        except ValueError:
            pass

