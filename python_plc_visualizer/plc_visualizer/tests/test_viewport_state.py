"""Unit tests for viewport state management."""

import pytest
from datetime import datetime, timedelta
from plc_visualizer.utils.viewport_state import ViewportState


class TestViewportState:
    """Test cases for ViewportState class."""

    @pytest.fixture
    def viewport_state(self):
        """Create a ViewportState instance for testing."""
        return ViewportState()

    @pytest.fixture
    def sample_time_range(self):
        """Create a sample time range."""
        start = datetime(2024, 1, 1, 10, 0, 0)
        end = datetime(2024, 1, 1, 11, 0, 0)  # 1 hour duration
        return start, end

    def test_initial_state(self, viewport_state):
        """Test initial state of viewport."""
        assert viewport_state.full_time_range is None
        assert viewport_state.visible_time_range is None
        assert viewport_state.zoom_level == 1.0

    def test_set_full_time_range(self, viewport_state, sample_time_range):
        """Test setting full time range."""
        start, end = sample_time_range
        viewport_state.set_full_time_range(start, end)

        assert viewport_state.full_time_range == (start, end)
        assert viewport_state.visible_time_range == (start, end)
        assert viewport_state.zoom_level == 1.0

    def test_set_full_time_range_invalid(self, viewport_state, sample_time_range):
        """Test setting invalid time range (start >= end)."""
        start, end = sample_time_range
        with pytest.raises(ValueError):
            viewport_state.set_full_time_range(end, start)

    def test_zoom_in(self, viewport_state, sample_time_range):
        """Test zoom in functionality."""
        start, end = sample_time_range
        viewport_state.set_full_time_range(start, end)

        initial_zoom = viewport_state.zoom_level
        viewport_state.zoom_in(factor=2.0)

        assert viewport_state.zoom_level == initial_zoom * 2.0
        assert viewport_state.visible_duration < viewport_state.full_duration

    def test_zoom_out(self, viewport_state, sample_time_range):
        """Test zoom out functionality."""
        start, end = sample_time_range
        viewport_state.set_full_time_range(start, end)

        # First zoom in
        viewport_state.zoom_in(factor=4.0)
        zoomed_level = viewport_state.zoom_level

        # Then zoom out
        viewport_state.zoom_out(factor=2.0)

        assert viewport_state.zoom_level == zoomed_level / 2.0

    def test_zoom_constraints(self, viewport_state, sample_time_range):
        """Test zoom level constraints (min and max)."""
        start, end = sample_time_range
        viewport_state.set_full_time_range(start, end)

        # Try to zoom out below minimum
        viewport_state.zoom_out(factor=10.0)
        assert viewport_state.zoom_level == viewport_state.min_zoom

        # Try to zoom in above maximum
        for _ in range(20):
            viewport_state.zoom_in(factor=2.0)
        assert viewport_state.zoom_level == viewport_state.max_zoom

    def test_reset_zoom(self, viewport_state, sample_time_range):
        """Test reset zoom functionality."""
        start, end = sample_time_range
        viewport_state.set_full_time_range(start, end)

        # Zoom in
        viewport_state.zoom_in(factor=5.0)
        assert viewport_state.zoom_level > 1.0

        # Reset
        viewport_state.reset_zoom()
        assert viewport_state.zoom_level == 1.0
        assert viewport_state.visible_time_range == (start, end)

    def test_pan_forward(self, viewport_state, sample_time_range):
        """Test panning forward in time."""
        start, end = sample_time_range
        viewport_state.set_full_time_range(start, end)

        # Zoom in first to allow panning
        viewport_state.zoom_in(factor=2.0)

        initial_start, _ = viewport_state.visible_time_range
        viewport_state.pan(delta_seconds=600)  # Pan 10 minutes forward

        new_start, _ = viewport_state.visible_time_range
        assert new_start > initial_start

    def test_pan_backward(self, viewport_state, sample_time_range):
        """Test panning backward in time."""
        start, end = sample_time_range
        viewport_state.set_full_time_range(start, end)

        # Zoom in and pan forward first
        viewport_state.zoom_in(factor=2.0)
        viewport_state.pan(delta_seconds=600)

        initial_start, _ = viewport_state.visible_time_range
        viewport_state.pan(delta_seconds=-300)  # Pan 5 minutes backward

        new_start, _ = viewport_state.visible_time_range
        assert new_start < initial_start

    def test_pan_constraints(self, viewport_state, sample_time_range):
        """Test pan constraints (can't pan beyond full range)."""
        start, end = sample_time_range
        viewport_state.set_full_time_range(start, end)

        # Zoom in
        viewport_state.zoom_in(factor=2.0)

        # Try to pan way backward (should constrain to start)
        viewport_state.pan(delta_seconds=-10000)
        visible_start, _ = viewport_state.visible_time_range
        assert visible_start == start

        # Try to pan way forward (should constrain to end)
        viewport_state.pan(delta_seconds=10000)
        _, visible_end = viewport_state.visible_time_range
        assert visible_end == end

    def test_set_time_range(self, viewport_state, sample_time_range):
        """Test setting time range directly."""
        start, end = sample_time_range
        viewport_state.set_full_time_range(start, end)

        # Set a custom visible range
        new_start = start + timedelta(minutes=10)
        new_end = start + timedelta(minutes=40)

        viewport_state.set_time_range(new_start, new_end)

        assert viewport_state.visible_time_range == (new_start, new_end)
        # Zoom level should be updated
        assert viewport_state.zoom_level > 1.0

    def test_set_time_range_constraints(self, viewport_state, sample_time_range):
        """Test time range constraints when setting directly."""
        start, end = sample_time_range
        viewport_state.set_full_time_range(start, end)

        # Try to set range outside full range
        new_start = start - timedelta(hours=1)
        new_end = end + timedelta(hours=1)

        viewport_state.set_time_range(new_start, new_end)

        # Should be constrained to full range
        visible_start, visible_end = viewport_state.visible_time_range
        assert visible_start == start
        assert visible_end == end

    def test_jump_to_time(self, viewport_state, sample_time_range):
        """Test jumping to a specific time."""
        start, end = sample_time_range
        viewport_state.set_full_time_range(start, end)

        # Zoom in first
        viewport_state.zoom_in(factor=3.0)

        # Jump to middle of range
        target = start + timedelta(minutes=30)
        viewport_state.jump_to_time(target)

        visible_start, visible_end = viewport_state.visible_time_range

        # Target should be approximately centered
        visible_center = visible_start + (visible_end - visible_start) / 2
        assert abs((visible_center - target).total_seconds()) < 60  # Within 1 minute

    def test_jump_to_time_constraints(self, viewport_state, sample_time_range):
        """Test jump to time constraints."""
        start, end = sample_time_range
        viewport_state.set_full_time_range(start, end)

        viewport_state.zoom_in(factor=3.0)

        # Try to jump before start
        viewport_state.jump_to_time(start - timedelta(hours=1))
        visible_start, _ = viewport_state.visible_time_range
        assert visible_start == start

        # Try to jump after end
        viewport_state.jump_to_time(end + timedelta(hours=1))
        _, visible_end = viewport_state.visible_time_range
        assert visible_end == end

    def test_full_duration(self, viewport_state, sample_time_range):
        """Test full duration calculation."""
        start, end = sample_time_range
        viewport_state.set_full_time_range(start, end)

        assert viewport_state.full_duration == timedelta(hours=1)

    def test_visible_duration(self, viewport_state, sample_time_range):
        """Test visible duration calculation."""
        start, end = sample_time_range
        viewport_state.set_full_time_range(start, end)

        # At 1x zoom, visible duration equals full duration
        assert viewport_state.visible_duration == viewport_state.full_duration

        # At 2x zoom, visible duration should be half
        viewport_state.zoom_in(factor=2.0)
        expected_duration = viewport_state.full_duration / 2
        actual_duration = viewport_state.visible_duration

        # Allow small tolerance for floating point errors
        assert abs((actual_duration - expected_duration).total_seconds()) < 1

    def test_zoom_maintains_center(self, viewport_state, sample_time_range):
        """Test that zooming maintains the center point of the viewport."""
        start, end = sample_time_range
        viewport_state.set_full_time_range(start, end)

        # Pan to a specific point
        target = start + timedelta(minutes=20)
        viewport_state.jump_to_time(target)

        # Get center before zoom
        vis_start, vis_end = viewport_state.visible_time_range
        center_before = vis_start + (vis_end - vis_start) / 2

        # Zoom in
        viewport_state.zoom_in(factor=2.0)

        # Get center after zoom
        vis_start, vis_end = viewport_state.visible_time_range
        center_after = vis_start + (vis_end - vis_start) / 2

        # Centers should be approximately the same
        assert abs((center_before - center_after).total_seconds()) < 5

    def test_set_zoom_level_directly(self, viewport_state, sample_time_range):
        """Test setting zoom level directly."""
        start, end = sample_time_range
        viewport_state.set_full_time_range(start, end)

        viewport_state.set_zoom_level(5.0)
        assert viewport_state.zoom_level == 5.0

        # Test clamping to max
        viewport_state.set_zoom_level(200.0)
        assert viewport_state.zoom_level == viewport_state.max_zoom

        # Test clamping to min
        viewport_state.set_zoom_level(0.5)
        assert viewport_state.zoom_level == viewport_state.min_zoom
