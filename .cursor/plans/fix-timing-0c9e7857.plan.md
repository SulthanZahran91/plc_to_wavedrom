<!-- 0c9e7857-d14f-409f-939a-0e31add98d9b 2e606235-055b-40e3-b713-a841612754ca -->
# Fix Timing Diagram Sync Reference Point

## Problem

When pressing "Sync Views" on a timing diagram, it jumps backward because:

- `get_current_time()` returns the **START** (leftmost) of visible range
- `jump_to_time()` **CENTERS** the target time in viewport
- Mismatch causes the view to shift backward

**Example:**

- Visible range: 10:00 to 10:10
- `get_current_time()` returns 10:00 (start)  
- `jump_to_time(10:00)` centers it → new range: 9:55 to 10:05
- Result: jumps backward by 5 seconds

## Solution

Change `TimingDiagramView.get_current_time()` to return the **MIDDLE** of the visible range. This way:

- Middle time is used as reference
- When `jump_to_time()` centers the middle, the view stays in place
- Other views sync to the middle of the timing diagram (more intuitive)

## Implementation

**File**: `python_plc_visualizer/plc_visualizer/ui/windows/timing_window.py`

Update `get_current_time()` method (around line 65):

```python
def get_current_time(self):
    """Get the current time position from the viewport."""
    if not self._viewport_state:
        return None
    visible_range = self._viewport_state.visible_time_range
    if visible_range:
        start, end = visible_range
        # Return middle of visible range (matches jump_to_time centering)
        return start + (end - start) / 2
    return None
```

## Expected Behavior After Fix

-  Press "Sync Views" on timing diagram → stays in exact same position
-  Other views sync to the middle of the timing diagram's visible range (most intuitive)
-  Syncing from other views still works correctly