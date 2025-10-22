"""Standalone window for the parsed log table with signal filters."""

from __future__ import annotations

from typing import Callable, Optional

from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QMessageBox,
)

from plc_visualizer.models import ParsedLog
from plc_visualizer.utils import SignalData
from .signal_filter_widget import SignalFilterWidget
from .data_table_widget import DataTableWidget


class LogTableWindow(QMainWindow):
    """Window that displays the parsed log table with filtering controls."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Log Table")
        self._parsed_log: Optional[ParsedLog] = None
        self._signal_data_map: dict[str, SignalData] = {}
        self._interval_request_handler: Optional[Callable[[str], None]] = None
        self._init_ui()

    def set_interval_request_handler(self, handler: Callable[[str], None]):
        """Register a callback for interval plotting requests."""
        self._interval_request_handler = handler

    def clear(self):
        """Reset the window to an empty state."""
        self._parsed_log = None
        self._signal_data_map.clear()
        self.signal_filter.clear()
        self.data_table.clear()

    def set_data(self, parsed_log: Optional[ParsedLog], signal_data: list[SignalData]):
        """Populate the table and filters with new data."""
        if parsed_log is None:
            self.clear()
            return

        self._parsed_log = parsed_log
        self._signal_data_map = {item.key: item for item in signal_data}

        self.signal_filter.set_signals(signal_data)
        self.data_table.set_data(parsed_log)

    # Internal helpers ---------------------------------------------------
    def _init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        self.signal_filter = SignalFilterWidget()
        self.signal_filter.visible_signals_changed.connect(self._on_visible_signals_changed)
        self.signal_filter.plot_intervals_requested.connect(self._handle_plot_intervals)
        layout.addWidget(self.signal_filter)

        self.data_table = DataTableWidget()
        layout.addWidget(self.data_table, stretch=1)

    def _on_visible_signals_changed(self, visible_names: list[str]):
        if self._parsed_log is None:
            return
        self.data_table.filter_signals(set(visible_names))

    def _handle_plot_intervals(self, signal_key: str):
        if not signal_key:
            return

        signal_data = self._signal_data_map.get(signal_key)
        if signal_data is None:
            QMessageBox.information(
                self,
                "Signal Not Available",
                "The selected signal is no longer available. Please reload the data.",
            )
            return

        if not signal_data.states or len(signal_data.states) < 2:
            QMessageBox.information(
                self,
                "No Transitions",
                "This signal does not have enough transitions to plot change intervals.",
            )
            return

        if self._interval_request_handler:
            self._interval_request_handler(signal_key)
