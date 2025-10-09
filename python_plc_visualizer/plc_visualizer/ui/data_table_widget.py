"""Widget for displaying parsed log data in a table."""

from PyQt6.QtCore import Qt, QAbstractTableModel, QModelIndex
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QTableView,
    QHeaderView,
    QLabel,
)

from plc_visualizer.models import ParsedLog, LogEntry


class LogDataModel(QAbstractTableModel):
    """Table model for displaying log entries."""

    COLUMNS = ["Device ID", "Signal Name", "Timestamp", "Value", "Type"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._entries: list[LogEntry] = []

    def set_entries(self, entries: list[LogEntry]):
        """Set the entries displayed by the model."""
        self.beginResetModel()
        self._entries = list(entries)
        self.endResetModel()

    def clear(self):
        """Clear all data."""
        self.beginResetModel()
        self._entries = []
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()) -> int:
        """Return number of rows."""
        if parent.isValid():
            return 0
        return len(self._entries)

    def columnCount(self, parent=QModelIndex()) -> int:
        """Return number of columns."""
        if parent.isValid():
            return 0
        return len(self.COLUMNS)

    def data(self, index: QModelIndex, role=Qt.ItemDataRole.DisplayRole):
        """Return data for the given index and role."""
        if not index.isValid():
            return None

        if role == Qt.ItemDataRole.DisplayRole:
            entry = self._entries[index.row()]
            column = index.column()

            if column == 0:  # Device ID
                return entry.device_id
            elif column == 1:  # Signal Name
                return entry.signal_name
            elif column == 2:  # Timestamp
                return entry.timestamp.strftime('%H:%M:%S')
            elif column == 3:  # Value
                return str(entry.value)
            elif column == 4:  # Type
                return entry.signal_type.value

        elif role == Qt.ItemDataRole.TextAlignmentRole:
            # Center align timestamp and type columns
            if index.column() in [2, 4]:
                return Qt.AlignmentFlag.AlignCenter

        return None

    def headerData(self, section: int, orientation: Qt.Orientation,
                   role=Qt.ItemDataRole.DisplayRole):
        """Return header data."""
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal:
                return self.COLUMNS[section]
            else:
                return str(section + 1)
        return None


class DataTableWidget(QWidget):
    """Widget for displaying parsed log data in a table view."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._parsed_log: ParsedLog | None = None
        self._init_ui()

    def _init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)

        # Title
        title = QLabel("Parsed Log Data")
        title.setStyleSheet("font-size: 16px; font-weight: bold; padding: 5px;")
        layout.addWidget(title)

        # Table view
        self.table_view = QTableView()
        self.model = LogDataModel(self)
        self.table_view.setModel(self.model)

        # Configure table view
        self.table_view.setAlternatingRowColors(True)
        self.table_view.setSelectionBehavior(
            QTableView.SelectionBehavior.SelectRows
        )
        self.table_view.setSortingEnabled(False)

        # Configure header
        header = self.table_view.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)

        # Style
        self.table_view.setStyleSheet("""
            QTableView {
                border: 1px solid #ddd;
                gridline-color: #e0e0e0;
                font-size: 12px;
            }
            QTableView::item {
                padding: 5px;
            }
            QTableView::item:selected {
                background-color: #2196F3;
                color: white;
            }
            QHeaderView::section {
                background-color: #f5f5f5;
                padding: 8px;
                border: 1px solid #ddd;
                font-weight: bold;
            }
        """)

        layout.addWidget(self.table_view)

        # Row count label
        self.row_count_label = QLabel("0 entries")
        self.row_count_label.setStyleSheet("padding: 5px; font-size: 11px; color: #666;")
        layout.addWidget(self.row_count_label)

    def set_data(self, parsed_log: ParsedLog):
        """Set the log data to display.

        Args:
            parsed_log: ParsedLog containing entries to display
        """
        self._parsed_log = parsed_log
        self.model.set_entries(parsed_log.entries)
        self.row_count_label.setText(f"{parsed_log.entry_count:,} entries")

    def clear(self):
        """Clear the table."""
        self.model.clear()
        self.row_count_label.setText("0 entries")
        self._parsed_log = None

    def filter_signals(self, signal_names: set[str]):
        """Filter the table by the given signal names."""
        if self._parsed_log is None:
            self.model.clear()
            self.row_count_label.setText("0 entries")
            return

        def entry_key(entry: LogEntry) -> str:
            return f"{entry.device_id}::{entry.signal_name}"

        if not signal_names:
            filtered_entries: list[LogEntry] = []
        elif len(signal_names) == len(self._parsed_log.signals):
            filtered_entries = self._parsed_log.entries
        else:
            filtered_entries = [
                entry
                for entry in self._parsed_log.entries
                if entry_key(entry) in signal_names
            ]

        self.model.set_entries(filtered_entries)

        total = self._parsed_log.entry_count
        filtered_count = len(filtered_entries)

        if total == 0 or filtered_count == total:
            self.row_count_label.setText(f"{filtered_count:,} entries")
        elif not signal_names:
            self.row_count_label.setText(f"0 of {total:,} entries")
        else:
            self.row_count_label.setText(f"{filtered_count:,} of {total:,} entries")
