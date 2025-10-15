"""Main application window for PLC Log Visualizer."""

from pathlib import Path
from datetime import timedelta
from typing import Dict, List

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QSplitter,
    QProgressBar,
    QMessageBox,
    QPushButton,
)

from plc_visualizer.models import ParseResult
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

    finished = pyqtSignal(object, object)  # aggregated_result, per_file_results
    error = pyqtSignal(str)

    def __init__(self, file_paths: List[str], parent=None):
        super().__init__(parent)
        self.file_paths = file_paths

    def run(self):
        """Parse files in a background thread."""
        try:
            per_file_results: Dict[str, ParseResult] = {}

            for file_path in self.file_paths:
                per_file_results[file_path] = parser_registry.parse(file_path)

            aggregated_result = merge_parse_results(per_file_results)
            self.finished.emit(aggregated_result, per_file_results)
        except Exception as e:
            self.error.emit(f"Failed to parse files: {str(e)}")


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self):
        super().__init__()
        self._current_files: list[str] = []
        self._merged_parsed_log = None
        self._file_results: Dict[str, ParseResult] = {}
        self._signal_data_list: list[SignalData] | None = None
        self._visible_signal_names: list[str] = []
        self._parser_thread = None
        self._viewport_state = ViewportState(self)
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

        # Left panel - statistics and filters
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(12)

        self.stats_widget = StatsWidget()
        self.stats_widget.setMaximumWidth(350)
        left_layout.addWidget(self.stats_widget)

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

        # Set initial horizontal split (roughly 30% stats/filters, 70% content)
        # main_splitter.setSizes([320, 680])

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
        # Show progress bar
        self.progress_bar.setVisible(True)
        self.upload_widget.setEnabled(False)
        names = ", ".join(Path(path).name for path in file_paths)
        self.upload_widget.set_status(
            f"📄 Parsing {len(file_paths)} file(s): {names}"
        )

        # Clear previous results
        self.stats_widget.clear()
        self.data_table.clear()
        self.waveform_view.clear()
        self.signal_filter.clear()
        self._merged_parsed_log = None
        self._signal_data_list = None
        self._visible_signal_names = []

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
        self._parser_thread.start()

    def _on_parse_finished(
        self,
        aggregated_result: ParseResult,
        per_file_results: dict[str, ParseResult],
    ):
        """Handle parsing completion.

        Args:
            aggregated_result: Combined ParseResult containing merged data/errors
            per_file_results: Mapping of file path to individual ParseResult
        """
        # Hide progress bar
        self.progress_bar.setVisible(False)
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
            self.signal_filter.clear()
            self.load_new_button.setVisible(True)
            return

        # Update UI with results
        signal_data_list = process_signals_for_waveform(aggregated_result.data)
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

    def _load_new_file(self):
        """Reset the UI to load a new file."""
        self.upload_widget.set_status(
            "📁 Drag and drop log files here\nor click to browse"
        )
        self.stats_widget.clear()
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
