"""UI components for the PLC Visualizer."""

from .main_window import MainWindow
from .file_upload_widget import FileUploadWidget
from .stats_widget import StatsWidget
from .data_table_widget import DataTableWidget
from .waveform_view import WaveformView
from .signal_filter_widget import SignalFilterWidget
from .ClickableLabel import ClickableLabel


__all__ = [
    'MainWindow',
    'FileUploadWidget',
    'StatsWidget',
    'DataTableWidget',
    'WaveformView',
    'SignalFilterWidget'
    'ClickableLabel'
]
