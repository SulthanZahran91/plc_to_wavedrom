"""File list widget showing loaded files with individual progress bars."""

from pathlib import Path
from typing import Dict

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QProgressBar,
    QScrollArea,
    QFrame,
)


class FileListItem(QFrame):
    """A single file item with name, progress bar, and delete button."""

    file_removed = Signal(str)  # Emits file path when removed

    def __init__(self, file_path: str, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self._init_ui()

    def _init_ui(self):
        """Initialize the user interface."""
        self.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        self.setLineWidth(1)
        self.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #e0e0e0;
                border-radius: 4px;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(12)

        # File icon and name
        file_name = Path(self.file_path).name
        file_label = QLabel(f" {file_name}")
        file_label.setStyleSheet("font-size: 12px;")
        file_label.setMinimumWidth(200)
        layout.addWidget(file_label)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setMinimumWidth(150)
        self.progress_bar.setMaximumWidth(200)
        self.progress_bar.setMaximumHeight(20)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #BDBDBD;
                border-radius: 3px;
                text-align: center;
                background-color: #f5f5f5;
                font-size: 10px;
            }
            QProgressBar::chunk {
                background-color: #4285F4;
            }
        """)
        layout.addWidget(self.progress_bar)

        # Trash button
        trash_button = QPushButton("")
        trash_button.setMaximumWidth(40)
        trash_button.setMaximumHeight(28)
        trash_button.setStyleSheet("""
            QPushButton {
                background-color: #ffebee;
                border: 1px solid #ffcdd2;
                border-radius: 4px;
                color: #d32f2f;
                font-size: 12px;
                padding: 2px;
            }
            QPushButton:hover {
                background-color: #ffcdd2;
            }
            QPushButton:pressed {
                background-color: #ef5350;
                color: white;
            }
        """)
        trash_button.clicked.connect(self._on_trash_clicked)
        layout.addWidget(trash_button)

        # Set fixed height
        self.setMaximumHeight(50)

    def _on_trash_clicked(self):
        """Emit signal when trash button is clicked."""
        self.file_removed.emit(self.file_path)

    def update_progress(self, value: int):
        """Update the progress bar value."""
        self.progress_bar.setValue(min(100, max(0, value)))

    def hide_progress(self):
        """Hide the progress bar."""
        self.progress_bar.setVisible(False)


class FileListWidget(QWidget):
    """Widget displaying a list of loaded files with individual progress."""

    file_removed = Signal(str)  # Emits file path when a file is removed

    def __init__(self, parent=None):
        super().__init__(parent)
        self._file_items: Dict[str, FileListItem] = {}
        self._init_ui()

    def _init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Header with file count
        self.header_label = QLabel("Loaded 0 files")
        self.header_label.setStyleSheet("font-weight: bold; font-size: 13px; color: #1976D2;")
        layout.addWidget(self.header_label)

        # Scrollable file list
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                background-color: #fafafa;
            }
        """)

        self.files_container = QWidget()
        self.files_layout = QVBoxLayout(self.files_container)
        self.files_layout.setContentsMargins(8, 8, 8, 8)
        self.files_layout.setSpacing(8)
        self.files_layout.addStretch()

        scroll_area.setWidget(self.files_container)
        layout.addWidget(scroll_area, 1)

        self.setStyleSheet("""
            QWidget {
                background-color: white;
            }
        """)

    def add_file(self, file_path: str):
        """Add a file to the list."""
        if file_path in self._file_items:
            return

        # Insert before stretch
        item = FileListItem(file_path)
        item.file_removed.connect(self._on_file_removed)
        self._file_items[file_path] = item

        # Insert before the stretch
        insert_position = self.files_layout.count() - 1
        self.files_layout.insertWidget(insert_position, item)

        self._update_header()

    def remove_file(self, file_path: str):
        """Remove a file from the list."""
        if file_path not in self._file_items:
            return

        item = self._file_items.pop(file_path)
        item.setParent(None)
        self._update_header()
        self.file_removed.emit(file_path)

    def _on_file_removed(self, file_path: str):
        """Handle file removal signal from item."""
        self.remove_file(file_path)

    def update_progress(self, file_path: str, value: int):
        """Update progress for a specific file."""
        if file_path in self._file_items:
            self._file_items[file_path].update_progress(value)

    def hide_all_progress(self):
        """Hide progress bars for all files."""
        for item in self._file_items.values():
            item.hide_progress()

    def clear_all(self):
        """Clear all files from the list."""
        for file_path in list(self._file_items.keys()):
            self.remove_file(file_path)

    def _update_header(self):
        """Update the header with current file count."""
        count = len(self._file_items)
        if count == 0:
            self.header_label.setText("No files loaded")
        elif count == 1:
            self.header_label.setText("Loaded 1 file")
        else:
            self.header_label.setText(f"Loaded {count} files")
