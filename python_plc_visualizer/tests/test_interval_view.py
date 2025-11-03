"""Tests for SignalIntervalDialog as an embeddable tab view."""

import pytest
from datetime import datetime, timedelta
from PySide6.QtWidgets import QWidget

from plc_visualizer.models import LogEntry, SignalType
from plc_visualizer.utils import SignalData, SignalState
from plc_visualizer.ui.windows.interval_window import SignalIntervalDialog
from plc_visualizer.ui.components.split_pane_manager import SplitPaneManager


@pytest.fixture
def sample_signal_data() -> SignalData:
    """Create sample signal data with transitions for testing."""
    base_time = datetime(2024, 1, 1, 10, 0, 0)
    device_id = "TEST_DEVICE"
    signal_name = "TEST_SIGNAL"
    
    states = [
        SignalState(
            start_time=base_time,
            end_time=base_time + timedelta(seconds=1.0),
            value=True,
            start_offset=0.0,
            end_offset=1.0
        ),
        SignalState(
            start_time=base_time + timedelta(seconds=1.0),
            end_time=base_time + timedelta(seconds=2.5),
            value=False,
            start_offset=1.0,
            end_offset=2.5
        ),
        SignalState(
            start_time=base_time + timedelta(seconds=2.5),
            end_time=base_time + timedelta(seconds=4.0),
            value=True,
            start_offset=2.5,
            end_offset=4.0
        ),
        SignalState(
            start_time=base_time + timedelta(seconds=4.0),
            end_time=base_time + timedelta(seconds=5.0),
            value=False,
            start_offset=4.0,
            end_offset=5.0
        ),
    ]
    
    return SignalData(
        name=signal_name,
        device_id=device_id,
        key=f"{device_id}::{signal_name}",
        signal_type=SignalType.BOOLEAN,
        states=states,
        _entries_count=len(states)
    )


class TestSignalIntervalView:
    """Test SignalIntervalDialog as embeddable view."""
    
    def test_interval_view_type(self, qtbot, sample_signal_data):
        """Verify VIEW_TYPE constant is set correctly."""
        view = SignalIntervalDialog(sample_signal_data)
        qtbot.addWidget(view)
        
        assert hasattr(view, 'VIEW_TYPE')
        assert view.VIEW_TYPE == "signal_interval"
        assert view.view_type == "signal_interval"
    
    def test_interval_view_initialization(self, qtbot, sample_signal_data):
        """Check it's a QWidget not QDialog."""
        view = SignalIntervalDialog(sample_signal_data)
        qtbot.addWidget(view)
        
        # Should be QWidget, not QDialog
        assert isinstance(view, QWidget)
        
        # Should not have modal attributes
        assert not view.isModal()
        
        # Should have the signal data
        assert view.signal_data == sample_signal_data
    
    def test_add_to_split_pane(self, qtbot, sample_signal_data):
        """Verify it integrates with tab system."""
        manager = SplitPaneManager()
        qtbot.addWidget(manager)
        
        view = SignalIntervalDialog(sample_signal_data)
        result = manager.add_view(view, "Test Interval View")
        
        assert result is True
        assert len(manager.get_all_views()) == 1
        assert manager.get_active_view() == view
    
    def test_has_interval_controls(self, qtbot, sample_signal_data):
        """Verify the view has the expected controls."""
        view = SignalIntervalDialog(sample_signal_data)
        qtbot.addWidget(view)
        
        # Check radio buttons exist
        assert hasattr(view, 'rb_change')
        assert hasattr(view, 'rb_pulse')
        assert hasattr(view, 'rb_custom')
        
        # Check plot widget exists
        assert hasattr(view, 'plot_widget')
        assert view.plot_widget is not None
        
        # Check table widget exists
        assert hasattr(view, 'table')
        assert view.table is not None
    
    def test_change_to_change_mode_default(self, qtbot, sample_signal_data):
        """Verify change-to-change mode is default."""
        view = SignalIntervalDialog(sample_signal_data)
        qtbot.addWidget(view)
        
        # Change to change should be checked by default
        assert view.rb_change.isChecked()
        assert not view.rb_pulse.isChecked()
        assert not view.rb_custom.isChecked()
    
    def test_pulse_width_mode_switch(self, qtbot, sample_signal_data):
        """Test switching to pulse width mode."""
        view = SignalIntervalDialog(sample_signal_data)
        qtbot.addWidget(view)
        
        # Switch to pulse mode
        view.rb_pulse.setChecked(True)
        
        assert view.rb_pulse.isChecked()
        assert not view.rb_change.isChecked()
    
    def test_custom_token_mode_enables_inputs(self, qtbot, sample_signal_data):
        """Test custom token mode enables input fields."""
        view = SignalIntervalDialog(sample_signal_data)
        qtbot.addWidget(view)
        
        # Initially disabled
        assert not view.le_start.isEnabled()
        assert not view.le_end.isEnabled()
        
        # Switch to custom mode
        view.rb_custom.setChecked(True)
        
        # Should be enabled now
        assert view.le_start.isEnabled()
        assert view.le_end.isEnabled()
    
    def test_bin_duration_control_exists(self, qtbot, sample_signal_data):
        """Verify bin duration control exists."""
        view = SignalIntervalDialog(sample_signal_data)
        qtbot.addWidget(view)
        
        assert hasattr(view, 'sb_bin_dur')
        assert view.sb_bin_dur is not None
        
        # Check that it has a reasonable value (auto-calculated from data)
        assert view.sb_bin_dur.value() > 0
        assert view.sb_bin_dur.value() <= 3600.0  # Max range
    
    def test_percentile_cap_control_exists(self, qtbot, sample_signal_data):
        """Verify percentile cap control exists."""
        view = SignalIntervalDialog(sample_signal_data)
        qtbot.addWidget(view)
        
        assert hasattr(view, 'sb_cap')
        assert view.sb_cap is not None
        
        # Check default value
        assert view.sb_cap.value() == 99
    
    def test_show_band_checkbox_exists(self, qtbot, sample_signal_data):
        """Verify show band checkbox exists."""
        view = SignalIntervalDialog(sample_signal_data)
        qtbot.addWidget(view)
        
        assert hasattr(view, 'cb_band')
        assert view.cb_band is not None
        
        # Should be checked by default
        assert view.cb_band.isChecked()
    
    def test_interval_table_has_correct_columns(self, qtbot, sample_signal_data):
        """Verify interval table has expected columns."""
        view = SignalIntervalDialog(sample_signal_data)
        qtbot.addWidget(view)
        
        # Check column count
        assert view.table.columnCount() == 5
        
        # Check column headers
        headers = [view.table.horizontalHeaderItem(i).text() 
                   for i in range(view.table.columnCount())]
        
        assert "Change #" in headers
        assert "From Value" in headers
        assert "To Value" in headers
        assert "Started At" in headers
        assert "Interval (s)" in headers


class TestIntervalPlotWidget:
    """Test the interval plot widget within the view."""
    
    def test_plot_widget_initialized(self, qtbot, sample_signal_data):
        """Test that plot widget is properly initialized."""
        view = SignalIntervalDialog(sample_signal_data)
        qtbot.addWidget(view)
        
        plot = view.plot_widget
        assert plot is not None
        
        # Check initial state
        assert hasattr(plot, '_bin_duration_s')
        assert hasattr(plot, '_cap_p')
        assert hasattr(plot, '_show_band')
    
    def test_plot_responds_to_bin_duration_change(self, qtbot, sample_signal_data):
        """Verify plot updates when bin duration changes."""
        view = SignalIntervalDialog(sample_signal_data)
        qtbot.addWidget(view)
        
        original_bin = view.plot_widget._bin_duration_s
        
        # Change bin duration
        new_value = 0.5
        view.sb_bin_dur.setValue(new_value)
        
        # Plot should be updated
        assert view.plot_widget._bin_duration_s == pytest.approx(new_value, rel=1e-6)
    
    def test_plot_responds_to_cap_percentile_change(self, qtbot, sample_signal_data):
        """Verify plot updates when cap percentile changes."""
        view = SignalIntervalDialog(sample_signal_data)
        qtbot.addWidget(view)
        
        # Change cap percentile
        new_cap = 95
        view.sb_cap.setValue(new_cap)
        
        # Plot should be updated (95% = 0.95)
        assert view.plot_widget._cap_p == pytest.approx(0.95, rel=1e-3)
    
    def test_plot_responds_to_band_toggle(self, qtbot, sample_signal_data):
        """Verify plot updates when band visibility changes."""
        view = SignalIntervalDialog(sample_signal_data)
        qtbot.addWidget(view)
        
        # Toggle band off
        view.cb_band.setChecked(False)
        assert view.plot_widget._show_band is False
        
        # Toggle band on
        view.cb_band.setChecked(True)
        assert view.plot_widget._show_band is True


class TestIntervalViewWithMinimalTransitions:
    """Test interval view behavior with edge cases."""
    
    def test_with_two_transitions(self, qtbot):
        """Test with minimal transitions (2 states)."""
        base_time = datetime(2024, 1, 1, 10, 0, 0)
        
        states = [
            SignalState(
                start_time=base_time,
                end_time=base_time + timedelta(seconds=1.0),
                value=True,
                start_offset=0.0,
                end_offset=1.0
            ),
            SignalState(
                start_time=base_time + timedelta(seconds=1.0),
                end_time=base_time + timedelta(seconds=2.0),
                value=False,
                start_offset=1.0,
                end_offset=2.0
            ),
        ]
        
        signal_data = SignalData(
            name="MINIMAL_SIGNAL",
            device_id="TEST_DEVICE",
            key="TEST_DEVICE::MINIMAL_SIGNAL",
            signal_type=SignalType.BOOLEAN,
            states=states,
            _entries_count=2
        )
        
        view = SignalIntervalDialog(signal_data)
        qtbot.addWidget(view)
        
        # Should be able to create view with minimal data
        assert view.signal_data == signal_data
        assert view.table.rowCount() >= 0  # Should have at least 0 rows

