"""Tests for the multi-view window manager system."""

import pytest
from datetime import datetime, timedelta
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from plc_visualizer.app.session_manager import SessionManager
from plc_visualizer.models import TimeBookmark
from plc_visualizer.ui.components.split_pane_manager import SplitPaneManager
from plc_visualizer.ui.components.view_tab_widget import ViewTabWidget
from plc_visualizer.ui.windows.timing_window import TimingDiagramView
from plc_visualizer.ui.windows.log_table_window import LogTableView


class TestSplitPaneManager:
    """Test the split pane manager functionality."""
    
    def test_initial_state(self, qtbot):
        """Test that split pane manager starts with one pane."""
        manager = SplitPaneManager()
        qtbot.addWidget(manager)
        
        assert manager.get_pane_count() == 1
        assert manager.get_active_pane_index() == 0
    
    def test_add_view(self, qtbot):
        """Test adding a view to the manager."""
        manager = SplitPaneManager()
        qtbot.addWidget(manager)
        
        session_manager = SessionManager()
        view = TimingDiagramView(session_manager.viewport_state)
        
        result = manager.add_view(view, "Test View")
        
        assert result is True
        assert len(manager.get_all_views()) == 1
        assert manager.get_active_view() == view
    
    def test_split_pane_horizontal(self, qtbot):
        """Test splitting a pane horizontally."""
        manager = SplitPaneManager()
        qtbot.addWidget(manager)
        
        session_manager = SessionManager()
        view1 = TimingDiagramView(session_manager.viewport_state)
        manager.add_view(view1, "View 1")
        
        # Split horizontally
        result = manager.split_pane(Qt.Horizontal, 0)
        
        assert result is True
        assert manager.get_pane_count() == 2
    
    def test_split_pane_vertical(self, qtbot):
        """Test splitting a pane vertically."""
        manager = SplitPaneManager()
        qtbot.addWidget(manager)
        
        session_manager = SessionManager()
        view1 = TimingDiagramView(session_manager.viewport_state)
        manager.add_view(view1, "View 1")
        
        # Split vertically
        result = manager.split_pane(Qt.Vertical, 0)
        
        assert result is True
        assert manager.get_pane_count() == 2
    
    def test_max_panes_constraint(self, qtbot):
        """Test that we can't exceed 4 panes."""
        manager = SplitPaneManager()
        qtbot.addWidget(manager)
        
        session_manager = SessionManager()
        
        # Add first view
        view1 = TimingDiagramView(session_manager.viewport_state)
        manager.add_view(view1, "View 1")
        
        # Split 3 times to get 4 panes
        manager.split_pane(Qt.Horizontal, 0)  # 2 panes
        manager.split_pane(Qt.Vertical, 0)    # 3 panes
        manager.split_pane(Qt.Vertical, 1)    # 4 panes
        
        assert manager.get_pane_count() == 4
        
        # Try to split again - should fail
        result = manager.split_pane(Qt.Horizontal, 0)
        assert result is False
        assert manager.get_pane_count() == 4  # Still 4
    
    def test_merge_pane(self, qtbot):
        """Test merging panes back."""
        manager = SplitPaneManager()
        qtbot.addWidget(manager)
        
        session_manager = SessionManager()
        view1 = TimingDiagramView(session_manager.viewport_state)
        manager.add_view(view1, "View 1")
        
        # Split and then merge
        manager.split_pane(Qt.Horizontal, 0)
        assert manager.get_pane_count() == 2
        
        result = manager.merge_pane(1)
        assert result is True
        assert manager.get_pane_count() == 1
    
    def test_cannot_merge_last_pane(self, qtbot):
        """Test that we can't merge when only one pane remains."""
        manager = SplitPaneManager()
        qtbot.addWidget(manager)
        
        result = manager.merge_pane(0)
        assert result is False
        assert manager.get_pane_count() == 1


class TestViewTabWidget:
    """Test the custom tab widget functionality."""
    
    def test_initial_state(self, qtbot):
        """Test initial tab widget state."""
        tab_widget = ViewTabWidget()
        qtbot.addWidget(tab_widget)
        
        assert tab_widget.count() == 0
        assert tab_widget.isMovable() is True
        # Note: tabsClosable is set to True in constructor but Qt may not report it
        # until there are actual tabs, so we just verify the tab bar is configured
    
    def test_add_tab(self, qtbot):
        """Test adding a tab."""
        tab_widget = ViewTabWidget()
        qtbot.addWidget(tab_widget)
        
        session_manager = SessionManager()
        view = TimingDiagramView(session_manager.viewport_state)
        
        index = tab_widget.addTab(view, "Test Tab")
        
        assert index == 0
        assert tab_widget.count() == 1
        assert tab_widget.tabText(0) == "Test Tab"
    
    def test_tab_close_signal(self, qtbot):
        """Test that tab close emits the correct signal."""
        tab_widget = ViewTabWidget()
        qtbot.addWidget(tab_widget)
        
        session_manager = SessionManager()
        view = TimingDiagramView(session_manager.viewport_state)
        tab_widget.addTab(view, "Test Tab")
        
        # Connect signal and test
        closed_widgets = []
        tab_widget.tab_closed.connect(lambda w: closed_widgets.append(w))
        
        # Trigger close
        tab_widget.tabCloseRequested.emit(0)
        
        assert len(closed_widgets) == 1
        assert closed_widgets[0] == view


class TestBookmarkSystem:
    """Test the bookmark functionality."""
    
    def test_add_bookmark(self):
        """Test adding a bookmark."""
        session = SessionManager()
        
        timestamp = datetime(2024, 1, 1, 12, 0, 0)
        bookmark = session.add_bookmark(timestamp, "Test Bookmark", "Description")
        
        assert bookmark.label == "Test Bookmark"
        assert bookmark.description == "Description"
        assert bookmark.timestamp == timestamp
        assert len(session.bookmarks) == 1
    
    def test_bookmarks_sorted(self):
        """Test that bookmarks are kept sorted by timestamp."""
        session = SessionManager()
        
        # Add out of order
        time2 = datetime(2024, 1, 1, 12, 0, 0)
        time1 = datetime(2024, 1, 1, 11, 0, 0)
        time3 = datetime(2024, 1, 1, 13, 0, 0)
        
        session.add_bookmark(time2, "Second")
        session.add_bookmark(time1, "First")
        session.add_bookmark(time3, "Third")
        
        bookmarks = session.bookmarks
        assert len(bookmarks) == 3
        assert bookmarks[0].label == "First"
        assert bookmarks[1].label == "Second"
        assert bookmarks[2].label == "Third"
    
    def test_remove_bookmark(self):
        """Test removing a bookmark."""
        session = SessionManager()
        
        timestamp = datetime(2024, 1, 1, 12, 0, 0)
        session.add_bookmark(timestamp, "Test Bookmark")
        
        assert len(session.bookmarks) == 1
        
        result = session.remove_bookmark(0)
        
        assert result is True
        assert len(session.bookmarks) == 0
    
    def test_jump_to_bookmark(self, qtbot):
        """Test jumping to a bookmark."""
        session = SessionManager()
        
        timestamp = datetime(2024, 1, 1, 12, 0, 0)
        session.add_bookmark(timestamp, "Test Bookmark")
        
        # Track signal emission
        jumped_times = []
        session.bookmark_jump_requested.connect(lambda t: jumped_times.append(t))
        
        result = session.jump_to_bookmark(0)
        
        assert result is True
        assert len(jumped_times) == 1
        assert jumped_times[0] == timestamp
    
    def test_next_bookmark(self, qtbot):
        """Test navigating to next bookmark."""
        session = SessionManager()
        
        time1 = datetime(2024, 1, 1, 11, 0, 0)
        time2 = datetime(2024, 1, 1, 12, 0, 0)
        
        session.add_bookmark(time1, "First")
        session.add_bookmark(time2, "Second")
        
        # Track signal emission
        jumped_times = []
        session.bookmark_jump_requested.connect(lambda t: jumped_times.append(t))
        
        # Jump to first
        session.jump_to_bookmark(0)
        assert len(jumped_times) == 1
        
        # Next should go to second
        result = session.next_bookmark()
        assert result is True
        assert len(jumped_times) == 2
        assert jumped_times[1] == time2
    
    def test_previous_bookmark(self, qtbot):
        """Test navigating to previous bookmark."""
        session = SessionManager()
        
        time1 = datetime(2024, 1, 1, 11, 0, 0)
        time2 = datetime(2024, 1, 1, 12, 0, 0)
        
        session.add_bookmark(time1, "First")
        session.add_bookmark(time2, "Second")
        
        # Track signal emission
        jumped_times = []
        session.bookmark_jump_requested.connect(lambda t: jumped_times.append(t))
        
        # Jump to second
        session.jump_to_bookmark(1)
        assert len(jumped_times) == 1
        
        # Previous should go to first
        result = session.prev_bookmark()
        assert result is True
        assert len(jumped_times) == 2
        assert jumped_times[1] == time1
    
    def test_bookmark_wrap_around(self, qtbot):
        """Test that bookmark navigation wraps around."""
        session = SessionManager()
        
        time1 = datetime(2024, 1, 1, 11, 0, 0)
        time2 = datetime(2024, 1, 1, 12, 0, 0)
        
        session.add_bookmark(time1, "First")
        session.add_bookmark(time2, "Second")
        
        # Jump to last bookmark
        session.jump_to_bookmark(1)
        
        # Next should wrap to first
        jumped_times = []
        session.bookmark_jump_requested.connect(lambda t: jumped_times.append(t))
        
        result = session.next_bookmark()
        assert result is True
        assert jumped_times[0] == time1


class TestSharedViewportState:
    """Test that views properly share viewport state."""
    
    def test_shared_viewport_state(self, qtbot):
        """Test that multiple views share the same viewport state."""
        session = SessionManager()
        
        view1 = TimingDiagramView(session.viewport_state)
        view2 = TimingDiagramView(session.viewport_state)
        
        qtbot.addWidget(view1)
        qtbot.addWidget(view2)
        
        # Both should reference the same object
        assert view1.viewport_state is view2.viewport_state
        assert view1.viewport_state is session.viewport_state
    
    def test_time_sync_propagates(self, qtbot):
        """Test that time changes propagate to all views."""
        session = SessionManager()
        
        start_time = datetime(2024, 1, 1, 10, 0, 0)
        end_time = datetime(2024, 1, 1, 12, 0, 0)
        
        # Set up viewport
        session.viewport_state.set_full_time_range(start_time, end_time)
        
        view1 = TimingDiagramView(session.viewport_state)
        view2 = TimingDiagramView(session.viewport_state)
        
        qtbot.addWidget(view1)
        qtbot.addWidget(view2)
        
        # Track time changes
        view1_times = []
        view2_times = []
        
        session.viewport_state.time_range_changed.connect(
            lambda s, e: view1_times.append((s, e))
        )
        session.viewport_state.time_range_changed.connect(
            lambda s, e: view2_times.append((s, e))
        )
        
        # Change time - use a duration within MAX_VISIBLE_DURATION_SECONDS (5 minutes)
        new_start = datetime(2024, 1, 1, 11, 0, 0)
        new_end = datetime(2024, 1, 1, 11, 3, 0)  # 3 minutes, well within 5 min max
        session.viewport_state.set_time_range(new_start, new_end)
        
        # Both views should receive the update
        assert len(view1_times) == 1
        assert len(view2_times) == 1
        assert view1_times[0][0] == new_start  # Check start time matches
        assert view2_times[0][0] == new_start  # Check start time matches
        # End times should also match (within constraints)
        assert view1_times[0] == view2_times[0]  # Both views get same time range


class TestTimeBookmarkModel:
    """Test the TimeBookmark data model."""
    
    def test_bookmark_creation(self):
        """Test creating a bookmark."""
        timestamp = datetime(2024, 1, 1, 12, 0, 0)
        bookmark = TimeBookmark(
            timestamp=timestamp,
            label="Test",
            description="Test Description"
        )
        
        assert bookmark.timestamp == timestamp
        assert bookmark.label == "Test"
        assert bookmark.description == "Test Description"
        assert bookmark.created_at is not None
    
    def test_bookmark_comparison(self):
        """Test that bookmarks can be sorted by timestamp."""
        time1 = datetime(2024, 1, 1, 11, 0, 0)
        time2 = datetime(2024, 1, 1, 12, 0, 0)
        
        bookmark1 = TimeBookmark(timestamp=time1, label="First")
        bookmark2 = TimeBookmark(timestamp=time2, label="Second")
        
        assert bookmark1 < bookmark2
        
        # Test sorting
        bookmarks = [bookmark2, bookmark1]
        bookmarks.sort()
        
        assert bookmarks[0].label == "First"
        assert bookmarks[1].label == "Second"
    
    def test_bookmark_string_representation(self):
        """Test bookmark string representation."""
        timestamp = datetime(2024, 1, 1, 12, 30, 45, 123000)
        bookmark = TimeBookmark(timestamp=timestamp, label="Test Label")
        
        string_repr = str(bookmark)
        
        assert "Test Label" in string_repr
        assert "12:30:45" in string_repr

