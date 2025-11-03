"""Widget for displaying parsing statistics."""

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QTextEdit,
)

from plc_visualizer.models import ParseResult


class StatsWidget(QWidget):
    """Widget to display parsing statistics and errors."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)

        # Stats container
        stats_frame = QFrame()
        stats_frame.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Raised)
        stats_layout = QVBoxLayout(stats_frame)

        # Title
        title = QLabel("Parsing Statistics")
        title.setStyleSheet("font-size: 16px; font-weight: bold; padding: 5px;")
        stats_layout.addWidget(title)

        # Stats labels
        self.entries_label = QLabel("Entries: -")
        self.devices_label = QLabel("Unique Devices: -")
        self.signals_label = QLabel("Unique Signals: -")
        self.time_range_label = QLabel("Time Range: -")
        self.processing_time_label = QLabel("Processing Time: -")
        self.errors_label = QLabel("Errors: -")

        for label in [self.entries_label, self.devices_label, self.signals_label,
                      self.time_range_label, self.processing_time_label, self.errors_label]:
            label.setStyleSheet("padding: 5px; font-size: 13px;")
            stats_layout.addWidget(label)

        layout.addWidget(stats_frame)

        # Error details (collapsible)
        self.error_details = QTextEdit()
        self.error_details.setReadOnly(True)
        self.error_details.setMaximumHeight(150)
        self.error_details.setVisible(False)
        self.error_details.setStyleSheet("""
            QTextEdit {
                background-color: #fff3cd;
                border: 1px solid #ffc107;
                border-radius: 3px;
                padding: 5px;
                font-family: monospace;
                font-size: 11px;
            }
        """)
        layout.addWidget(self.error_details)

        layout.addStretch()

    def update_stats(self, result: ParseResult):
        """Update statistics from parse result.

        Args:
            result: ParseResult containing parsed data and errors
        """
        if result.data:
            # Update entry count
            self.entries_label.setText(
                f"Entries: {result.data.entry_count:,}"
            )

            # Update signal count
            self.signals_label.setText(
                f"Unique Signals: {result.data.signal_count}"
            )
            # Update device count
            self.devices_label.setText(
                f"Unique Devices: {result.data.device_count}"
            )

            # Update time range
            if result.data.time_range:
                start, end = result.data.time_range
                time_range_str = (
                    f"{start.strftime('%H:%M:%S')} to "
                    f"{end.strftime('%H:%M:%S')}"
                )
                self.time_range_label.setText(f"Time Range: {time_range_str}")
            else:
                self.time_range_label.setText("Time Range: -")
        else:
            self.entries_label.setText("Entries: 0")
            self.devices_label.setText("Unique Devices: 0")
            self.signals_label.setText("Unique Signals: 0")
            self.time_range_label.setText("Time Range: -")
        
        # Update processing time
        if result.processing_time is not None:
            if result.processing_time < 1.0:
                time_str = f"{result.processing_time * 1000:.0f}ms"
            else:
                time_str = f"{result.processing_time:.2f}s"
            self.processing_time_label.setText(f"Processing Time: {time_str}")
        else:
            self.processing_time_label.setText("Processing Time: -")

        # Update error information
        if result.has_errors:
            error_count = result.error_count
            self.errors_label.setText(
                f"⚠️ Errors: {error_count} line(s) could not be parsed"
            )
            self.errors_label.setStyleSheet(
                "padding: 5px; font-size: 13px; color: #d32f2f; font-weight: bold;"
            )

            # Show error details
            error_text = f"Parsing Errors ({error_count}):\n" + "="*50 + "\n\n"
            for error in result.errors:
                file_label = ""
                if error.file_path:
                    file_label = f"[{Path(error.file_path).name}] "
                error_text += f"{file_label}Line {error.line}: {error.reason}\n"
                error_text += f"  Content: {error.content[:80]}\n\n"

            self.error_details.setText(error_text)
            self.error_details.setVisible(True)
        else:
            self.errors_label.setText("✓ Errors: 0")
            self.errors_label.setStyleSheet(
                "padding: 5px; font-size: 13px; color: #2e7d32; font-weight: bold;"
            )
            self.error_details.setVisible(False)

    def clear(self):
        """Clear all statistics."""
        self.entries_label.setText("Entries: -")
        self.devices_label.setText("Unique Devices: -")
        self.signals_label.setText("Unique Signals: -")
        self.time_range_label.setText("Time Range: -")
        self.errors_label.setText("Errors: -")
        self.errors_label.setStyleSheet("padding: 5px; font-size: 13px;")
        self.error_details.setVisible(False)
