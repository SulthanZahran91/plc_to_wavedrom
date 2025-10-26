"""Main application window for PLC Log Visualizer."""

import atexit
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Dict, List, Optional
import multiprocessing as mp
from multiprocessing.context import BaseContext

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QResizeEvent
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QVBoxLayout,
    QWidget,
    QGridLayout,
    QHBoxLayout,
    QLabel,
)

from plc_visualizer.models import ParseResult, ParsedLog
from plc_visualizer.parsers import parser_registry
from plc_visualizer.utils import (
    SignalData,
    merge_parse_results,
    process_signals_for_waveform,
    compute_signal_states,
)
from .file_upload_widget import FileUploadWidget
from .file_list_widget import FileListWidget
from .stats_widget import StatsWidget
from .timing_diagram_window import TimingDiagramWindow
from .log_table_window import LogTableWindow
from .signal_interval_dialog import SignalIntervalDialog
from .signal_selection_dialog import SignalSelectionDialog


class ParserThread(QThread):
    """Background thread for parsing one or more log files."""

    finished = Signal(object, object, object)  # aggregated_result, per_file_results, signal_data_list
    progress = Signal(int, int, str)  # current_index, total_files, file_path
    error = Signal(str)
    _executor: ProcessPoolExecutor | None = None
    _mp_context: BaseContext | None = None

    def __init__(self, file_paths: List[str], parent=None):
        super().__init__(parent)
        self.file_paths = file_paths

    def run(self):
        """Parse files in a background thread."""
        try:
            per_file_results: Dict[str, ParseResult] = {}
            total_files = len(self.file_paths)

            for index, file_path in enumerate(self.file_paths, start=1):
                per_file_results[file_path] = parser_registry.parse(file_path)
                self.progress.emit(index, total_files, file_path)

            aggregated_result = merge_parse_results(per_file_results)
            signal_data_list = []
            if aggregated_result.success and aggregated_result.data:
                signal_data_list = self._compute_signal_data(aggregated_result.data)

            self.finished.emit(aggregated_result, per_file_results, signal_data_list)
        except Exception as e:
            self.error.emit(f"Failed to parse files: {str(e)}")

    @classmethod
    def _compute_signal_data(cls, parsed_log: ParsedLog):
        """Compute waveform data, using a subprocess for heavy workloads."""
        try:
            entry_count = getattr(parsed_log, "entry_count", 0)
            if entry_count and entry_count >= 10000:
                if cls._executor is None:
                    if cls._mp_context is None:
                        try:
                            cls._mp_context = mp.get_context("spawn")
                        except ValueError:
                            cls._mp_context = mp.get_context()
                    try:
                        cls._executor = ProcessPoolExecutor(
                            max_workers=1,
                            mp_context=cls._mp_context,
                        )
                    except TypeError:
                        cls._executor = ProcessPoolExecutor(max_workers=1)
                future = cls._executor.submit(process_signals_for_waveform, parsed_log)
                return future.result()
            return process_signals_for_waveform(parsed_log)
        except Exception:
            # Fallback to in-process computation if multiprocessing fails
            return process_signals_for_waveform(parsed_log)

    @classmethod
    def shutdown_executor(cls):
        """Dispose of the shared process pool."""
        if cls._executor is not None:
            cls._executor.shutdown(wait=False)
            cls._executor = None


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self):
        super().__init__()
        platform_name = ""
        app = QApplication.instance()
        if app:
            try:
                platform_name = app.platformName().lower()
            except Exception:
                platform_name = ""
        self._is_wayland = "wayland" in platform_name
        print(f"[MainWindow] Initialized on platform '{platform_name}', is_wayland={self._is_wayland}")

        self._current_files: list[str] = []
        self._merged_parsed_log: Optional[ParsedLog] = None
        self._file_results: Dict[str, ParseResult] = {}
        self._signal_data_list: list[SignalData] = []
        self._signal_data_map: dict[str, SignalData] = {}
        self._parser_thread: Optional[ParserThread] = None

        self._timing_window: Optional[TimingDiagramWindow] = None
        self._table_window: Optional[LogTableWindow] = None
        self._map_viewer_window = None
        self._interval_windows: dict[str, SignalIntervalDialog] = {}
        self._interval_selection_window: Optional[SignalSelectionDialog] = None

        self.stats_widget: Optional[StatsWidget] = None
        self.file_list_widget: Optional[FileListWidget] = None

        self._init_ui()

    def _init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("PLC Log Visualizer")
        self.setMinimumSize(1400, 900)

        self._create_menu_bar()

        # Create header widget
        header_widget = QWidget()
        header_widget.setStyleSheet("""
            QWidget {
                background-color: #003D82;
                padding: 10px 18px;
            }
        """)
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(18, 10, 18, 10)
        header_layout.setSpacing(0)

        # Header title
        header_label = QLabel("PLC Log Visualizer")
        header_label.setStyleSheet("color: white; font-size: 16px; font-weight: bold;")
        header_layout.addWidget(header_label)
        header_layout.addStretch()

        # Clear File button in header
        clear_button = QPushButton("Clear File")
        clear_button.setMaximumWidth(120)
        clear_button.setStyleSheet("""
            QPushButton {
                background-color: #4285F4;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1967D2;
            }
            QPushButton:pressed {
                background-color: #0D47A1;
            }
        """)
        clear_button.clicked.connect(self._on_clear_file)
        header_layout.addWidget(clear_button)

        # Main layout structure
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Add header
        main_layout.addWidget(header_widget)

        # Content area
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(16, 16, 16, 16)
        content_layout.setSpacing(16)

        # 2-column top section: Upload/Stats (left) and File List (right)
        top_section = QWidget()
        top_layout = QHBoxLayout(top_section)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(16)

        # LEFT COLUMN: Upload widget and stats
        left_column = QWidget()
        left_layout = QVBoxLayout(left_column)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(12)

        # Upload section label
        upload_label = QLabel("📄 Log File")
        upload_label.setStyleSheet("font-weight: bold; font-size: 13px;")
        left_layout.addWidget(upload_label)

        # Upload widget
        self.upload_widget = FileUploadWidget()
        self.upload_widget.files_selected.connect(self._on_files_selected)
        left_layout.addWidget(self.upload_widget)

        # Stats widget
        stats_container = QWidget()
        stats_layout = QVBoxLayout(stats_container)
        stats_layout.setContentsMargins(0, 0, 0, 0)
        stats_layout.setSpacing(0)

        self.stats_widget = StatsWidget(stats_container)
        stats_layout.addWidget(self.stats_widget)

        left_layout.addWidget(stats_container)
        top_layout.addWidget(left_column, 40)  # 40% width

        # RIGHT COLUMN: File list
        self.file_list_widget = FileListWidget()
        self.file_list_widget.file_removed.connect(self._on_file_removed_from_list)
        top_layout.addWidget(self.file_list_widget, 60)  # 60% width

        content_layout.addWidget(top_section, 1)

        # Progress bar (hidden during normal operation, shown during parsing)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setVisible(False)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("Parsing files... %p%")
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #BDBDBD;
                border-radius: 4px;
                text-align: center;
                background-color: #f5f5f5;
                height: 24px;
            }
            QProgressBar::chunk {
                background-color: #4285F4;
            }
        """)
        content_layout.addWidget(self.progress_bar)

        # Buttons section
        buttons_container = QWidget()
        buttons_layout = QGridLayout(buttons_container)
        buttons_layout.setContentsMargins(0, 16, 0, 0)
        buttons_layout.setHorizontalSpacing(16)
        buttons_layout.setVerticalSpacing(16)

        # Timing Diagram button (gray)
        self.timing_button = QPushButton("⚙ Timing Diagram")
        self.timing_button.clicked.connect(self._open_timing_diagram_window)
        self.timing_button.setMinimumHeight(120)
        self.timing_button.setMinimumWidth(250)
        self.timing_button.setStyleSheet("""
            QPushButton {
                background-color: #9E9E9E;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 14px;
                font-weight: bold;
                padding: 15px;
            }
            QPushButton:hover {
                background-color: #757575;
            }
            QPushButton:pressed {
                background-color: #616161;
            }
            QPushButton:disabled {
                background-color: #BDBDBD;
                color: #f5f5f5;
            }
        """)
        buttons_layout.addWidget(self.timing_button, 0, 0)

        # Map Viewer button (blue - primary)
        self.map_button = QPushButton("📖 Map Viewer")
        self.map_button.clicked.connect(self._open_map_viewer)
        self.map_button.setMinimumHeight(120)
        self.map_button.setMinimumWidth(250)
        self.map_button.setStyleSheet("""
            QPushButton {
                background-color: #4285F4;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 14px;
                font-weight: bold;
                padding: 15px;
            }
            QPushButton:hover {
                background-color: #1967D2;
            }
            QPushButton:pressed {
                background-color: #0D47A1;
            }
            QPushButton:disabled {
                background-color: #BDBDBD;
                color: #f5f5f5;
            }
        """)
        buttons_layout.addWidget(self.map_button, 0, 1)

        # Transition Intervals button (gray)
        self.interval_button = QPushButton("📈 Transition Intervals")
        self.interval_button.clicked.connect(self._open_signal_interval_windows)
        self.interval_button.setMinimumHeight(120)
        self.interval_button.setMinimumWidth(250)
        self.interval_button.setStyleSheet("""
            QPushButton {
                background-color: #9E9E9E;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 14px;
                font-weight: bold;
                padding: 15px;
            }
            QPushButton:hover {
                background-color: #757575;
            }
            QPushButton:pressed {
                background-color: #616161;
            }
            QPushButton:disabled {
                background-color: #BDBDBD;
                color: #f5f5f5;
            }
        """)
        buttons_layout.addWidget(self.interval_button, 1, 0)

        # Log Table button (gray)
        self.table_button = QPushButton("📋 Log Table")
        self.table_button.clicked.connect(self._open_log_table_window)
        self.table_button.setMinimumHeight(120)
        self.table_button.setMinimumWidth(250)
        self.table_button.setStyleSheet("""
            QPushButton {
                background-color: #9E9E9E;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 14px;
                font-weight: bold;
                padding: 15px;
            }
            QPushButton:hover {
                background-color: #757575;
            }
            QPushButton:pressed {
                background-color: #616161;
            }
            QPushButton:disabled {
                background-color: #BDBDBD;
                color: #f5f5f5;
            }
        """)
        buttons_layout.addWidget(self.table_button, 1, 1)

        content_layout.addWidget(buttons_container, 1)

        main_layout.addWidget(content_widget, 1)

        self.setStyleSheet("""
            QMainWindow {
                background-color: #ffffff;
            }
        """)

        self._update_navigation_buttons(False)

    def _update_navigation_buttons(self, has_data: bool):
        """Enable or disable navigation buttons based on parsed data availability."""
        self.timing_button.setEnabled(has_data)
        self.table_button.setEnabled(has_data)
        self.interval_button.setEnabled(has_data)
        # Map viewer can open without parsed data so keep it enabled
        self.map_button.setEnabled(True)

    def _create_menu_bar(self):
        """Create the menu bar with tools menu."""
        menu_bar = self.menuBar()
        tools_menu = menu_bar.addMenu("&Tools")

        timing_action = tools_menu.addAction("Open &Timing Diagram")
        timing_action.triggered.connect(self._open_timing_diagram_window)

        table_action = tools_menu.addAction("Open &Log Table")
        table_action.triggered.connect(self._open_log_table_window)

        map_viewer_action = tools_menu.addAction("Open Map &Viewer")
        map_viewer_action.triggered.connect(self._open_map_viewer)

        interval_action = tools_menu.addAction("Plot &Signal Intervals")
        interval_action.triggered.connect(self._open_signal_interval_windows)

    def _open_timing_diagram_window(self):
        """Launch or focus the timing diagram window."""
        if self._timing_window is not None:
            try:
                self._timing_window.show()
                self._timing_window.raise_()
                self._timing_window.activateWindow()
                return
            except RuntimeError:
                self._timing_window = None

        self._timing_window = TimingDiagramWindow(self)
        self._timing_window.set_interval_request_handler(self._open_signal_interval_for_key)
        self._timing_window.destroyed.connect(self._on_timing_window_destroyed)

        if self._merged_parsed_log:
            self._timing_window.set_data(self._merged_parsed_log, self._signal_data_list)
        else:
            self._timing_window.clear()

        if self._map_viewer_window is not None:
            try:
                self._timing_window.viewport_state.time_range_changed.connect(self._on_map_viewer_time_update)
            except (RuntimeError, TypeError):
                pass

        self._timing_window.show()
        self._timing_window.raise_()
        self._timing_window.activateWindow()

        if self._map_viewer_window is not None:
            visible_range = self._timing_window.viewport_state.visible_time_range
            if visible_range:
                start_time, _ = visible_range
                try:
                    self._map_viewer_window.update_time_position(start_time)
                except RuntimeError:
                    self._map_viewer_window = None

    def _on_timing_window_destroyed(self, _obj=None):
        """Reset timing window reference when it is closed."""
        self._timing_window = None

    def _open_log_table_window(self):
        """Launch or focus the log table window."""
        if self._table_window is not None:
            try:
                self._table_window.show()
                self._table_window.raise_()
                self._table_window.activateWindow()
                return
            except RuntimeError:
                self._table_window = None

        self._table_window = LogTableWindow(self)
        self._table_window.set_interval_request_handler(self._open_signal_interval_for_key)
        self._table_window.destroyed.connect(self._on_table_window_destroyed)

        if self._merged_parsed_log:
            self._table_window.set_data(self._merged_parsed_log, self._signal_data_list)
        else:
            self._table_window.clear()

        self._table_window.show()
        self._table_window.raise_()
        self._table_window.activateWindow()

    def _on_table_window_destroyed(self, _obj=None):
        """Reset table window reference when it is closed."""
        self._table_window = None

    def _open_map_viewer(self):
        """Launch the map viewer in a separate window."""
        try:
            from plc_visualizer.ui.integrated_map_viewer import IntegratedMapViewer

            if self._map_viewer_window is not None:
                try:
                    self._map_viewer_window.show()
                    self._map_viewer_window.raise_()
                    self._map_viewer_window.activateWindow()
                    return
                except RuntimeError:
                    self._map_viewer_window = None

            base_path = Path(__file__).parent.parent.parent / "tools" / "map_viewer"
            xml_file = None
            yaml_file = None

            if base_path.exists():
                candidate_xml = base_path / "test.xml"
                candidate_yaml = base_path / "mappings_and_rules.yaml"
                if candidate_xml.exists():
                    xml_file = candidate_xml
                if candidate_yaml.exists():
                    yaml_file = candidate_yaml

            self._map_viewer_window = IntegratedMapViewer(
                signal_data_list=self._signal_data_list,
                xml_path=str(xml_file) if xml_file else None,
                yaml_cfg=str(yaml_file) if yaml_file else None,
                parent=self,
            )

            if self._timing_window is not None:
                try:
                    self._timing_window.viewport_state.time_range_changed.connect(self._on_map_viewer_time_update)
                except (RuntimeError, TypeError):
                    pass

            self._map_viewer_window.show()
            self._map_viewer_window.raise_()
            self._map_viewer_window.activateWindow()

            if self._timing_window is not None:
                visible_range = self._timing_window.viewport_state.visible_time_range
                if visible_range:
                    start_time, _ = visible_range
                    try:
                        self._map_viewer_window.update_time_position(start_time)
                    except RuntimeError:
                        self._map_viewer_window = None

        except ImportError as e:
            QMessageBox.warning(
                self,
                "Map Viewer Not Available",
                f"Could not load the map viewer module:\n{str(e)}"
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error Opening Map Viewer",
                f"An error occurred while opening the map viewer:\n{str(e)}"
            )

    def _open_signal_interval_windows(self):
        """Open or focus signal interval windows instead of blocking dialogs."""
        if not self._signal_data_list:
            QMessageBox.information(
                self,
                "No Signals Loaded",
                "Load a PLC log before plotting signal intervals.",
            )
            return

        if len(self._signal_data_list) == 1:
            self._open_signal_interval_for_key(self._signal_data_list[0].key)
            return

        if self._interval_selection_window is not None:
            try:
                self._interval_selection_window.show()
                self._interval_selection_window.raise_()
                self._interval_selection_window.activateWindow()
                return
            except RuntimeError:
                self._interval_selection_window = None

        selector = SignalSelectionDialog(self._signal_data_list, self)
        selector.setModal(False)
        selector.setWindowModality(Qt.WindowModality.NonModal)
        selector.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        selector.accepted.connect(lambda sel=selector: self._handle_signal_selection(sel))
        selector.destroyed.connect(self._on_signal_selection_window_destroyed)
        self._interval_selection_window = selector

        selector.show()
        selector.raise_()
        selector.activateWindow()

    def _handle_signal_selection(self, selector: SignalSelectionDialog):
        """Handle acceptance from the non-modal signal selector."""
        selected_key = selector.selected_key
        if selected_key:
            self._open_signal_interval_for_key(selected_key)

    def _on_signal_selection_window_destroyed(self, _obj=None):
        """Clear selection window reference once it closes."""
        self._interval_selection_window = None

    def _ensure_signal_states(self, signal_data: SignalData) -> bool:
        """Ensure SignalData has populated states by recomputing if necessary."""
        if signal_data.states:
            return True

        if not self._merged_parsed_log:
            return False

        try:
            compute_signal_states(signal_data, self._merged_parsed_log)
        except Exception as exc:
            print(f"[Intervals] Failed to rebuild states for {signal_data.key}: {exc}")
            return False

        return bool(signal_data.states)

    def _pin_signal_data(self, signal_key: str):
        """Prevent a signal's states from being cleared while an interval window is open."""
        signal_data = self._signal_data_map.get(signal_key)
        if signal_data:
            signal_data.pinned = True

    def _unpin_signal_data(self, signal_key: str):
        """Allow a signal's states to be cleared when no window depends on it."""
        signal_data = self._signal_data_map.get(signal_key)
        if signal_data:
            signal_data.pinned = False

    def _on_interval_window_destroyed(self, signal_key: str):
        """Cleanup when a signal interval window is closed."""
        self._interval_windows.pop(signal_key, None)
        self._unpin_signal_data(signal_key)

    def _open_signal_interval_for_key(self, signal_key: str):
        """Open the signal interval dialog for a specific signal key."""
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
            if not self._ensure_signal_states(signal_data):
                QMessageBox.information(
                    self,
                    "Transitions Not Available",
                    "Could not reconstruct transitions for this signal. Reload the log and try again.",
                )
                return

        if len(signal_data.states) < 2:
            QMessageBox.information(
                self,
                "No Transitions",
                "This signal does not have enough transitions to plot change intervals.",
            )
            return

        existing = self._interval_windows.get(signal_key)
        if existing is not None:
            try:
                existing.show()
                existing.raise_()
                existing.activateWindow()
                return
            except RuntimeError:
                self._interval_windows.pop(signal_key, None)

        window = SignalIntervalDialog(signal_data, self)
        window.setModal(False)
        window.setWindowModality(Qt.WindowModality.NonModal)
        window.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        window.destroyed.connect(lambda _obj=None, key=signal_key: self._on_interval_window_destroyed(key))
        self._interval_windows[signal_key] = window
        self._pin_signal_data(signal_key)

        window.show()
        window.raise_()
        window.activateWindow()

    def _on_map_viewer_time_update(self, start_time, _end_time):
        """Update map viewer when waveform time changes."""
        if self._map_viewer_window is not None:
            try:
                self._map_viewer_window.update_time_position(start_time)
            except RuntimeError:
                self._map_viewer_window = None

    def _on_files_selected(self, file_paths: list[str]):
        """Handle selection of one or more files."""
        if not file_paths:
            return

        resolved_paths: list[str] = []
        missing_paths: list[str] = []

        for path in file_paths:
            normalized = str(Path(path).expanduser().resolve())
            if Path(normalized).is_file():
                if normalized not in resolved_paths:
                    resolved_paths.append(normalized)
            else:
                missing_paths.append(path)

        if missing_paths:
            missing_list = "\n".join(missing_paths)
            QMessageBox.warning(
                self,
                "Missing Files",
                f"The following files could not be found:\n\n{missing_list}"
            )

        if not resolved_paths:
            return

        self._current_files = resolved_paths

        # Add files to file list widget
        if self.file_list_widget:
            for file_path in resolved_paths:
                self.file_list_widget.add_file(file_path)

        self._parse_files(resolved_paths)

    def _parse_files(self, file_paths: list[str]):
        """Parse the selected log files in a background thread."""
        if self._parser_thread and self._parser_thread.isRunning():
            QMessageBox.information(
                self,
                "Parsing In Progress",
                "Please wait for the current parsing job to complete before starting a new one."
            )
            return

        if self._parser_thread:
            self._parser_thread.deleteLater()
            self._parser_thread = None

        # Show progress bar
        self.progress_bar.setVisible(True)
        self.upload_widget.setEnabled(False)
        names = ", ".join(Path(path).name for path in file_paths)
        self.upload_widget.set_status(
            f"📄 Parsing {len(file_paths)} file(s): {names}"
        )
        self.progress_bar.setRange(0, len(file_paths))
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("Parsing files... %p%")

        # Clear previous results
        if self.stats_widget:
            self.stats_widget.clear()
        self._merged_parsed_log = None
        self._signal_data_list = []
        self._signal_data_map = {}
        self._file_results = {}
        self._update_navigation_buttons(False)

        if self._timing_window is not None:
            try:
                self._timing_window.clear()
            except RuntimeError:
                self._timing_window = None

        if self._table_window is not None:
            try:
                self._table_window.clear()
            except RuntimeError:
                self._table_window = None

        if self._map_viewer_window is not None:
            try:
                self._map_viewer_window.set_signal_data([])
            except RuntimeError:
                self._map_viewer_window = None

        # Create and start parser thread
        self._parser_thread = ParserThread(file_paths, self)
        self._parser_thread.finished.connect(self._on_parse_finished)
        self._parser_thread.error.connect(self._on_parse_error)
        self._parser_thread.progress.connect(self._on_parse_progress)
        self._parser_thread.start()

    def _on_parse_finished(
        self,
        aggregated_result: ParseResult,
        per_file_results: dict[str, ParseResult],
        signal_data_list: list[SignalData],
    ):
        """Handle parsing completion.

        Args:
            aggregated_result: Combined ParseResult containing merged data/errors
            per_file_results: Mapping of file path to individual ParseResult
            signal_data_list: Pre-processed signal data ready for visualization
        """
        # Hide progress bar
        self.progress_bar.setVisible(False)
        self.progress_bar.reset()
        self.progress_bar.setFormat("Parsing files... %p%")
        self.upload_widget.setEnabled(True)

        # Hide progress bars in file list widget
        if self.file_list_widget:
            self.file_list_widget.hide_all_progress()

        self._file_results = per_file_results
        self._merged_parsed_log = aggregated_result.data

        total_files = len(self._current_files)
        successful_files = [
            path for path, result in per_file_results.items() if result.success
        ]
        failed_files = [
            path for path, result in per_file_results.items() if not result.success
        ]

        if self.stats_widget:
            self.stats_widget.update_stats(aggregated_result)

        if not aggregated_result.success:
            # No data parsed successfully
            primary_error = aggregated_result.errors[0] if aggregated_result.errors else None
            details = ""
            if primary_error:
                file_name = Path(primary_error.file_path).name if primary_error.file_path else "Unknown file"
                details = f":\n\n[{file_name}] {primary_error.reason}"

            QMessageBox.critical(
                self,
                "Parsing Error",
                f"Failed to parse selected files{details}"
            )
            self.upload_widget.set_status(
                "📁 Drag and drop log files here\nor click to browse"
            )
            self._signal_data_map = {}
            self._signal_data_list = []
            self._update_navigation_buttons(False)
            self._finalize_parser_thread()
            return

        # Update UI with results
        self._signal_data_list = signal_data_list
        self._signal_data_map = {signal.key: signal for signal in signal_data_list}

        if self._timing_window is not None:
            try:
                self._timing_window.set_data(aggregated_result.data, signal_data_list)
            except RuntimeError:
                self._timing_window = None

        if self._table_window is not None:
            try:
                self._table_window.set_data(aggregated_result.data, signal_data_list)
            except RuntimeError:
                self._table_window = None

        if self._map_viewer_window is not None:
            try:
                self._map_viewer_window.set_signal_data(signal_data_list)
            except RuntimeError:
                self._map_viewer_window = None

        has_data = aggregated_result.data is not None
        self._update_navigation_buttons(has_data)

        # Update upload widget status
        success_count = len(successful_files)
        status = f"✓ Loaded {success_count} of {total_files} file(s)"
        if aggregated_result.has_errors:
            status += f" with {aggregated_result.error_count} error(s)"
        self.upload_widget.set_status(status)

        # Show success message for significant errors
        if aggregated_result.has_errors and aggregated_result.error_count > 5:
            QMessageBox.warning(
                self,
                "Parsing Warnings",
                f"Files parsed with {aggregated_result.error_count} error(s).\n"
                f"Successfully parsed {aggregated_result.data.entry_count} entries.\n\n"
                f"See the statistics panel for details."
            )

        if failed_files:
            failed_names = "\n".join(Path(path).name for path in failed_files)
            QMessageBox.warning(
                self,
                "Parsing Warnings",
                "Some files could not be parsed:\n\n"
                f"{failed_names}\n\n"
                "See the statistics panel for error details."
            )
        self._finalize_parser_thread()

    def _on_parse_error(self, error_msg: str):
        """Handle parsing error.

        Args:
            error_msg: Error message
        """
        self.progress_bar.setVisible(False)
        self.upload_widget.setEnabled(True)

        self._update_navigation_buttons(False)
        QMessageBox.critical(self, "Error", error_msg)
        self.upload_widget.set_status(
            "📁 Drag and drop log files here\nor click to browse"
        )
        self._finalize_parser_thread()
        self.progress_bar.reset()
        self.progress_bar.setFormat("Parsing files... %p%")

    def _on_parse_progress(self, current: int, total: int, file_path: str):
        """Update progress bar as files are parsed."""
        if total <= 0:
            return

        self.progress_bar.setRange(0, total)
        self.progress_bar.setValue(current)
        filename = Path(file_path).name if file_path else ""
        self.progress_bar.setFormat(
            f"Parsing {current}/{total} file(s) - {filename}"
        )

        # Update individual file progress in the file list widget
        if self.file_list_widget and file_path:
            # Calculate progress for this file as a percentage
            file_progress = int((current / total) * 100) if total > 0 else 0
            self.file_list_widget.update_progress(file_path, file_progress)

    def _on_file_removed_from_list(self, file_path: str):
        """Handle file removal from file list widget (trash button clicked)."""
        if file_path in self._current_files:
            self._current_files.remove(file_path)

    def _on_clear_file(self):
        """Handle Clear File button click - reset everything."""
        # Clear file list
        if self.file_list_widget:
            self.file_list_widget.clear_all()

        # Clear current files
        self._current_files = []

        # Clear stats
        if self.stats_widget:
            self.stats_widget.clear()

        # Clear parsed data
        self._merged_parsed_log = None
        self._signal_data_list = []
        self._signal_data_map = {}
        self._file_results = {}

        # Reset upload widget
        self.upload_widget.set_status(
            "📁 Drag and drop log files here\nor click to browse"
        )

        # Close all sub-windows
        if self._timing_window is not None:
            try:
                self._timing_window.close()
                self._timing_window = None
            except RuntimeError:
                self._timing_window = None

        if self._table_window is not None:
            try:
                self._table_window.close()
                self._table_window = None
            except RuntimeError:
                self._table_window = None

        if self._map_viewer_window is not None:
            try:
                self._map_viewer_window.close()
                self._map_viewer_window = None
            except RuntimeError:
                self._map_viewer_window = None

        # Close all interval windows
        for window in list(self._interval_windows.values()):
            try:
                window.close()
            except RuntimeError:
                pass
        self._interval_windows.clear()

        # Update buttons
        self._update_navigation_buttons(False)

        # Stop parsing if in progress
        if self._parser_thread and self._parser_thread.isRunning():
            self._parser_thread.quit()
            self._parser_thread.wait()

    def resizeEvent(self, event: QResizeEvent):
        """Log resize information (useful for debugging Wayland sizing)."""
        super().resizeEvent(event)
        if self._is_wayland:
            handle = self.windowHandle()
            handle_size = handle.size() if handle else None
            print(f"[MainWindow] resizeEvent old={event.oldSize()}, new={event.size()}, handle_size={handle_size}")

    def _finalize_parser_thread(self):
        """Release references to the parser thread."""
        if self._parser_thread:
            self._parser_thread.deleteLater()
            self._parser_thread = None


atexit.register(ParserThread.shutdown_executor)
