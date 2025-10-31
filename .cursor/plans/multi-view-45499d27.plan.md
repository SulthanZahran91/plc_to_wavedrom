<!-- 45499d27-7988-421e-9ea8-1499c14aa1c0 a503d47d-9e96-4d6d-9cd9-0f85aff1a804 -->
# Fix View Synchronization

## Problem

The "Sync Views" button emits `session_manager.sync_requested` signal, but no views are listening to it. Views are created without connecting to this signal, so synchronization does not work.

## Root Cause

Views are instantiated in `MainWindow._add_*_view()` methods but are never connected to `session_manager.sync_requested`. Each view needs to:

1. Receive the session_manager reference
2. Connect to the `sync_requested` signal
3. Implement a sync handler method

## Implementation Plan

### 1. Update TimingDiagramView

**File**: `plc_visualizer/ui/windows/timing_window.py`

- Modify `__init__` to accept `session_manager` parameter (store as `_session_manager`)
- Connect to `session_manager.sync_requested` signal in `__init__`
- Add `_on_sync_requested(target_time)` method that calls `self._viewport_state.jump_to_time(target_time)` to center the target time

### 2. Update LogTableView

**File**: `plc_visualizer/ui/windows/log_table_window.py`

- Modify `__init__` to accept `session_manager` parameter (store as `_session_manager`)
- Connect to `session_manager.sync_requested` signal in `__init__`
- Add `_on_sync_requested(target_time)` method that:
- Searches through `self._parsed_log.entries` for the first entry at or after `target_time`
- Scrolls to that row using `self.data_table.table_view.scrollTo()`
- Selects that row using `selectionModel().select()`

### 3. Update MapViewerView

**File**: `plc_visualizer/ui/windows/map_viewer_window.py`

- Modify `__init__` to accept `session_manager` parameter (store as `_session_manager`)
- Connect to `session_manager.sync_requested` signal in `__init__`
- Add `_on_sync_requested(target_time)` method that:
- Pauses playback if currently playing (call `_pause()`)
- Calls `self.update_time_position(target_time)` to jump to the target time

### 4. Update MainWindow view creation methods

**File**: `plc_visualizer/ui/main_window.py`

Update three methods to pass `session_manager`:

- `_add_timing_view()`: Pass `self.session_manager` to `TimingDiagramView()`
- `_add_log_table_view()`: Pass `self.session_manager` to `LogTableView()`
- `_add_map_viewer_view()`: Pass `self.session_manager` to `MapViewerView()`

## Expected Behavior After Fix

- Click "Sync Views" button with TimingDiagramView active: All views jump to the visible start time of the timing diagram
- Click "Sync Views" button with LogTableView active (row selected): All views jump to the timestamp of the selected row
- Click "Sync Views" button with MapViewerView active: All views jump to the current playback position
- All views respond simultaneously when any view triggers sync

## Files Modified

1. `plc_visualizer/ui/windows/timing_window.py`
2. `plc_visualizer/ui/windows/log_table_window.py`
3. `plc_visualizer/ui/windows/map_viewer_window.py`
4. `plc_visualizer/ui/main_window.py`

### To-dos

- [ ] Add session_manager parameter and sync_requested handler to TimingDiagramView
- [ ] Add session_manager parameter and sync_requested handler to LogTableView
- [ ] Add session_manager parameter and sync_requested handler to MapViewerView
- [ ] Update MainWindow view creation methods to pass session_manager
- [ ] Test sync from each view type to verify all views respond correctly