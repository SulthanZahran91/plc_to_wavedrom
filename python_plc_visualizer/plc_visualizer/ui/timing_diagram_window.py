"""Standalone window for viewing the timing diagram with signal filters."""

from __future__ import annotations

from datetime import timedelta
from typing import Callable, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QSplitter,
    QVBoxLayout,
    QHBoxLayout,
    QMessageBox,
)

from plc_visualizer.models import ParsedLog
from plc_visualizer.utils import SignalData, ViewportState
from .waveform_view import WaveformView
from .zoom_controls import ZoomControls
from .pan_controls import PanControls
from .time_range_selector import TimeRangeSelector
from .signal_filter_widget import SignalFilterWidget


class TimingDiagramWindow(QMainWindow):
    """Window that hosts the waveform view alongside signal filters."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Timing Diagram")
        self._parsed_log: Optional[ParsedLog] = None
        self._signal_data_list: list[SignalData] = []
        self._signal_data_map: dict[str, SignalData] = {}
        self._interval_request_handler: Optional[Callable[[str], None]] = None

        self._viewport_state = ViewportState(self)
        self._init_ui()
        self._connect_viewport_signals()
        self._update_controls_enabled(False)

    # Public API ---------------------------------------------------------
    @property
    def viewport_state(self) -> ViewportState:
        """Expose the viewport state for synchronization."""
        return self._viewport_state

    def set_interval_request_handler(self, handler: Callable[[str], None]):
        """Forward interval plotting requests to the provided handler."""
        self._interval_request_handler = handler

    def clear(self):
        """Remove any loaded data and disable controls."""
        self._parsed_log = None
        self._signal_data_list = []
        self._signal_data_map.clear()
        self.waveform_view.clear()
        self.signal_filter.clear()
        self._update_controls_enabled(False)

    def set_data(self, parsed_log: Optional[ParsedLog], signal_data: list[SignalData]):
        """Load parsed data into the window.

        Args:
            parsed_log: Parsed log entries to visualize.
            signal_data: Pre-processed signal data for waveform rendering.
        """
        if parsed_log is None:
            self.clear()
            return

        self._parsed_log = parsed_log
        self._signal_data_list = list(signal_data)
        self._signal_data_map = {item.key: item for item in signal_data}

        self.waveform_view.set_data(parsed_log, signal_data)
        self.signal_filter.set_signals(signal_data)
        self._update_controls_enabled(bool(signal_data))

        if parsed_log.time_range:
            start_time, end_time = parsed_log.time_range
            self._viewport_state.set_full_time_range(start_time, end_time)

            initial_end = start_time + timedelta(seconds=10)
            if initial_end > end_time:
                initial_end = end_time

            self._viewport_state.set_time_range(start_time, initial_end)
            self.time_range_selector.set_full_time_range(start_time, end_time)
            self.pan_controls.set_time_range(start_time, end_time)

    # Internal helpers ---------------------------------------------------
    def _init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        outer_layout = QVBoxLayout(central)
        outer_layout.setContentsMargins(12, 12, 12, 12)
        outer_layout.setSpacing(10)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(10)
        splitter.setStyleSheet("""
            QSplitter::handle:horizontal {
                background-color: #d7dee4;
                margin: 0px;
            }
        """)
        outer_layout.addWidget(splitter, stretch=1)

        # Filter panel
        filter_container = QWidget()
        filter_layout = QVBoxLayout(filter_container)
        filter_layout.setContentsMargins(0, 0, 0, 0)
        filter_layout.setSpacing(0)

        self.signal_filter = SignalFilterWidget()
        self.signal_filter.visible_signals_changed.connect(self._on_visible_signals_changed)
        self.signal_filter.plot_intervals_requested.connect(self._handle_plot_intervals)
        filter_layout.addWidget(self.signal_filter)

        splitter.addWidget(filter_container)

        # Waveform panel
        waveform_container = QWidget()
        waveform_layout = QVBoxLayout(waveform_container)
        waveform_layout.setContentsMargins(0, 0, 0, 0)
        waveform_layout.setSpacing(8)

        self.zoom_controls = ZoomControls()
        self.zoom_controls.zoom_in_clicked.connect(lambda: self._viewport_state.zoom_in(factor=1.5))
        self.zoom_controls.zoom_out_clicked.connect(lambda: self._viewport_state.zoom_out(factor=1.5))
        self.zoom_controls.reset_zoom_clicked.connect(self._viewport_state.reset_zoom)
        self.zoom_controls.duration_changed.connect(self._on_duration_slider_changed)
        waveform_layout.addWidget(self.zoom_controls)

        self.waveform_view = WaveformView()
        self.waveform_view.set_viewport_state(self._viewport_state)
        self.waveform_view.wheel_zoom.connect(self._on_wheel_zoom)
        waveform_layout.addWidget(self.waveform_view, stretch=1)

        self.pan_controls = PanControls()
        self.pan_controls.pan_left_clicked.connect(self._on_pan_left)
        self.pan_controls.pan_right_clicked.connect(self._on_pan_right)
        self.pan_controls.jump_to_time.connect(self._on_jump_to_time)
        self.pan_controls.scroll_changed.connect(self._on_scroll_changed)
        waveform_layout.addWidget(self.pan_controls)

        self.time_range_selector = TimeRangeSelector()
        self.time_range_selector.time_range_changed.connect(self._on_time_range_selector_changed)
        waveform_layout.addWidget(self.time_range_selector)

        splitter.addWidget(waveform_container)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([320, 900])

    def _connect_viewport_signals(self):
        self._viewport_state.duration_changed.connect(self._on_viewport_duration_changed)
        self._viewport_state.time_range_changed.connect(self._on_viewport_time_range_changed)

    def _update_controls_enabled(self, enabled: bool):
        self.zoom_controls.set_enabled(enabled)
        self.pan_controls.set_enabled(enabled)
        self.time_range_selector.setEnabled(enabled)

    # Viewport interaction handlers -------------------------------------
    def _on_duration_slider_changed(self, duration_seconds: float):
        self._viewport_state.set_visible_duration(duration_seconds)

    def _on_viewport_duration_changed(self, duration_seconds: float):
        self.zoom_controls.set_visible_duration(
            duration_seconds,
            min_duration=self._viewport_state.min_visible_duration,
            max_duration=self._viewport_state.max_visible_duration,
        )

    def _on_wheel_zoom(self, delta: int):
        if delta > 0:
            self._viewport_state.zoom_in(factor=1.2)
        else:
            self._viewport_state.zoom_out(factor=1.2)

    def _on_pan_left(self):
        if self._viewport_state.visible_duration:
            delta = -self._viewport_state.visible_duration.total_seconds() * 0.1
            self._viewport_state.pan(delta)

    def _on_pan_right(self):
        if self._viewport_state.visible_duration:
            delta = self._viewport_state.visible_duration.total_seconds() * 0.1
            self._viewport_state.pan(delta)

    def _on_jump_to_time(self, target_time):
        self._viewport_state.jump_to_time(target_time)

    def _on_scroll_changed(self, position: float):
        full_range = self._viewport_state.full_time_range
        visible_range = self._viewport_state.visible_time_range

        if not full_range or not visible_range:
            return

        full_start, full_end = full_range
        visible_start, visible_end = visible_range
        visible_duration = visible_end - visible_start

        full_duration = full_end - full_start
        max_start_offset = full_duration - visible_duration
        if max_start_offset.total_seconds() <= 0:
            return

        new_start = full_start + timedelta(seconds=position * max_start_offset.total_seconds())
        new_end = new_start + visible_duration
        self._viewport_state.set_time_range(new_start, new_end)

    def _on_time_range_selector_changed(self, start, end):
        self._viewport_state.set_time_range(start, end)

    def _on_viewport_time_range_changed(self, start, end):
        self.time_range_selector.set_visible_time_range(start, end)

        full_range = self._viewport_state.full_time_range
        if not full_range:
            return

        full_start, full_end = full_range
        full_duration = (full_end - full_start).total_seconds()
        visible_duration = (end - start).total_seconds()
        visible_fraction = 1.0

        if full_duration > 0:
            visible_fraction = min(1.0, visible_duration / full_duration)

        if full_duration > visible_duration and full_duration > 0:
            offset = (start - full_start).total_seconds()
            max_offset = full_duration - visible_duration
            position = offset / max_offset if max_offset > 0 else 0.0
            self.pan_controls.set_scroll_position(position, visible_fraction)
        else:
            self.pan_controls.set_scroll_position(0.0, visible_fraction)

    # Filter integration -------------------------------------------------
    def _on_visible_signals_changed(self, visible_names: list[str]):
        if self._parsed_log is None:
            return
        self.waveform_view.set_visible_signals(visible_names)

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
