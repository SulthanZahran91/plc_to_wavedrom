"""File upload widget with drag-and-drop support."""

from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QPalette
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QFileDialog,
    QFrame,
)


class FileUploadWidget(QWidget):
    """Widget for uploading log files via button or drag-and-drop."""

    files_selected = pyqtSignal(list)  # Emits list of file paths when selected

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)

        # Drop zone frame
        self.drop_zone = QFrame()
        self.drop_zone.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Plain)
        self.drop_zone.setLineWidth(2)
        self.drop_zone.setAcceptDrops(True)
        self.drop_zone.setMinimumHeight(150)

        # Enable drag and drop
        self.setAcceptDrops(True)

        # Drop zone layout
        drop_layout = QVBoxLayout(self.drop_zone)
        drop_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Icon/Label
        self.label = QLabel("📁 Drag and drop log files here\nor click to browse")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setStyleSheet("font-size: 14px; padding: 20px;")
        drop_layout.addWidget(self.label)

        # Browse button
        self.browse_button = QPushButton("Browse for Files")
        self.browse_button.clicked.connect(self._browse_file)
        self.browse_button.setMinimumHeight(40)
        drop_layout.addWidget(self.browse_button)

        layout.addWidget(self.drop_zone)

        # Style the drop zone
        self._apply_normal_style()

    def _apply_normal_style(self):
        """Apply normal style to drop zone."""
        self.drop_zone.setStyleSheet("""
            QFrame {
                border: 2px dashed #aaa;
                border-radius: 5px;
                background-color: #f9f9f9;
            }
        """)

    def _apply_hover_style(self):
        """Apply hover style to drop zone."""
        self.drop_zone.setStyleSheet("""
            QFrame {
                border: 2px dashed #4CAF50;
                border-radius: 5px;
                background-color: #e8f5e9;
            }
        """)

    def dragEnterEvent(self, event: QDragEnterEvent):
        """Handle drag enter event."""
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if any(Path(url.toLocalFile()).is_file() for url in urls):
                event.acceptProposedAction()
                self._apply_hover_style()
                return
        event.ignore()

    def dragLeaveEvent(self, event):
        """Handle drag leave event."""
        self._apply_normal_style()
        event.accept()

    def dropEvent(self, event: QDropEvent):
        """Handle drop event."""
        self._apply_normal_style()

        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            file_paths = [
                url.toLocalFile()
                for url in urls
                if Path(url.toLocalFile()).is_file()
            ]
            if file_paths:
                self.files_selected.emit(file_paths)
                event.acceptProposedAction()
                return
        event.ignore()

    def _browse_file(self):
        """Open file browser dialog."""
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Log Files",
            "",
            "Log Files (*.log);;All Files (*)"
        )

        if file_paths:
            self.files_selected.emit(file_paths)

    def set_status(self, text: str):
        """Update the status text in the drop zone."""
        self.label.setText(text)
