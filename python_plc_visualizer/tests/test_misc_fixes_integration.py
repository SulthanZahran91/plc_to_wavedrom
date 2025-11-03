"""End-to-end integration tests for miscellaneous fixes."""

import pytest
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QSplitter

from plc_visualizer.app.session_manager import SessionManager
from plc_visualizer.models import LogEntry, ParsedLog, SignalType
from plc_visualizer.utils import SignalData, SignalState
from plc_visualizer.parsers.plc_parser import PLCDebugParser
from plc_visualizer.ui.components.split_pane_manager import SplitPaneManager
from plc_visualizer.ui.components.stats_widget import StatsWidget
from plc_visualizer.ui.windows.interval_window import SignalIntervalDialog
from plc_visualizer.ui.windows.log_table_window import LogTableView


@pytest.fixture
def sample_log_file():
    """Create a temporary log file for testing."""
    content = """2024-01-01 10:00:00.000 [] B1ACNV13301-104@::/CARRIER_DETECTED	<-	True		L1	0	0	2024-01-01 10:00:00.000
2024-01-01 10:00:01.000 [] B1ACNV13301-104@::/CARRIER_ID	<-	ABC123		L1	0	0	2024-01-01 10:00:01.000
2024-01-01 10:00:02.000 [] B1ACNV13301-104@::/CONVEYOR_MOVE	<-	True		L1	0	0	2024-01-01 10:00:02.000
2024-01-01 10:00:03.000 [] B1ACNV13301-104@::/CARRIER_DETECTED	<-	False		L1	0	0	2024-01-01 10:00:03.000
2024-01-01 10:00:04.000 [] B1ACNV13301-104@::/CONVEYOR_MOVE	<-	False		L1	0	0	2024-01-01 10:00:04.000
"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
        f.write(content)
        temp_path = f.name
    
    yield temp_path
    
    Path(temp_path).unlink()


@pytest.fixture
def parsed_log_with_signal_data():
    """Create parsed log and signal data for testing."""
    base_time = datetime(2024, 1, 1, 10, 0, 0)
    device_id = "B1ACNV13301-104"
    
    entries = [
        LogEntry(device_id, "CARRIER_DETECTED", base_time, True, SignalType.BOOLEAN),
        LogEntry(device_id, "CARRIER_ID", base_time + timedelta(seconds=1), "ABC123", SignalType.STRING),
        LogEntry(device_id, "CONVEYOR_MOVE", base_time + timedelta(seconds=2), True, SignalType.BOOLEAN),
        LogEntry(device_id, "CARRIER_DETECTED", base_time + timedelta(seconds=3), False, SignalType.BOOLEAN),
        LogEntry(device_id, "CONVEYOR_MOVE", base_time + timedelta(seconds=4), False, SignalType.BOOLEAN),
    ]
    
    parsed_log = ParsedLog(
        entries=entries,
        signals={f"{device_id}::{e.signal_name}" for e in entries},
        devices={device_id},
        time_range=(base_time, base_time + timedelta(seconds=4))
    )
    
    # Create signal data with states
    signal_data_list = []
    signals_by_name = {}
    for entry in entries:
        if entry.signal_name not in signals_by_name:
            signals_by_name[entry.signal_name] = []
        signals_by_name[entry.signal_name].append(entry)
    
    for signal_name, signal_entries in signals_by_name.items():
        states = []
        for i, entry in enumerate(signal_entries):
            end_time = signal_entries[i + 1].timestamp if i + 1 < len(signal_entries) else base_time + timedelta(seconds=10)
            states.append(SignalState(
                start_time=entry.timestamp,
                end_time=end_time,
                value=entry.value,
                start_offset=(entry.timestamp - base_time).total_seconds(),
                end_offset=(end_time - base_time).total_seconds()
            ))
        
        signal_data_list.append(SignalData(
            name=signal_name,
            device_id=device_id,
            key=f"{device_id}::{signal_name}",
            signal_type=signal_entries[0].signal_type,
            states=states,
            _entries_count=len(signal_entries)
        ))
    
    return parsed_log, signal_data_list


class TestIntervalViewOpensAsTab:
    """Test that signal interval view opens as tab, not window."""
    
    def test_interval_view_opens_as_tab(self, qtbot, parsed_log_with_signal_data):
        """End-to-end test: opening interval view as tab."""
        parsed_log, signal_data = parsed_log_with_signal_data
        
        # Find a signal with transitions
        signal_with_transitions = None
        for sig_data in signal_data:
            if len(sig_data.states) >= 2 and sig_data.signal_type == SignalType.BOOLEAN:
                signal_with_transitions = sig_data
                break
        
        assert signal_with_transitions is not None
        
        # Create split pane manager
        manager = SplitPaneManager()
        qtbot.addWidget(manager)
        
        # Create interval view
        interval_view = SignalIntervalDialog(signal_with_transitions)
        
        # Add to split pane manager as tab
        result = manager.add_view(interval_view, f"Intervals: {signal_with_transitions.display_label}")
        
        # Should successfully add as tab
        assert result is True
        
        # Should be in the tab system
        assert len(manager.get_all_views()) == 1
        assert manager.get_active_view() == interval_view
        
        # Should be a widget, not a standalone window
        assert interval_view.isWindow() is False
    
    def test_multiple_interval_views_as_tabs(self, qtbot, parsed_log_with_signal_data):
        """Test opening multiple interval views as separate tabs."""
        parsed_log, signal_data = parsed_log_with_signal_data
        
        # Get boolean signals with transitions
        boolean_signals = [
            sig for sig in signal_data
            if sig.signal_type == SignalType.BOOLEAN and len(sig.states) >= 2
        ]
        
        assert len(boolean_signals) >= 2
        
        # Create split pane manager
        manager = SplitPaneManager()
        qtbot.addWidget(manager)
        
        # Add multiple interval views
        for sig_data in boolean_signals[:2]:
            interval_view = SignalIntervalDialog(sig_data)
            manager.add_view(interval_view, f"Intervals: {sig_data.display_label}")
        
        # Should have multiple tabs
        assert len(manager.get_all_views()) == 2
        
        # All should be widgets in the tab system
        for view in manager.get_all_views():
            assert isinstance(view, SignalIntervalDialog)
            assert view.isWindow() is False


class TestProcessingTimeShownAfterParse:
    """Test that processing time appears in stats after parsing."""
    
    def test_processing_time_shown_after_parse(self, qtbot, sample_log_file):
        """Verify processing time displays after parsing a real file."""
        # Create stats widget
        stats_widget = StatsWidget()
        qtbot.addWidget(stats_widget)
        
        # Parse the file
        parser = PLCDebugParser()
        result = parser.parse(sample_log_file, num_workers=1)
        
        # Should have processing time
        assert result.processing_time is not None
        assert result.processing_time > 0
        
        # Update stats widget
        stats_widget.update_stats(result)
        
        # Processing time should be displayed
        time_text = stats_widget.processing_time_label.text()
        assert "Processing Time:" in time_text
        assert time_text != "Processing Time: -"
        
        # Should show either ms or s format
        assert "ms" in time_text or "s" in time_text
    
    def test_processing_time_format(self, qtbot):
        """Test that processing time formatting is correct."""
        from plc_visualizer.models import ParseResult
        
        stats_widget = StatsWidget()
        qtbot.addWidget(stats_widget)
        
        parsed_log = ParsedLog(entries=[], signals=set(), devices=set())
        
        # Test milliseconds format
        result_ms = ParseResult(data=parsed_log, processing_time=0.123)
        stats_widget.update_stats(result_ms)
        assert "123ms" in stats_widget.processing_time_label.text()
        
        # Test seconds format
        result_s = ParseResult(data=parsed_log, processing_time=1.234)
        stats_widget.update_stats(result_s)
        assert "1.23s" in stats_widget.processing_time_label.text() or "1.24s" in stats_widget.processing_time_label.text()


class TestLogTableFilterCollapsibleUI:
    """Test that log table filter is collapsible via splitter."""
    
    def test_log_table_filter_collapsible_ui(self, qtbot, parsed_log_with_signal_data):
        """Interactive test of splitter in log table."""
        session_manager = SessionManager()
        parsed_log, signal_data = parsed_log_with_signal_data
        
        # Create log table view
        log_table = LogTableView(session_manager)
        qtbot.addWidget(log_table)
        log_table.show()
        qtbot.waitExposed(log_table)
        
        # Load data
        log_table.set_data(parsed_log, signal_data)
        
        # Find splitter
        splitters = log_table.findChildren(QSplitter)
        horizontal_splitter = None
        for splitter in splitters:
            if splitter.orientation() == Qt.Orientation.Horizontal:
                horizontal_splitter = splitter
                break
        
        assert horizontal_splitter is not None
        
        # Test collapsing filter panel
        original_sizes = horizontal_splitter.sizes()
        
        # Collapse first panel (filter)
        horizontal_splitter.setSizes([0, sum(original_sizes)])
        collapsed_sizes = horizontal_splitter.sizes()
        
        # Filter should be collapsed
        assert collapsed_sizes[0] < 50
        
        # Restore filter panel
        horizontal_splitter.setSizes([320, 900])
        restored_sizes = horizontal_splitter.sizes()
        
        # Filter should be visible again
        if restored_sizes[0] > 0:
            assert restored_sizes[0] > 100


class TestAllFixesWorkTogether:
    """Comprehensive test of all 4 fixes working together."""
    
    def test_all_fixes_integration(self, qtbot, sample_log_file, parsed_log_with_signal_data):
        """Test all 4 fixes working in a realistic scenario."""
        # Setup
        session_manager = SessionManager()
        parsed_log, signal_data = parsed_log_with_signal_data
        
        # 1. Parse file and verify processing time is tracked
        parser = PLCDebugParser()
        parse_result = parser.parse(sample_log_file, num_workers=1)
        assert parse_result.processing_time is not None
        assert parse_result.processing_time > 0
        
        # 2. Display stats with processing time
        stats_widget = StatsWidget()
        qtbot.addWidget(stats_widget)
        stats_widget.update_stats(parse_result)
        assert "Processing Time:" in stats_widget.processing_time_label.text()
        assert stats_widget.processing_time_label.text() != "Processing Time: -"
        
        # 3. Create log table with collapsible filter
        log_table = LogTableView(session_manager)
        qtbot.addWidget(log_table)
        log_table.set_data(parsed_log, signal_data)
        
        # Verify splitter exists
        splitters = log_table.findChildren(QSplitter)
        has_horizontal_splitter = any(
            s.orientation() == Qt.Orientation.Horizontal for s in splitters
        )
        assert has_horizontal_splitter
        
        # 4. Create interval view and add as tab
        boolean_signal = next(
            (sig for sig in signal_data 
             if sig.signal_type == SignalType.BOOLEAN and len(sig.states) >= 2),
            None
        )
        
        if boolean_signal:
            manager = SplitPaneManager()
            qtbot.addWidget(manager)
            
            interval_view = SignalIntervalDialog(boolean_signal)
            result = manager.add_view(interval_view, "Test Interval")
            
            assert result is True
            assert interval_view.view_type == "signal_interval"
            assert not interval_view.isWindow()
        
        # 5. Verify YAML config loading (if map viewer available)
        try:
            from tools.map_viewer import config as map_config
            
            # Should have loaded config
            assert isinstance(map_config.ATTRIBUTES_TO_EXTRACT, list)
            assert isinstance(map_config.TYPE_COLOR_MAPPING, dict)
            assert "default" in map_config.TYPE_COLOR_MAPPING
        except ImportError:
            # Map viewer not available, skip this part
            pass


class TestFixesWithEmptyData:
    """Test fixes handle edge cases gracefully."""
    
    def test_interval_view_with_minimal_data(self, qtbot):
        """Test interval view with minimal signal data."""
        base_time = datetime(2024, 1, 1, 10, 0, 0)
        
        # Create signal with only 2 states
        states = [
            SignalState(
                start_time=base_time,
                end_time=base_time + timedelta(seconds=1),
                value=True,
                start_offset=0.0,
                end_offset=1.0
            ),
            SignalState(
                start_time=base_time + timedelta(seconds=1),
                end_time=base_time + timedelta(seconds=2),
                value=False,
                start_offset=1.0,
                end_offset=2.0
            ),
        ]
        
        signal_data = SignalData(
            name="TEST",
            device_id="DEVICE",
            key="DEVICE::TEST",
            signal_type=SignalType.BOOLEAN,
            states=states,
            _entries_count=2
        )
        
        # Should be able to create view
        interval_view = SignalIntervalDialog(signal_data)
        qtbot.addWidget(interval_view)
        
        assert interval_view.view_type == "signal_interval"
    
    def test_log_table_splitter_with_empty_data(self, qtbot):
        """Test log table splitter with no data loaded."""
        session_manager = SessionManager()
        
        log_table = LogTableView(session_manager)
        qtbot.addWidget(log_table)
        
        # Should still have splitter even without data
        splitters = log_table.findChildren(QSplitter)
        has_horizontal_splitter = any(
            s.orientation() == Qt.Orientation.Horizontal for s in splitters
        )
        
        assert has_horizontal_splitter
    
    def test_stats_widget_with_no_processing_time(self, qtbot):
        """Test stats widget when processing_time is None."""
        from plc_visualizer.models import ParseResult
        
        stats_widget = StatsWidget()
        qtbot.addWidget(stats_widget)
        
        parsed_log = ParsedLog(entries=[], signals=set(), devices=set())
        result = ParseResult(data=parsed_log, processing_time=None)
        
        stats_widget.update_stats(result)
        
        # Should show "-"
        assert "Processing Time: -" in stats_widget.processing_time_label.text()

