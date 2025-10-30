"""Dialog for managing and navigating time bookmarks."""

from __future__ import annotations

from typing import Callable, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QAbstractItemView,
    QInputDialog,
    QMessageBox,
    QWidget,
)

from plc_visualizer.models import TimeBookmark


class BookmarkDialog(QDialog):
    """Dialog for browsing, adding, and deleting bookmarks.
    
    Signals:
        bookmark_selected: Emitted when user selects a bookmark to jump to (index)
    """

    bookmark_selected = Signal(int)  # bookmark index

    def __init__(
        self,
        bookmarks: list[TimeBookmark],
        add_callback: Optional[Callable[[str, str], None]] = None,
        delete_callback: Optional[Callable[[int], None]] = None,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self._bookmarks = bookmarks
        self._add_callback = add_callback
        self._delete_callback = delete_callback
        self._auto_close = True  # Auto-close after selection

        self._init_ui()
        self._populate_table()

    def _init_ui(self):
        """Initialize the UI."""
        self.setWindowTitle("Time Bookmarks")
        self.setMinimumSize(700, 400)
        
        layout = QVBoxLayout(self)
        
        # Table widget
        self.table = QTableWidget(self)
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Timestamp", "Label", "Description"])
        
        # Configure table
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        
        # Resize columns
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        
        # Connect double-click to jump
        self.table.itemDoubleClicked.connect(self._on_table_double_click)
        
        layout.addWidget(self.table)
        
        # Button layout
        button_layout = QHBoxLayout()
        
        # Add button
        if self._add_callback:
            add_btn = QPushButton("Add Bookmark", self)
            add_btn.clicked.connect(self._on_add_clicked)
            button_layout.addWidget(add_btn)
        
        # Delete button
        if self._delete_callback:
            delete_btn = QPushButton("Delete", self)
            delete_btn.clicked.connect(self._on_delete_clicked)
            button_layout.addWidget(delete_btn)
        
        button_layout.addStretch()
        
        # Jump button
        jump_btn = QPushButton("Jump to Selected", self)
        jump_btn.setDefault(True)
        jump_btn.clicked.connect(self._on_jump_clicked)
        button_layout.addWidget(jump_btn)
        
        # Close button
        close_btn = QPushButton("Close", self)
        close_btn.clicked.connect(self.reject)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
        
        # Keyboard shortcuts
        self.table.installEventFilter(self)

    def _populate_table(self):
        """Populate the table with bookmarks."""
        self.table.setRowCount(len(self._bookmarks))
        
        for row, bookmark in enumerate(self._bookmarks):
            # Timestamp column
            timestamp_item = QTableWidgetItem(bookmark.timestamp.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3])
            self.table.setItem(row, 0, timestamp_item)
            
            # Label column
            label_item = QTableWidgetItem(bookmark.label)
            self.table.setItem(row, 1, label_item)
            
            # Description column
            desc_item = QTableWidgetItem(bookmark.description)
            self.table.setItem(row, 2, desc_item)
        
        # Select first row if available
        if self.table.rowCount() > 0:
            self.table.selectRow(0)

    def set_bookmarks(self, bookmarks: list[TimeBookmark]):
        """Update the bookmark list and refresh the table."""
        self._bookmarks = bookmarks
        self._populate_table()

    def eventFilter(self, obj, event):
        """Handle keyboard events in the table."""
        if obj == self.table and event.type() == event.Type.KeyPress:
            if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
                self._on_jump_clicked()
                return True
            elif event.key() == Qt.Key_Delete:
                if self._delete_callback:
                    self._on_delete_clicked()
                return True
        return super().eventFilter(obj, event)

    def _get_selected_row(self) -> int:
        """Get the currently selected row index."""
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            return -1
        return selected_rows[0].row()

    def _on_table_double_click(self, item: QTableWidgetItem):
        """Handle double-click on table item."""
        self._on_jump_clicked()

    def _on_jump_clicked(self):
        """Handle jump button click."""
        row = self._get_selected_row()
        if row < 0:
            QMessageBox.warning(self, "No Selection", "Please select a bookmark to jump to.")
            return
        
        self.bookmark_selected.emit(row)
        
        if self._auto_close:
            self.accept()

    def _on_add_clicked(self):
        """Handle add button click."""
        if not self._add_callback:
            return
        
        # Prompt for label
        label, ok = QInputDialog.getText(
            self,
            "Add Bookmark",
            "Bookmark Label:",
            text="New Bookmark"
        )
        
        if not ok or not label.strip():
            return
        
        # Optional description
        description, ok = QInputDialog.getText(
            self,
            "Add Bookmark",
            "Description (optional):",
            text=""
        )
        
        if not ok:
            description = ""
        
        # Call the add callback
        self._add_callback(label.strip(), description.strip())

    def _on_delete_clicked(self):
        """Handle delete button click."""
        if not self._delete_callback:
            return
        
        row = self._get_selected_row()
        if row < 0:
            QMessageBox.warning(self, "No Selection", "Please select a bookmark to delete.")
            return
        
        # Confirm deletion
        bookmark = self._bookmarks[row]
        reply = QMessageBox.question(
            self,
            "Delete Bookmark",
            f"Delete bookmark '{bookmark.label}'?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self._delete_callback(row)

