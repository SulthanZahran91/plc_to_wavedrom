"""Graphics scene for waveform visualization."""

from datetime import datetime

from PySide6.QtWidgets import QGraphicsScene
from PySide6.QtCore import QRect

try:
    import shiboken6 as sip  # PySide6 uses shiboken6
    # For compatibility, create isdeleted from isValid
    # shiboken6 uses isValid instead of isDeleted
    if not hasattr(sip, 'isdeleted'):
        if hasattr(sip, 'isValid'):
            sip.isdeleted = lambda obj: not sip.isValid(obj)
        else:
            sip.isdeleted = lambda obj: False
except ImportError:  # pragma: no cover
    try:
        import sip  # Fallback for standalone sip
    except ImportError:
        # Create a dummy sip module if neither is available
        class _DummySip:
            @staticmethod
            def isdeleted(obj):
                return False
        sip = _DummySip()

from plc_visualizer.models import ParsedLog
from plc_visualizer.utils import (
    SignalData,
    process_signals_for_waveform,
    compute_signal_states,
)
from .time_axis_item import TimeAxisItem
from .signal_item import SignalItem
from .signal_label_item import SignalLabelItem
from .grid_lines_item import GridLinesItem
from .signal_row_item import SignalRowItem



class WaveformScene(QGraphicsScene):
    """Graphics scene containing the waveform visualization."""

    TIME_AXIS_HEIGHT = 30.0
    SIGNAL_HEIGHT = 60.0  # Increased from 40.0 for better visibility
    LABEL_WIDTH = 180.0  # Width of signal label column


    def __init__(self, parent=None):
        super().__init__(parent)

        self.parsed_log = None
        self.signal_items = []  # Waveform items only
        self.label_items = []  # Signal label items
        self.row_items = []
        self.time_axis = None
        self.grid_lines = None
        self.signal_data_map: dict[str, SignalData] = {}
        self.all_signal_names: list[str] = []
        self.visible_signal_names: list[str] = []

        # Scene dimensions
        self.scene_width = 1000.0
        self.scene_height = 100.0

        # Current visible time range (for viewport culling)
        self.visible_time_range = None

        self.setBackgroundBrush(self.palette().window())

    def set_data(
        self,
        parsed_log: ParsedLog,
        signal_data_list: list[SignalData] | None = None,
        lazy: bool = True
    ):
        """Set the parsed log data and render waveforms.

        Memory optimization: Uses lazy loading by default to avoid
        computing states for all signals upfront.

        Args:
            parsed_log: ParsedLog containing entries to visualize
            signal_data_list: Pre-computed signal data (optional)
            lazy: If True, compute states only for visible signals (default)
        """
        self.parsed_log = parsed_log
        self.visible_time_range = parsed_log.time_range if parsed_log else None

        # Reset collections
        self.signal_items.clear()
        self.label_items.clear()
        self.signal_data_map.clear()
        self.all_signal_names.clear()
        self.visible_signal_names.clear()
        self.row_items = []   # reset


        if not parsed_log or not parsed_log.time_range:
            self.clear()
            self.setSceneRect(0, 0, self.scene_width, self.TIME_AXIS_HEIGHT)
            return

        if signal_data_list is None:
            # Use lazy loading by default for memory efficiency
            signal_data_list = process_signals_for_waveform(parsed_log, lazy=lazy)

        self.signal_data_map = {signal.key: signal for signal in signal_data_list}
        self.all_signal_names = [signal.key for signal in signal_data_list]
        # self.visible_signal_names = list(self.all_signal_names)
        self.visible_signal_names = []

        self._build_scene()

    def update_width(self, width: float):
        """Update the scene width and redraw all items.

        Args:
            width: New width in pixels
        """
        new_width = max(width, 500.0)  # Minimum width
        if abs(self.scene_width - new_width) < 0.5:
            return  # No significant change; avoid unnecessary redraws

        self.scene_width = new_width
        waveform_width = max(self.scene_width - self.LABEL_WIDTH, 100.0)

        # Update grid lines
        if self.grid_lines and not sip.isdeleted(self.grid_lines):
            self.grid_lines.update_dimensions(self.scene_width, self.scene_height)
        else:
            self.grid_lines = None

        # Update time axis
        if self.time_axis and not sip.isdeleted(self.time_axis):
            self.time_axis.update_width(self.scene_width)
        else:
            self.time_axis = None

        # Update all signal waveform items (not labels - they're fixed width)
        alive_signal_items: list[SignalItem] = []
        for signal_item in self.signal_items:
            if sip.isdeleted(signal_item):
                continue
            signal_item.update_width(waveform_width)
            alive_signal_items.append(signal_item)
        self.signal_items = alive_signal_items

        # Update scene rect
        self.setSceneRect(0, 0, self.scene_width, self.scene_height)

        alive_rows: list[SignalRowItem] = []
        for row in self.row_items:
            if sip.isdeleted(row):
                continue
            row.update_width(self.scene_width)
            alive_rows.append(row)
        self.row_items = alive_rows
        self.setSceneRect(0, 0, self.scene_width, self.scene_height)


    def get_signal_count(self) -> int:
        """Get the number of signals displayed."""
        return len(self.signal_items)

    def set_time_range(self, start: datetime, end: datetime):
        """Update the visible time range for viewport culling.

        Args:
            start: Visible start time
            end: Visible end time
        """
        self.visible_time_range = (start, end)

        # Update time axis
        if self.time_axis and not sip.isdeleted(self.time_axis):
            self.time_axis.set_time_range(start, end)

        # Update grid lines
        if self.grid_lines and not sip.isdeleted(self.grid_lines):
            self.grid_lines.set_time_range(start, end)

        # Update all signal items
        alive_signal_items: list[SignalItem] = []
        for signal_item in self.signal_items:
            if sip.isdeleted(signal_item):
                continue
            signal_item.set_time_range(start, end)
            alive_signal_items.append(signal_item)
        self.signal_items = alive_signal_items

    def set_visible_signals(self, signal_names: list[str]):
        """Update which signals are visible and rebuild the scene.

        Memory optimization: Clears states for hidden signals and computes
        states on-demand for newly visible signals.
        """
        if not self.signal_data_map:
            return

        # Track which signals are being hidden/shown
        old_visible = set(self.visible_signal_names)

        if not signal_names:
            self.visible_signal_names = []
        else:
            desired = set(signal_names)
            self.visible_signal_names = [
                name for name in self.all_signal_names if name in desired
            ]

        new_visible = set(self.visible_signal_names)

        # Clear states for newly hidden signals to free memory
        hidden_signals = old_visible - new_visible
        for signal_key in hidden_signals:
            signal_data = self.signal_data_map.get(signal_key)
            if signal_data:
                signal_data.clear_states()

        # Compute states for newly visible signals that don't have them
        shown_signals = new_visible - old_visible
        for signal_key in shown_signals:
            signal_data = self.signal_data_map.get(signal_key)
            if signal_data and not signal_data.states and self.parsed_log:
                compute_signal_states(signal_data, self.parsed_log)

        self._build_scene()

    def _build_scene(self):
        """Rebuild the scene using the current visible signals."""
        self.clear()
        self.signal_items.clear()
        self.label_items.clear()
        self.row_items = []
        self.time_axis = None
        self.grid_lines = None

        if not self.parsed_log or not self.parsed_log.time_range:
            self.setSceneRect(0, 0, self.scene_width, self.TIME_AXIS_HEIGHT)
            return

        render_range = self.visible_time_range or self.parsed_log.time_range
        num_signals = len(self.visible_signal_names)
        self.scene_height = self.TIME_AXIS_HEIGHT + (num_signals * self.SIGNAL_HEIGHT)
        self.scene_height = max(self.scene_height, self.TIME_AXIS_HEIGHT + 10.0)

        waveform_width = max(self.scene_width - self.LABEL_WIDTH, 100.0)

        # Grid lines behind everything
        self.grid_lines = GridLinesItem(
            render_range,
            self.scene_width,
            self.scene_height
        )
        self.addItem(self.grid_lines)

        # Time axis
        self.time_axis = TimeAxisItem(
            render_range,
            self.scene_width,
            self.TIME_AXIS_HEIGHT
        )
        self.addItem(self.time_axis)
        
        # Add label and waveform pairs
        y_offset = self.TIME_AXIS_HEIGHT
        waveform_width = max(self.scene_width - self.LABEL_WIDTH, 100)
        row_total_width = self.scene_width
        
        for signal_name in self.visible_signal_names:
            signal_data = self.signal_data_map.get(signal_name)
            if not signal_data:
                continue

            label_item = SignalLabelItem(signal_data.device_id, signal_data.name)
            label_item.setPos(0, 0)
            
            # self.addItem(label_item)
            # self.label_items.append(label_item)

            signal_item = SignalItem(
                signal_data,
                render_range,
                waveform_width
            )
            signal_item.setPos(self.LABEL_WIDTH, 0)
            # self.addItem(signal_item)
            # self.signal_items.append(signal_item)
            
            row = SignalRowItem(
                label_item=label_item,
                waveform_item=signal_item,
                row_height=self.SIGNAL_HEIGHT,
                top_margin=self.TIME_AXIS_HEIGHT,
                total_width=row_total_width,
            )
            
            row.signal_key = signal_data.key             
            self.addItem(row)
            row.set_row_index(len(self.row_items))
            row.dropped.connect(self._on_row_dropped)
            
            self.label_items.append(label_item)
            self.signal_items.append(signal_item)
            
            self.row_items.append(row)


            # y_offset += self.SIGNAL_HEIGHT

        # Update scene rect
        self.setSceneRect(0, 0, self.scene_width, self.scene_height)

        # Ensure current time range is applied to new items
        if self.visible_time_range:
            start, end = self.visible_time_range
            self.set_time_range(start, end)
            
    def _on_row_dropped(self, row: SignalRowItem):
    # sort by visual Y
        ordered_rows = sorted(self.row_items, key=lambda r: r.pos().y())

        # snap rows to their exact slots
        for i, r in enumerate(ordered_rows):
            r.set_row_index(i)

        # update the logical order using the canonical keys you stored
        self.visible_signal_names = [r.signal_key for r in ordered_rows]

        # (no rebuild necessary here; items are already in place)
