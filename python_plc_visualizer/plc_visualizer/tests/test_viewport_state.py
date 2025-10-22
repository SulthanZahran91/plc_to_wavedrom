"""Unit tests for the ViewportState helper."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from plc_visualizer.utils.viewport_state import ViewportState


class TestViewportState:
    """Comprehensive tests for viewport state management."""

    @pytest.fixture
    def viewport_state(self) -> ViewportState:
        return ViewportState()

    @pytest.fixture
    def long_range(self) -> tuple[datetime, datetime]:
        start = datetime(2024, 1, 1, 10, 0, 0)
        end = datetime(2024, 1, 1, 11, 0, 0)  # 60 minutes
        return start, end

    @pytest.fixture
    def short_range(self) -> tuple[datetime, datetime]:
        start = datetime(2024, 1, 1, 12, 0, 0)
        end = datetime(2024, 1, 1, 12, 2, 0)  # 2 minutes
        return start, end

    def test_initial_state(self, viewport_state: ViewportState):
        assert viewport_state.full_time_range is None
        assert viewport_state.visible_time_range is None
        assert viewport_state.zoom_level == 1.0

    def test_set_full_range_long_duration(self, viewport_state: ViewportState, long_range: tuple[datetime, datetime]):
        start, end = long_range
        viewport_state.set_full_time_range(start, end)

        assert viewport_state.full_time_range == (start, end)
        visible_start, visible_end = viewport_state.visible_time_range
        assert visible_start == start
        assert visible_end == start + timedelta(seconds=ViewportState.MAX_VISIBLE_DURATION_SECONDS)
        assert viewport_state.visible_duration == timedelta(seconds=ViewportState.MAX_VISIBLE_DURATION_SECONDS)
        assert viewport_state.zoom_level == pytest.approx(
            (end - start).total_seconds() / ViewportState.MAX_VISIBLE_DURATION_SECONDS
        )

    def test_set_full_range_short_duration(self, viewport_state: ViewportState, short_range: tuple[datetime, datetime]):
        start, end = short_range
        viewport_state.set_full_time_range(start, end)

        assert viewport_state.full_time_range == (start, end)
        assert viewport_state.visible_time_range == (start, end)
        assert viewport_state.visible_duration == timedelta(minutes=2)
        assert viewport_state.zoom_level == pytest.approx(1.0)

    def test_zoom_in_reduces_duration(self, viewport_state: ViewportState, long_range: tuple[datetime, datetime]):
        viewport_state.set_full_time_range(*long_range)
        baseline_duration = viewport_state.visible_duration

        viewport_state.zoom_in(factor=2.0)

        assert viewport_state.visible_duration < baseline_duration
        assert viewport_state.visible_duration.total_seconds() == pytest.approx(
            baseline_duration.total_seconds() / 2, rel=1e-3
        )

    def test_zoom_out_respects_maximum(self, viewport_state: ViewportState, long_range: tuple[datetime, datetime]):
        viewport_state.set_full_time_range(*long_range)
        viewport_state.zoom_in(factor=4.0)
        zoomed_duration = viewport_state.visible_duration

        viewport_state.zoom_out(factor=10.0)

        assert viewport_state.visible_duration >= zoomed_duration
        assert viewport_state.visible_duration == timedelta(seconds=ViewportState.MAX_VISIBLE_DURATION_SECONDS)

    def test_zoom_in_hits_minimum(self, viewport_state: ViewportState, long_range: tuple[datetime, datetime]):
        viewport_state.set_full_time_range(*long_range)

        # Repeat zoom in until we hit the minimum duration
        for _ in range(20):
            viewport_state.zoom_in(factor=4.0)

        assert viewport_state.visible_duration_seconds == pytest.approx(
            viewport_state.min_visible_duration, rel=1e-6
        )

    def test_reset_zoom_restores_initial_window(self, viewport_state: ViewportState, long_range: tuple[datetime, datetime]):
        viewport_state.set_full_time_range(*long_range)
        viewport_state.zoom_in(factor=3.0)
        viewport_state.pan(delta_seconds=120)

        viewport_state.reset_zoom()

        assert viewport_state.visible_time_range == (
            long_range[0],
            long_range[0] + timedelta(seconds=ViewportState.MAX_VISIBLE_DURATION_SECONDS),
        )

    def test_pan_respects_bounds(self, viewport_state: ViewportState, long_range: tuple[datetime, datetime]):
        viewport_state.set_full_time_range(*long_range)
        viewport_state.zoom_in(factor=3.0)

        start_before, end_before = viewport_state.visible_time_range
        viewport_state.pan(delta_seconds=300)
        start_after, end_after = viewport_state.visible_time_range

        assert start_after > start_before
        assert end_after > end_before

        # Pan backward beyond start; should clamp to the beginning
        viewport_state.pan(delta_seconds=-10_000)
        clamped_start, clamped_end = viewport_state.visible_time_range
        assert clamped_start == viewport_state.full_time_range[0]
        assert clamped_end - clamped_start == viewport_state.visible_duration

    def test_set_time_range_clamps_duration(self, viewport_state: ViewportState, long_range: tuple[datetime, datetime]):
        start, end = long_range
        viewport_state.set_full_time_range(start, end)

        requested_start = start + timedelta(minutes=5)
        requested_end = start + timedelta(minutes=45)
        viewport_state.set_time_range(requested_start, requested_end)

        visible_start, visible_end = viewport_state.visible_time_range
        assert visible_start == requested_start
        assert visible_end == requested_start + timedelta(seconds=ViewportState.MAX_VISIBLE_DURATION_SECONDS)
        assert viewport_state.visible_duration == timedelta(seconds=ViewportState.MAX_VISIBLE_DURATION_SECONDS)

    def test_set_time_range_handles_small_spans(self, viewport_state: ViewportState, long_range: tuple[datetime, datetime]):
        start, end = long_range
        viewport_state.set_full_time_range(start, end)

        tiny_start = start + timedelta(seconds=10)
        tiny_end = tiny_start + timedelta(milliseconds=10)
        viewport_state.set_time_range(tiny_start, tiny_end)

        visible_start, visible_end = viewport_state.visible_time_range
        assert visible_start <= tiny_start
        assert visible_end - visible_start == timedelta(seconds=viewport_state.visible_duration_seconds)
        assert viewport_state.visible_duration_seconds >= viewport_state.min_visible_duration

    def test_jump_to_time_centers_view(self, viewport_state: ViewportState, long_range: tuple[datetime, datetime]):
        viewport_state.set_full_time_range(*long_range)
        viewport_state.zoom_in(factor=4.0)

        target = long_range[0] + timedelta(minutes=20)
        viewport_state.jump_to_time(target)

        start_visible, end_visible = viewport_state.visible_time_range
        center = start_visible + (end_visible - start_visible) / 2
        assert abs((center - target).total_seconds()) < 1

    def test_jump_to_time_clamps_to_edges(self, viewport_state: ViewportState, long_range: tuple[datetime, datetime]):
        viewport_state.set_full_time_range(*long_range)
        viewport_state.zoom_in(factor=3.0)

        viewport_state.jump_to_time(long_range[0] - timedelta(hours=1))
        assert viewport_state.visible_time_range[0] == long_range[0]

        viewport_state.jump_to_time(long_range[1] + timedelta(hours=1))
        assert viewport_state.visible_time_range[1] == long_range[1]

    def test_set_zoom_level_directly_respects_bounds(self, viewport_state: ViewportState, long_range: tuple[datetime, datetime]):
        viewport_state.set_full_time_range(*long_range)
        full_seconds = (viewport_state.full_duration or timedelta()).total_seconds()

        viewport_state.set_zoom_level(6.0)
        # 3600 / 6 = 600 seconds, but max visible duration is 300 seconds.
        expected_duration = min(viewport_state.max_visible_duration, full_seconds / 6.0)
        assert viewport_state.visible_duration_seconds == pytest.approx(expected_duration, rel=1e-3)
        assert viewport_state.zoom_level == pytest.approx(full_seconds / expected_duration, rel=1e-3)

        viewport_state.set_zoom_level(0.1)
        expected_duration = min(viewport_state.max_visible_duration, full_seconds / 0.1)
        assert viewport_state.visible_duration_seconds == pytest.approx(expected_duration, rel=1e-3)

        viewport_state.set_zoom_level(10_000.0)
        assert viewport_state.visible_duration_seconds >= viewport_state.min_visible_duration

    def test_set_zoom_level_directly_with_short_range(self, viewport_state: ViewportState, short_range: tuple[datetime, datetime]):
        viewport_state.set_full_time_range(*short_range)
        full_seconds = (viewport_state.full_duration or timedelta()).total_seconds()

        viewport_state.set_zoom_level(2.0)
        expected_duration = full_seconds / 2.0
        assert viewport_state.visible_duration_seconds == pytest.approx(expected_duration, rel=1e-3)
        assert viewport_state.zoom_level == pytest.approx(2.0, rel=1e-3)
