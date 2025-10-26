"""Standalone window for the parsed log table with signal filters."""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QMessageBox,
    QPushButton,
    QLabel,
    QFileDialog,
    QFrame,
)

from plc_visualizer.models import ParsedLog
from plc_visualizer.utils import SignalData
from plc_visualizer.validation import SignalValidator, ValidationViolation
from ..components.signal_filter_widget import SignalFilterWidget
from ..components.data_table_widget import DataTableWidget
from ..theme import (
    MUTED_TEXT,
    PRIMARY_NAVY,
    apply_primary_button_style,
    apply_secondary_button_style,
    card_panel_styles,
    create_header_bar,
    surface_stylesheet,
)


class LogTableWindow(QMainWindow):
    """Window that displays the parsed log table with filtering controls."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Log Table")
        self._parsed_log: Optional[ParsedLog] = None
        self._signal_data_map: dict[str, SignalData] = {}
        self._signal_data_list: list[SignalData] = []
        self._interval_request_handler: Optional[Callable[[str], None]] = None
        self._validator: Optional[SignalValidator] = None
        self._violations: dict[str, list[ValidationViolation]] = {}
        self._loaded_rules_path: Optional[Path] = None
        self._init_ui()

    def set_interval_request_handler(self, handler: Callable[[str], None]):
        """Register a callback for interval plotting requests."""
        self._interval_request_handler = handler

    def clear(self):
        """Reset the window to an empty state."""
        self._parsed_log = None
        self._signal_data_map.clear()
        self._signal_data_list.clear()
        self._violations.clear()
        self.signal_filter.clear()
        self.data_table.clear()

    def set_data(self, parsed_log: Optional[ParsedLog], signal_data: list[SignalData]):
        """Populate the table and filters with new data."""
        if parsed_log is None:
            self.clear()
            return

        self._parsed_log = parsed_log
        self._signal_data_map = {item.key: item for item in signal_data}
        self._signal_data_list = signal_data

        self.signal_filter.set_signals(signal_data)
        self.data_table.set_data(parsed_log)

    def load_validation_rules(self, rules_path: str | Path = None) -> bool:
        """Load validation rules from a YAML file.

        Args:
            rules_path: Path to the YAML rules file. If None, shows file dialog.

        Returns:
            True if rules loaded successfully, False otherwise.
        """
        # Show file dialog if no path provided
        if rules_path is None:
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "Load Validation Rules",
                str(Path.cwd()),
                "YAML Files (*.yaml *.yml);;All Files (*)"
            )
            if not file_path:
                return False  # User cancelled
            rules_path = file_path

        try:
            self._validator = SignalValidator(rules_path)
            self._loaded_rules_path = Path(rules_path)

            # Update UI
            self._update_validation_ui()

            QMessageBox.information(
                self,
                "Rules Loaded",
                f"Validation rules loaded successfully from:\n{self._loaded_rules_path.name}\n\n"
                f"Click 'Run Validation' to check the log data."
            )
            return True
        except FileNotFoundError:
            QMessageBox.critical(
                self,
                "File Not Found",
                f"Rules file not found:\n{rules_path}"
            )
            return False
        except Exception as e:
            QMessageBox.critical(
                self,
                "Load Error",
                f"Failed to load validation rules:\n{str(e)}"
            )
            return False

    def run_validation(self) -> dict[str, list[ValidationViolation]]:
        """Run validation on current log data.

        Returns:
            Dictionary mapping device_id to list of violations.
        """
        if self._validator is None:
            QMessageBox.warning(
                self,
                "No Rules Loaded",
                "Please load validation rules first."
            )
            return {}

        if self._parsed_log is None or not self._signal_data_list:
            QMessageBox.warning(
                self,
                "No Data",
                "Please load log data first."
            )
            return {}

        try:
            # Run validation
            self._violations = self._validator.validate_all(
                self._parsed_log,
                self._signal_data_list
            )

            # Show summary
            total_violations = sum(len(v) for v in self._violations.values())
            devices_with_violations = len(self._violations)

            if total_violations == 0:
                QMessageBox.information(
                    self,
                    "Validation Complete",
                    "No violations found! All signals follow expected patterns."
                )
            else:
                # Count by severity
                error_count = sum(
                    1 for vlist in self._violations.values()
                    for v in vlist if v.severity == "error"
                )
                warning_count = sum(
                    1 for vlist in self._violations.values()
                    for v in vlist if v.severity == "warning"
                )
                info_count = sum(
                    1 for vlist in self._violations.values()
                    for v in vlist if v.severity == "info"
                )

                QMessageBox.warning(
                    self,
                    "Validation Complete",
                    f"Found {total_violations} violations in {devices_with_violations} devices:\n\n"
                    f"  Errors: {error_count}\n"
                    f"  Warnings: {warning_count}\n"
                    f"  Info: {info_count}\n\n"
                    f"Check console output for details."
                )

                # Print detailed violations to console
                self._print_violations()

            return self._violations

        except Exception as e:
            QMessageBox.critical(
                self,
                "Validation Error",
                f"Error during validation:\n{str(e)}"
            )
            import traceback
            traceback.print_exc()
            return {}

    def _print_violations(self):
        """Print violations to console for debugging."""
        print("\n" + "=" * 80)
        print("VALIDATION VIOLATIONS")
        print("=" * 80)

        for device_id in sorted(self._violations.keys()):
            violations = self._violations[device_id]
            print(f"\nDevice: {device_id}")
            print("-" * 80)

            for violation in violations:
                print(f"  {violation}")

        print("\n" + "=" * 80 + "\n")

    # Internal helpers ---------------------------------------------------
    def _init_ui(self):
        central = QWidget()
        central.setObjectName("LogTableSurface")
        central.setStyleSheet(surface_stylesheet("LogTableSurface"))
        self.setCentralWidget(central)

        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        header = create_header_bar(
            "Log Table",
            "Browse parsed rows, filter signals, and run validation rules.",
        )
        root_layout.addWidget(header)

        content = QWidget()
        content.setObjectName("LogTableContent")
        content.setStyleSheet(surface_stylesheet("LogTableContent"))
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(16, 16, 16, 16)
        content_layout.setSpacing(12)
        root_layout.addWidget(content, stretch=1)

        # Validation toolbar
        validation_panel = self._create_validation_toolbar()
        content_layout.addWidget(validation_panel)

        self.signal_filter = SignalFilterWidget()
        self.signal_filter.visible_signals_changed.connect(self._on_visible_signals_changed)
        self.signal_filter.plot_intervals_requested.connect(self._handle_plot_intervals)

        filter_card = QWidget()
        filter_card.setObjectName("LogFilterCard")
        filter_card.setStyleSheet(card_panel_styles("LogFilterCard"))
        filter_layout = QVBoxLayout(filter_card)
        filter_layout.setContentsMargins(12, 12, 12, 12)
        filter_layout.setSpacing(8)
        filter_layout.addWidget(self.signal_filter)
        content_layout.addWidget(filter_card)

        self.data_table = DataTableWidget()
        table_card = QWidget()
        table_card.setObjectName("LogTableCard")
        table_card.setStyleSheet(card_panel_styles("LogTableCard"))
        table_layout = QVBoxLayout(table_card)
        table_layout.setContentsMargins(12, 12, 12, 12)
        table_layout.setSpacing(0)
        table_layout.addWidget(self.data_table)
        content_layout.addWidget(table_card, stretch=1)

    def _create_validation_toolbar(self) -> QFrame:
        """Create the validation control toolbar."""
        frame = QFrame()
        frame.setObjectName("ValidationPanel")
        frame.setStyleSheet(card_panel_styles("ValidationPanel"))

        layout = QHBoxLayout(frame)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)

        # Section label
        title_label = QLabel("<b>Signal Validation:</b>")
        title_label.setStyleSheet("font-size: 13px; color: #003D82;")
        layout.addWidget(title_label)

        # Load Rules button
        self.load_rules_btn = QPushButton("Load Rules...")
        self.load_rules_btn.setToolTip("Load validation rules from a YAML file")
        self.load_rules_btn.clicked.connect(self._on_load_rules_clicked)
        apply_secondary_button_style(self.load_rules_btn)
        layout.addWidget(self.load_rules_btn)

        # Status label
        self.rules_status_label = QLabel("No rules loaded")
        self.rules_status_label.setStyleSheet(f"color: {MUTED_TEXT}; font-style: italic;")
        layout.addWidget(self.rules_status_label)

        layout.addStretch()

        # Run Validation button
        self.run_validation_btn = QPushButton("Run Validation")
        self.run_validation_btn.setToolTip("Validate log data against loaded rules")
        self.run_validation_btn.setEnabled(False)  # Disabled until rules are loaded
        self.run_validation_btn.clicked.connect(self._on_run_validation_clicked)
        apply_primary_button_style(self.run_validation_btn)
        layout.addWidget(self.run_validation_btn)

        return frame

    def _on_load_rules_clicked(self):
        """Handle Load Rules button click."""
        self.load_validation_rules()

    def _on_run_validation_clicked(self):
        """Handle Run Validation button click."""
        self.run_validation()

    def _update_validation_ui(self):
        """Update validation UI state based on loaded rules."""
        if self._validator is not None and self._loaded_rules_path is not None:
            self.rules_status_label.setText(f"Loaded: {self._loaded_rules_path.name}")
            self.rules_status_label.setStyleSheet(f"color: {PRIMARY_NAVY}; font-weight: bold;")
            self.run_validation_btn.setEnabled(True)
        else:
            self.rules_status_label.setText("No rules loaded")
            self.rules_status_label.setStyleSheet(f"color: {MUTED_TEXT}; font-style: italic;")
            self.run_validation_btn.setEnabled(False)

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
