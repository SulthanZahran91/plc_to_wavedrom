"""Embeddable timing diagram view with signal filters."""

from __future__ import annotations

from datetime import timedelta
from typing import Callable, Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import (
    QWidget,
    QSplitter,
    QVBoxLayout,
    QMessageBox,
)

from plc_visualizer.models import ParsedLog
from plc_visualizer.utils import SignalData, ViewportState
from ..components.waveform.waveform_view import WaveformView
from ..components.waveform.zoom_controls import ZoomControls
from ..components.waveform.pan_controls import PanControls
from ..components.waveform.time_range_selector import TimeRangeSelector
from ..components.signal_filter_widget import SignalFilterWidget
from ..theme import create_header_bar, card_panel_styles, surface_stylesheet


class TimingDiagramView(QWidget):
    """Embeddable view that hosts the waveform view alongside signal filters."""

    VIEW_TYPE = "timing_diagram"

    def __init__(self, viewport_state: ViewportState, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Timing Diagram")
        self._parsed_log: Optional[ParsedLog] = None
        self._signal_data_list: list[SignalData] = []
        self._signal_data_map: dict[str, SignalData] = {}
        self._interval_request_handler: Optional[Callable[[str], None]] = None

        self._viewport_state = viewport_state
        self._init_ui()
        self._connect_viewport_signals()
        self._update_controls_enabled(False)

    @property
    def view_type(self) -> str:
        """Return the type identifier for this view."""
        return self.VIEW_TYPE

    # Public API ---------------------------------------------------------
    @property
    def viewport_state(self) -> ViewportState:
        """Expose the viewport state for synchronization."""
        return self._viewport_state

    def set_interval_request_handler(self, handler: Callable[[str], None]):
        """Forward interval plotting requests to the provided handler."""
        self._interval_request_handler = handler
    
    def get_current_time(self):
        """Get the current time position from the viewport."""
        if not self._viewport_state:
            return None
        visible_range = self._viewport_state.visible_time_range
        if visible_range:
            return visible_range[0]  # Use start of visible range
        return None
    
    def keyPressEvent(self, event: QKeyEvent):
        """Handle keyboard shortcuts for navigation."""
        key = event.key()
        modifiers = event.modifiers()
        
        # No modifiers required for these shortcuts
        if modifiers == Qt.NoModifier:
            # Left Arrow - Pan left (backward in time)
            if key == Qt.Key_Left:
                self._on_pan_left()
                event.accept()
                return
            
            # Right Arrow - Pan right (forward in time)
            if key == Qt.Key_Right:
                self._on_pan_right()
                event.accept()
                return
            
            # Up Arrow - Scroll up through signals
            if key == Qt.Key_Up:
                scrollbar = self.waveform_view.verticalScrollBar()
                if scrollbar:
                    scrollbar.setValue(scrollbar.value() - scrollbar.singleStep())
                event.accept()
                return
            
            # Down Arrow - Scroll down through signals
            if key == Qt.Key_Down:
                scrollbar = self.waveform_view.verticalScrollBar()
                if scrollbar:
                    scrollbar.setValue(scrollbar.value() + scrollbar.singleStep())
                event.accept()
                return
            
            # Home - Jump to start of data
            if key == Qt.Key_Home:
                full_range = self._viewport_state.full_time_range
                if full_range:
                    start_time, _ = full_range
                    self._on_jump_to_time(start_time)
                event.accept()
                return
            
            # End - Jump to end of data
            if key == Qt.Key_End:
                full_range = self._viewport_state.full_time_range
                if full_range:
                    _, end_time = full_range
                    self._on_jump_to_time(end_time)
                event.accept()
                return
            
            # + or = - Zoom in
            if key in (Qt.Key_Plus, Qt.Key_Equal):
                self._viewport_state.zoom_in(factor=1.5)
                event.accept()
                return
            
            # - - Zoom out
            if key == Qt.Key_Minus:
                self._viewport_state.zoom_out(factor=1.5)
                event.accept()
                return
        
        # Let parent handle other events
        super().keyPressEvent(event)

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
        self.setObjectName("TimingViewSurface")
        self.setStyleSheet(surface_stylesheet("TimingViewSurface"))

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        header = create_header_bar(
            "Timing Diagram",
            "Waveform explorer for parsed PLC signals.",
        )
        root_layout.addWidget(header)

        content = QWidget()
        content.setObjectName("TimingWindowContent")
        content.setStyleSheet(surface_stylesheet("TimingWindowContent"))
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(16, 16, 16, 16)
        content_layout.setSpacing(12)
        root_layout.addWidget(content, stretch=1)

        splitter_frame = QWidget()
        splitter_frame.setObjectName("TimingSplitterCard")
        splitter_frame.setStyleSheet(card_panel_styles("TimingSplitterCard"))
        splitter_frame_layout = QVBoxLayout(splitter_frame)
        splitter_frame_layout.setContentsMargins(12, 12, 12, 12)
        splitter_frame_layout.setSpacing(0)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(10)
        splitter.setStyleSheet("""
            QSplitter::handle:horizontal {
                background-color: #d7dee4;
                margin: 0;
            }
        """)
        splitter_frame_layout.addWidget(splitter, stretch=1)
        content_layout.addWidget(splitter_frame, stretch=1)

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


# Backward compatibility alias
TimingDiagramWindow = TimingDiagramView
