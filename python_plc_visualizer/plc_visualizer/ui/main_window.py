"""Main application window for PLC Log Visualizer."""

import atexit
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from datetime import timedelta
from typing import Dict, List
import multiprocessing as mp
from multiprocessing.context import BaseContext

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QResizeEvent
from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QSplitter,
    QProgressBar,
    QMessageBox,
    QPushButton,
    QApplication,
)

from plc_visualizer.models import ParseResult, ParsedLog
from plc_visualizer.parsers import parser_registry
from plc_visualizer.utils.viewport_state import ViewportState
from plc_visualizer.utils import (
    SignalData,
    merge_parse_results,
    process_signals_for_waveform,
)
from .file_upload_widget import FileUploadWidget
from .stats_widget import StatsWidget
from .data_table_widget import DataTableWidget
from .waveform_view import WaveformView
from .zoom_controls import ZoomControls
from .pan_controls import PanControls
from .time_range_selector import TimeRangeSelector
from .signal_filter_widget import SignalFilterWidget


class ParserThread(QThread):
    """Background thread for parsing one or more log files."""

    finished = pyqtSignal(object, object, object)  # aggregated_result, per_file_results, signal_data_list
    progress = pyqtSignal(int, int, str)  # current_index, total_files, file_path
    error = pyqtSignal(str)
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
        self._merged_parsed_log = None
        self._file_results: Dict[str, ParseResult] = {}
        self._signal_data_list: list[SignalData] | None = None
        self._visible_signal_names: list[str] = []
        self._parser_thread = None
        self._viewport_state = ViewportState(self)
        self._stats_holder = None
        self._stats_holder_layout = None
        self._left_layout = None
        self._init_ui()
        

    def _init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("PLC Log Visualizer")

        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # File upload section
        self.upload_widget = FileUploadWidget()
        self.upload_widget.files_selected.connect(self._on_files_selected)
        main_layout.addWidget(self.upload_widget)

        # Progress bar (initially hidden)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        self.progress_bar.setVisible(False)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("Parsing files... %p%")
        main_layout.addWidget(self.progress_bar)

        # Main content splitter (stats on left, content on right)
        main_splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left panel - statistic and filters
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(12)
        self._left_layout = left_layout

        self._stats_holder = QWidget()
        self._stats_holder.destroyed.connect(self._on_stats_holder_destroyed)
        self._stats_holder_layout = QVBoxLayout(self._stats_holder)
        self._stats_holder_layout.setContentsMargins(0, 0, 0, 0)
        self._stats_holder_layout.setSpacing(0)

        self.stats_widget = StatsWidget(self._stats_holder)
        self.stats_widget.setMaximumWidth(350)
        self.stats_widget.destroyed.connect(self._on_stats_widget_destroyed)
        self._stats_holder_layout.addWidget(self.stats_widget)

        left_layout.addWidget(self._stats_holder)
        self.signal_filter = SignalFilterWidget()
        self.signal_filter.visible_signals_changed.connect(self._on_visible_signals_changed)
        left_layout.addWidget(self.signal_filter, stretch=1)

        main_splitter.addWidget(left_panel)

        # Right panel - Vertical splitter for waveform and table
        right_splitter = QSplitter(Qt.Orientation.Vertical)

        # Waveform section with controls
        waveform_container = QWidget()
        waveform_layout = QVBoxLayout(waveform_container)
        waveform_layout.setContentsMargins(0, 0, 0, 0)
        waveform_layout.setSpacing(5)

        # Zoom controls
        self.zoom_controls = ZoomControls()
        self.zoom_controls.zoom_in_clicked.connect(self._on_zoom_in)
        self.zoom_controls.zoom_out_clicked.connect(self._on_zoom_out)
        self.zoom_controls.reset_zoom_clicked.connect(self._on_reset_zoom)
        self.zoom_controls.zoom_level_changed.connect(self._on_zoom_slider_changed)
        self.zoom_controls.set_enabled(False)
        waveform_layout.addWidget(self.zoom_controls)

        # Waveform view
        self.waveform_view = WaveformView()
        self.waveform_view.set_viewport_state(self._viewport_state)
        self.waveform_view.wheel_zoom.connect(self._on_wheel_zoom)
        waveform_layout.addWidget(self.waveform_view, stretch=1)

        # Pan controls
        self.pan_controls = PanControls()
        self.pan_controls.pan_left_clicked.connect(self._on_pan_left)
        self.pan_controls.pan_right_clicked.connect(self._on_pan_right)
        self.pan_controls.jump_to_time.connect(self._on_jump_to_time)
        self.pan_controls.scroll_changed.connect(self._on_scroll_changed)
        self.pan_controls.set_enabled(False)
        waveform_layout.addWidget(self.pan_controls)

        # Time range selector
        self.time_range_selector = TimeRangeSelector()
        self.time_range_selector.time_range_changed.connect(self._on_time_range_selector_changed)
        waveform_layout.addWidget(self.time_range_selector)

        right_splitter.addWidget(waveform_container)

        # Data table (bottom)
        self.data_table = DataTableWidget()
        right_splitter.addWidget(self.data_table)

        # Set initial vertical split (60% waveform, 40% table)
        # right_splitter.setSizes([600, 400])

        main_splitter.addWidget(right_splitter)
        main_layout.addWidget(main_splitter, stretch=1)

        # Bottom action bar
        action_layout = QHBoxLayout()

        self.load_new_button = QPushButton("Load New File")
        self.load_new_button.clicked.connect(self._load_new_file)
        self.load_new_button.setVisible(False)

        action_layout.addWidget(self.load_new_button)
        action_layout.addStretch()

        main_layout.addLayout(action_layout)

        # Apply overall styling
        self.setStyleSheet("""
            QMainWindow {
                background-color: #ffffff;
            }
            QPushButton {
                padding: 8px 16px;
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #0D47A1;
            }
        """)

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
        self._invoke_stats_widget("clear")
        self.data_table.clear()
        self.waveform_view.clear()
        self.signal_filter.clear()
        self._merged_parsed_log = None
        self._signal_data_list = None
        self._visible_signal_names = []
        self.zoom_controls.set_enabled(False)
        self.pan_controls.set_enabled(False)

        # Disconnect previous viewport listeners to avoid duplicates
        try:
            self._viewport_state.zoom_level_changed.disconnect(self.zoom_controls.set_zoom_level)
        except TypeError:
            pass
        try:
            self._viewport_state.time_range_changed.disconnect(self._on_viewport_time_range_changed)
        except TypeError:
            pass

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

        self._file_results = per_file_results
        self._merged_parsed_log = aggregated_result.data

        total_files = len(self._current_files)
        successful_files = [
            path for path, result in per_file_results.items() if result.success
        ]
        failed_files = [
            path for path, result in per_file_results.items() if not result.success
        ]

        self._invoke_stats_widget("update_stats", aggregated_result)

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
            self.signal_filter.clear()
            self.load_new_button.setVisible(True)
            self._finalize_parser_thread()
            return

        # Update UI with results
        self._signal_data_list = signal_data_list
        self._visible_signal_names = [signal.key for signal in signal_data_list]

        self.waveform_view.set_data(aggregated_result.data, signal_data_list)
        self.data_table.set_data(aggregated_result.data)
        self.signal_filter.set_signals(signal_data_list)

        # Initialize viewport state with the time range
        if aggregated_result.data and aggregated_result.data.time_range:
            start_time, end_time = aggregated_result.data.time_range
            self._viewport_state.set_full_time_range(start_time, end_time)

            initial_end = start_time + timedelta(seconds=10)  # 10 seconds from start
            if initial_end > end_time:
                initial_end = end_time  # Don't exceed actual data

            self._viewport_state.set_time_range(start_time, initial_end)

            # Update controls
            self.pan_controls.set_time_range(start_time, end_time)
            self.time_range_selector.set_full_time_range(start_time, end_time)

            # Enable navigation controls
            self.zoom_controls.set_enabled(True)
            self.pan_controls.set_enabled(True)

            # Connect viewport state changes to update controls
            self._viewport_state.zoom_level_changed.connect(self.zoom_controls.set_zoom_level)
            self._viewport_state.time_range_changed.connect(self._on_viewport_time_range_changed)

        # Update upload widget status
        success_count = len(successful_files)
        status = f"✓ Loaded {success_count} of {total_files} file(s)"
        if aggregated_result.has_errors:
            status += f" with {aggregated_result.error_count} error(s)"
        self.upload_widget.set_status(status)

        # Show load new file button
        self.load_new_button.setVisible(True)

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

        self.signal_filter.clear()
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

    def _load_new_file(self):
        """Reset the UI to load a new file."""
        self.upload_widget.set_status(
            "📁 Drag and drop log files here\nor click to browse"
        )
        self.data_table.clear()
        self.waveform_view.clear()
        self.signal_filter.clear()
        self.load_new_button.setVisible(False)
        self._current_files = []
        self._merged_parsed_log = None
        self._file_results = {}
        self._signal_data_list = None
        self._visible_signal_names = []

        # Disable navigation controls
        self.zoom_controls.set_enabled(False)
        self.pan_controls.set_enabled(False)
        self._invoke_stats_widget("clear")

    def _invoke_stats_widget(self, method_name: str, *args):
        """Safely invoke a method on the stats widget."""
        widget = self.stats_widget
        if widget is None:
            widget = self._create_stats_widget()
        if widget is None:
            return

        try:
            getattr(widget, method_name)(*args)
        except RuntimeError:
            self.stats_widget = None
            widget = self._create_stats_widget()
            if widget is not None:
                getattr(widget, method_name)(*args)

    def _create_stats_widget(self) -> StatsWidget | None:
        """Create a fresh stats widget, attaching it to the holder layout."""
        holder = self._ensure_stats_holder()
        layout = self._stats_holder_layout

        if holder is None or layout is None:
            return None

        # Remove any existing stats widget instance
        old_widget = self.stats_widget
        if old_widget is not None:
            print("[Stats] Removing existing stats widget before recreation")
            try:
                index = layout.indexOf(old_widget)
                if index != -1:
                    layout.takeAt(index)
            except RuntimeError:
                index = -1
            try:
                old_widget.setParent(None)
            except RuntimeError:
                pass
            try:
                old_widget.deleteLater()
            except RuntimeError:
                pass

        print("[Stats] Creating new StatsWidget instance")
        widget = StatsWidget(holder)
        widget.setMaximumWidth(350)
        widget.destroyed.connect(self._on_stats_widget_destroyed)
        layout.insertWidget(0, widget)
        self.stats_widget = widget
        return widget

    def _ensure_stats_holder(self) -> QWidget | None:
        """Ensure the stats holder widget and layout exist."""
        holder = self._stats_holder

        if holder is None:
            print("[Stats] Creating stats holder widget")
            holder = QWidget()
            holder.destroyed.connect(self._on_stats_holder_destroyed)
            self._stats_holder = holder

            layout = QVBoxLayout(holder)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(0)
            self._stats_holder_layout = layout

            if self._left_layout is not None:
                try:
                    self._left_layout.insertWidget(0, holder)
                except RuntimeError:
                    pass
                else:
                    print(f"[Stats] Inserted stats holder into left layout. Current count: {self._left_layout.count()}")
        elif self._stats_holder_layout is None:
            layout = QVBoxLayout(holder)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(0)
            self._stats_holder_layout = layout
            print("[Stats] Recreated stats holder layout")

        return self._stats_holder

    def _on_stats_widget_destroyed(self, _obj=None):
        """Reset stats widget reference when underlying QObject is destroyed."""
        self.stats_widget = None

    def _on_stats_holder_destroyed(self, _obj=None):
        """Reset stats holder references when destroyed."""
        self._stats_holder = None
        self._stats_holder_layout = None
        self.stats_widget = None

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

    # Zoom control handlers
    def _on_zoom_in(self):
        """Handle zoom in button click."""
        self._viewport_state.zoom_in(factor=1.5)

    def _on_zoom_out(self):
        """Handle zoom out button click."""
        self._viewport_state.zoom_out(factor=1.5)

    def _on_reset_zoom(self):
        """Handle reset zoom button click."""
        self._viewport_state.reset_zoom()

    def _on_zoom_slider_changed(self, zoom: float):
        """Handle zoom slider change.

        Args:
            zoom: New zoom level from slider
        """
        self._viewport_state.set_zoom_level(zoom)

    def _on_wheel_zoom(self, delta: int):
        """Handle mouse wheel zoom.

        Args:
            delta: Wheel delta (positive = zoom in, negative = zoom out)
        """
        if delta > 0:
            self._viewport_state.zoom_in(factor=1.2)
        else:
            self._viewport_state.zoom_out(factor=1.2)

    # Pan control handlers
    def _on_pan_left(self):
        """Handle pan left button click."""
        # Pan by 10% of visible duration
        if self._viewport_state.visible_duration:
            delta_seconds = -self._viewport_state.visible_duration.total_seconds() * 0.1
            self._viewport_state.pan(delta_seconds)

    def _on_pan_right(self):
        """Handle pan right button click."""
        # Pan by 10% of visible duration
        if self._viewport_state.visible_duration:
            delta_seconds = self._viewport_state.visible_duration.total_seconds() * 0.1
            self._viewport_state.pan(delta_seconds)

    def _on_jump_to_time(self, target_time):
        """Handle jump to time request.

        Args:
            target_time: Target datetime to jump to
        """
        self._viewport_state.jump_to_time(target_time)

    def _on_scroll_changed(self, position: float):
        """Handle scrollbar position change.

        Args:
            position: Position as fraction (0.0 to 1.0)
        """
        if not self._viewport_state.full_time_range:
            return

        full_start, full_end = self._viewport_state.full_time_range
        visible_range = self._viewport_state.visible_time_range

        if not visible_range:
            return

        visible_start, visible_end = visible_range
        visible_duration = visible_end - visible_start

        # Calculate new start time based on scroll position
        full_duration = full_end - full_start
        max_start_offset = full_duration - visible_duration

        from datetime import timedelta
        new_start = full_start + timedelta(seconds=position * max_start_offset.total_seconds())
        new_end = new_start + visible_duration

        self._viewport_state.set_time_range(new_start, new_end)

    def _on_visible_signals_changed(self, visible_names: list[str]):
        """Handle updates from the signal filter widget."""
        self._visible_signal_names = visible_names

        if self._merged_parsed_log is None:
            return

        self.waveform_view.set_visible_signals(visible_names)
        self.data_table.filter_signals(set(visible_names))

    def _on_time_range_selector_changed(self, start, end):
        """Handle time range selector change.

        Args:
            start: New start time
            end: New end time
        """
        self._viewport_state.set_time_range(start, end)

    def _on_viewport_time_range_changed(self, start, end):
        """Handle viewport time range changes to update controls.

        Args:
            start: New visible start time
            end: New visible end time
        """
        # Update time range selector
        self.time_range_selector.set_visible_time_range(start, end)

        # Update scroll position
        if self._viewport_state.full_time_range:
            full_start, full_end = self._viewport_state.full_time_range
            full_duration = (full_end - full_start).total_seconds()
            visible_duration = (end - start).total_seconds()
            visible_fraction = 1.0

            if full_duration > 0:
                visible_fraction = min(1.0, visible_duration / full_duration)

            if full_duration > visible_duration:
                # Calculate scroll position
                offset = (start - full_start).total_seconds()
                max_offset = full_duration - visible_duration
                position = offset / max_offset if max_offset > 0 else 0.0
                self.pan_controls.set_scroll_position(position, visible_fraction)
            else:
                self.pan_controls.set_scroll_position(0.0, visible_fraction)


atexit.register(ParserThread.shutdown_executor)
