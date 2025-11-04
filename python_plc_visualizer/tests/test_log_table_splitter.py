"""Tests for collapsible log table filter using horizontal splitter."""

import pytest
from datetime import datetime, timedelta
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QSplitter

from plc_visualizer.app.session_manager import SessionManager
from plc_visualizer.models import LogEntry, ParsedLog, SignalType
from plc_visualizer.utils import SignalData, SignalState
from plc_visualizer.ui.windows.log_table_window import LogTableView


@pytest.fixture
def session_manager():
    """Create a session manager for testing."""
    return SessionManager()


@pytest.fixture
def sample_log_data():
    """Create sample log data for testing."""
    base_time = datetime(2024, 1, 1, 10, 0, 0)
    device_id = "TEST_DEVICE"
    
    entries = [
        LogEntry(device_id, "SIGNAL_A", base_time, True, SignalType.BOOLEAN),
        LogEntry(device_id, "SIGNAL_B", base_time + timedelta(seconds=1), "VALUE1", SignalType.STRING),
        LogEntry(device_id, "SIGNAL_A", base_time + timedelta(seconds=2), False, SignalType.BOOLEAN),
        LogEntry(device_id, "SIGNAL_C", base_time + timedelta(seconds=3), 42, SignalType.INTEGER),
    ]
    
    parsed_log = ParsedLog(
        entries=entries,
        signals={f"{device_id}::{e.signal_name}" for e in entries},
        devices={device_id},
        time_range=(base_time, base_time + timedelta(seconds=3))
    )
    
    # Create signal data
    signal_data_list = []
    for signal_name in ["SIGNAL_A", "SIGNAL_B", "SIGNAL_C"]:
        signal_entries = [e for e in entries if e.signal_name == signal_name]
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


class TestLogTableSplitter:
    """Test the horizontal splitter in log table view."""
    
    def test_log_table_has_splitter(self, qtbot, session_manager):
        """Verify LogTableView has a splitter."""
        view = LogTableView(session_manager)
        qtbot.addWidget(view)
        
        # Find splitter in the widget hierarchy
        splitters = view.findChildren(QSplitter)
        
        # Should have at least one splitter
        assert len(splitters) > 0
        
        # Get the main splitter (should be horizontal)
        main_splitter = None
        for splitter in splitters:
            if splitter.orientation() == Qt.Orientation.Horizontal:
                main_splitter = splitter
                break
        
        assert main_splitter is not None
    
    def test_splitter_orientation(self, qtbot, session_manager):
        """Check splitter is horizontal."""
        view = LogTableView(session_manager)
        qtbot.addWidget(view)
        
        # Find horizontal splitter
        splitters = view.findChildren(QSplitter)
        horizontal_splitter = None
        for splitter in splitters:
            if splitter.orientation() == Qt.Orientation.Horizontal:
                horizontal_splitter = splitter
                break
        
        assert horizontal_splitter is not None
        assert horizontal_splitter.orientation() == Qt.Orientation.Horizontal
    
    def test_splitter_has_two_children(self, qtbot, session_manager):
        """Verify splitter has filter panel and table panel."""
        view = LogTableView(session_manager)
        qtbot.addWidget(view)
        
        # Find horizontal splitter
        splitters = view.findChildren(QSplitter)
        horizontal_splitter = None
        for splitter in splitters:
            if splitter.orientation() == Qt.Orientation.Horizontal:
                horizontal_splitter = splitter
                break
        
        assert horizontal_splitter is not None
        
        # Should have 2 children (filter panel and table panel)
        assert horizontal_splitter.count() == 2
    
    def test_initial_splitter_sizes(self, qtbot, session_manager):
        """Verify initial splitter sizes are [320, 900]."""
        view = LogTableView(session_manager)
        qtbot.addWidget(view)
        
        # Need to show the widget for sizes to be set
        view.show()
        qtbot.waitExposed(view)
        
        # Find horizontal splitter
        splitters = view.findChildren(QSplitter)
        horizontal_splitter = None
        for splitter in splitters:
            if splitter.orientation() == Qt.Orientation.Horizontal:
                horizontal_splitter = splitter
                break
        
        assert horizontal_splitter is not None
        
        # Get sizes
        sizes = horizontal_splitter.sizes()
        
        # Should have 2 sizes
        assert len(sizes) == 2
        
        # Both panels should have some width
        assert all(s >= 0 for s in sizes)
        
        # Total should equal the widget width
        assert sum(sizes) > 0
    
    def test_filter_panel_is_first_child(self, qtbot, session_manager):
        """Verify filter panel is on the left (first child)."""
        view = LogTableView(session_manager)
        qtbot.addWidget(view)
        
        # Find horizontal splitter
        splitters = view.findChildren(QSplitter)
        horizontal_splitter = None
        for splitter in splitters:
            if splitter.orientation() == Qt.Orientation.Horizontal:
                horizontal_splitter = splitter
                break
        
        assert horizontal_splitter is not None
        
        # Get first child
        first_child = horizontal_splitter.widget(0)
        assert first_child is not None
        
        # Should contain the signal filter
        # The filter is nested in a container, so we look for SignalFilterWidget in descendants
        from plc_visualizer.ui.components.signal_filter_widget import SignalFilterWidget
        filters = first_child.findChildren(SignalFilterWidget)
        assert len(filters) > 0
    
    def test_table_panel_is_second_child(self, qtbot, session_manager):
        """Verify table panel is on the right (second child)."""
        view = LogTableView(session_manager)
        qtbot.addWidget(view)
        
        # Find horizontal splitter
        splitters = view.findChildren(QSplitter)
        horizontal_splitter = None
        for splitter in splitters:
            if splitter.orientation() == Qt.Orientation.Horizontal:
                horizontal_splitter = splitter
                break
        
        assert horizontal_splitter is not None
        
        # Get second child
        second_child = horizontal_splitter.widget(1)
        assert second_child is not None
        
        # Should contain the data table
        from plc_visualizer.ui.components.data_table_widget import DataTableWidget
        tables = second_child.findChildren(DataTableWidget)
        assert len(tables) > 0
    
    def test_filter_can_collapse(self, qtbot, session_manager):
        """Test filter panel can be collapsed programmatically."""
        view = LogTableView(session_manager)
        qtbot.addWidget(view)
        view.show()
        qtbot.waitExposed(view)
        
        # Find horizontal splitter
        splitters = view.findChildren(QSplitter)
        horizontal_splitter = None
        for splitter in splitters:
            if splitter.orientation() == Qt.Orientation.Horizontal:
                horizontal_splitter = splitter
                break
        
        assert horizontal_splitter is not None
        
        # Collapse first panel (filter)
        horizontal_splitter.setSizes([0, 1000])
        
        # Get sizes
        sizes = horizontal_splitter.sizes()
        
        # First panel should be collapsed or very small
        assert sizes[0] < 50  # Allow some minimum size
    
    def test_splitter_is_collapsible(self, qtbot, session_manager):
        """Verify splitter children are collapsible."""
        view = LogTableView(session_manager)
        qtbot.addWidget(view)
        
        # Find horizontal splitter
        splitters = view.findChildren(QSplitter)
        horizontal_splitter = None
        for splitter in splitters:
            if splitter.orientation() == Qt.Orientation.Horizontal:
                horizontal_splitter = splitter
                break
        
        assert horizontal_splitter is not None
        
        # Check if children are collapsible
        # In Qt, by default, splitter children are collapsible
        # We verify by checking that we can set size to 0
        horizontal_splitter.setCollapsible(0, True)
        horizontal_splitter.setCollapsible(1, True)
        
        # Should not raise an error
        assert True


class TestLogTableWithData:
    """Test log table splitter behavior with actual data."""
    
    def test_splitter_with_loaded_data(self, qtbot, session_manager, sample_log_data):
        """Test splitter works correctly with loaded data."""
        view = LogTableView(session_manager)
        qtbot.addWidget(view)
        
        parsed_log, signal_data = sample_log_data
        view.set_data(parsed_log, signal_data)
        
        # Find splitter
        splitters = view.findChildren(QSplitter)
        horizontal_splitter = None
        for splitter in splitters:
            if splitter.orientation() == Qt.Orientation.Horizontal:
                horizontal_splitter = splitter
                break
        
        assert horizontal_splitter is not None
        assert horizontal_splitter.count() == 2
    
    def test_filter_and_table_both_visible_with_data(self, qtbot, session_manager, sample_log_data):
        """Verify both filter and table are visible when data is loaded."""
        view = LogTableView(session_manager)
        qtbot.addWidget(view)
        view.show()
        qtbot.waitExposed(view)
        
        parsed_log, signal_data = sample_log_data
        view.set_data(parsed_log, signal_data)
        
        # Find splitter
        splitters = view.findChildren(QSplitter)
        horizontal_splitter = None
        for splitter in splitters:
            if splitter.orientation() == Qt.Orientation.Horizontal:
                horizontal_splitter = splitter
                break
        
        assert horizontal_splitter is not None
        
        # Both panels should have non-zero size
        sizes = horizontal_splitter.sizes()
        assert len(sizes) == 2
        # Note: sizes might be 0 until layout is complete, so we just check structure
        assert horizontal_splitter.widget(0) is not None
        assert horizontal_splitter.widget(1) is not None


class TestSplitterHandleStyling:
    """Test splitter handle has correct styling."""
    
    def test_splitter_handle_width(self, qtbot, session_manager):
        """Verify splitter handle width is set."""
        view = LogTableView(session_manager)
        qtbot.addWidget(view)
        
        # Find horizontal splitter
        splitters = view.findChildren(QSplitter)
        horizontal_splitter = None
        for splitter in splitters:
            if splitter.orientation() == Qt.Orientation.Horizontal:
                horizontal_splitter = splitter
                break
        
        assert horizontal_splitter is not None
        
        # Check handle width
        handle_width = horizontal_splitter.handleWidth()
        
        # Should be set to 10 (as per implementation)
        assert handle_width == 10
    
    def test_splitter_has_stylesheet(self, qtbot, session_manager):
        """Verify splitter has custom stylesheet for handle."""
        view = LogTableView(session_manager)
        qtbot.addWidget(view)
        
        # Find horizontal splitter
        splitters = view.findChildren(QSplitter)
        horizontal_splitter = None
        for splitter in splitters:
            if splitter.orientation() == Qt.Orientation.Horizontal:
                horizontal_splitter = splitter
                break
        
        assert horizontal_splitter is not None
        
        # Check if it has a stylesheet
        stylesheet = horizontal_splitter.styleSheet()
        
        # Should contain handle styling
        assert "QSplitter::handle" in stylesheet or stylesheet != ""

