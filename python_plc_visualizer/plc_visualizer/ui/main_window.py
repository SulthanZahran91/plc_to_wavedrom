"""Main application window for PLC Log Visualizer."""

from pathlib import Path
from datetime import timedelta
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

import cProfile
import pstats

from plc_visualizer.models import ParseResult
from plc_visualizer.parsers import parser_registry
from plc_visualizer.utils.viewport_state import ViewportState
from plc_visualizer.utils import process_signals_for_waveform, SignalData
from .file_upload_widget import FileUploadWidget
from .stats_widget import StatsWidget
from .data_table_widget import DataTableWidget
from .waveform_view import WaveformView
from .zoom_controls import ZoomControls
from .pan_controls import PanControls
from .time_range_selector import TimeRangeSelector
from .signal_filter_widget import SignalFilterWidget


class ParserThread(QThread):
    """Background thread for parsing log files."""

    finished = pyqtSignal(ParseResult)
    error = pyqtSignal(str)

    def __init__(self, file_path: str, parent=None):
        super().__init__(parent)
        self.file_path = file_path

    def run(self):
        """Parse the file in background thread."""
        try:
            
            import cProfile
            import pstats
            from pathlib import Path
            
            # Start profiling
            profiler = cProfile.Profile()
            profiler.enable()

            result = parser_registry.parse(self.file_path, num_workers=0)
            
            # Stop profiling
            profiler.disable()
            
            # Save profile to file
            profile_path = Path.home() / 'parse_profile.prof'
            profiler.dump_stats(str(profile_path))
            
            # Print quick summary to console
            stats = pstats.Stats(profiler)
            stats.sort_stats('cumulative')
            print(f"\n=== Profile saved to: {profile_path} ===")
            print("\nTop 10 slowest operations:")
            stats.print_stats(10)
            

            self.finished.emit(result)
        except Exception as e:
            self.error.emit(f"Failed to parse file: {str(e)}")


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self):
        super().__init__()
        self._current_file = None
        self._current_parsed_log = None
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
        self.upload_widget.file_selected.connect(self._on_file_selected)
        main_layout.addWidget(self.upload_widget)

        # Progress bar (initially hidden)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        self.progress_bar.setVisible(False)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("Parsing file... %p%")
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

    def _on_file_selected(self, file_path: str):
        """Handle file selection.

        Args:
            file_path: Path to the selected file
        """
        # Validate file exists
        if not Path(file_path).is_file():
            QMessageBox.critical(
                self,
                "Error",
                f"File not found: {file_path}"
            )
            return

        self._current_file = file_path
        self._parse_file(file_path)

    def _parse_file(self, file_path: str):
        """Parse the log file in background thread.

        Args:
            file_path: Path to the file to parse
        """
        
        # Show progress bar
        self.progress_bar.setVisible(True)
        self.upload_widget.setEnabled(False)
        self.upload_widget.set_status(f"📄 Parsing: {Path(file_path).name}...")

        # Clear previous results
        self.stats_widget.clear()
        self.data_table.clear()
        self.waveform_view.clear()

        # Create and start parser thread
        self._parser_thread = ParserThread(file_path, self)
        self._parser_thread.finished.connect(self._on_parse_finished)
        self._parser_thread.error.connect(self._on_parse_error)
        self._parser_thread.start()

    def _on_parse_finished(self, result: ParseResult):
        """Handle parsing completion.

        Args:
            result: ParseResult containing parsed data and errors
        """
        import time
        print(f"\n=== Parse finished, processing results ===")
        start = time.time()


        # Hide progress bar
        self.progress_bar.setVisible(False)
        self.upload_widget.setEnabled(True)

        if not result.success:
            # Parsing failed
            error_msg = "Failed to parse file"
            if result.errors:
                error_msg += f":\n\n{result.errors[0].reason}"

            QMessageBox.critical(self, "Parsing Error", error_msg)
            self.upload_widget.set_status(
                "📁 Drag and drop a log file here\nor click to browse"
            )
            return

        # Update UI with results
        # t = time.time()
        self.stats_widget.update_stats(result)
        self._current_parsed_log = result.data
        # print(f"update_stats: {time.time() - t:.2f}s")

        # t = time.time()
        signal_data_list = process_signals_for_waveform(result.data)
        # print(f"process_signals_for_waveform: {time.time() - t:.2f}s")
        
        # t = time.time()
        self._signal_data_list = signal_data_list
        self._visible_signal_names = [signal.key for signal in signal_data_list]
        
        # print(f"About to call waveform_view.set_data with {len(signal_data_list)} signals...")
        self.waveform_view.set_data(result.data, signal_data_list)
        # print(f"waveform_view.set_data: {time.time() - t:.2f}s")
        # t = time.time()
        self.data_table.set_data(result.data)
        # print(f"data_table.set_data: {time.time() - t:.2f}s")

        # t = time.time()
        self.signal_filter.set_signals(signal_data_list)
        # print(f"signal_filter.set_signals: {time.time() - t:.2f}s")


        # Initialize viewport state with the time range
        if result.data and result.data.time_range:
            start_time, end_time = result.data.time_range
            self._viewport_state.set_full_time_range(start_time, end_time)
        
            initial_end = start_time + timedelta(seconds=10)  # 10 seconds from start
            if initial_end > end_time:
                initial_end = end_time  # Don't exceed actual data

            self._viewport_state.set_time_range(start_time, initial_end)

            # self._viewport_state.time_range_changed.emit(start_time, initial_end)  # ← Add this

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
        file_name = Path(self._current_file).name if self._current_file else "file"
        status = f"✓ Successfully loaded: {file_name}"
        if result.has_errors:
            status += f" ({result.error_count} error(s))"
        self.upload_widget.set_status(status)

        # Show load new file button
        self.load_new_button.setVisible(True)

        # Show success message for significant errors
        if result.has_errors and result.error_count > 5:
            QMessageBox.warning(
                self,
                "Parsing Warnings",
                f"File parsed with {result.error_count} error(s).\n"
                f"Successfully parsed {result.data.entry_count} entries.\n\n"
                f"See the statistics panel for details."
            )
        print(f"TOTAL _on_parse_finished: {time.time() - start:.2f}s")


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
            "📁 Drag and drop a log file here\nor click to browse"
        )

    def _load_new_file(self):
        """Reset the UI to load a new file."""
        self.upload_widget.set_status(
            "📁 Drag and drop a log file here\nor click to browse"
        )
        self.stats_widget.clear()
        self.data_table.clear()
        self.waveform_view.clear()
        self.signal_filter.clear()
        self.load_new_button.setVisible(False)
        self._current_file = None
        self._current_parsed_log = None
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

        if self._current_parsed_log is None:
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
