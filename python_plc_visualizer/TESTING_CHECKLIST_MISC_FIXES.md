# Testing Checklist - Miscellaneous UI Fixes

This checklist covers manual testing for the 4 miscellaneous fixes implemented:
1. Signal Interval Views as Tabs
2. Processing Time in Statistics
3. Collapsible Log Table Filter
4. Map Viewer YAML Configuration

## Signal Interval Tabs

### Opening Signal Interval Plots

- [ ] Load a PLC log file with signal data
- [ ] Open a Timing Diagram view
- [ ] Select a signal with transitions
- [ ] Click "Plot Change Intervals" button
- [ ] **Verify:** Interval plot opens as a new tab (not a separate window)
- [ ] **Verify:** Tab title shows "Intervals: [Signal Name]"
- [ ] **Verify:** No separate window appears

### Multiple Interval Plots

- [ ] Open an interval plot for a first signal (as above)
- [ ] Switch back to Timing Diagram tab
- [ ] Select a different signal with transitions
- [ ] Click "Plot Change Intervals" again
- [ ] **Verify:** Second interval plot opens as another tab
- [ ] **Verify:** Both interval tabs are visible in the tab bar
- [ ] **Verify:** Can switch between interval tabs

### Tab Behavior

- [ ] With multiple interval tabs open, close one tab (click X button)
- [ ] **Verify:** Tab closes cleanly without errors
- [ ] **Verify:** Other tabs remain open
- [ ] Switch between interval tabs and other view types (Timing, Log Table)
- [ ] **Verify:** Switching between tabs works smoothly

### Interval Plot Functionality

- [ ] Open an interval plot
- [ ] **Verify:** All controls are present (mode buttons, bin duration, percentile cap)
- [ ] Switch between modes (Change → change, Pulse width, Custom tokens)
- [ ] **Verify:** Mode switching works correctly
- [ ] Adjust bin duration slider
- [ ] **Verify:** Plot updates immediately
- [ ] Adjust percentile cap
- [ ] **Verify:** Y-axis scaling adjusts
- [ ] **Verify:** Table shows interval data correctly

## Processing Time

### Small Log File

- [ ] Load a small log file (< 100 KB)
- [ ] Wait for parsing to complete
- [ ] View the Parsing Statistics widget
- [ ] **Verify:** "Processing Time:" label is visible
- [ ] **Verify:** Time is shown in milliseconds (e.g., "123ms")
- [ ] **Verify:** Time value is reasonable (< 1000ms for small files)

### Large Log File

- [ ] Load a larger log file (> 1 MB)
- [ ] Wait for parsing to complete
- [ ] View the Parsing Statistics widget
- [ ] **Verify:** "Processing Time:" label is visible
- [ ] **Verify:** Time is shown in seconds (e.g., "2.34s")
- [ ] **Verify:** Time value is reasonable for file size

### Parsing with Errors

- [ ] Load an invalid or partially corrupted log file
- [ ] Wait for parsing to complete (with errors)
- [ ] View the Parsing Statistics widget
- [ ] **Verify:** Processing time is still shown
- [ ] **Verify:** Error count is also displayed

### Time Format Verification

- [ ] Parse multiple files of different sizes
- [ ] **Verify:** Files taking < 1s show time as "XXXms"
- [ ] **Verify:** Files taking ≥ 1s show time as "X.XXs"
- [ ] **Verify:** Very fast parsing (< 10ms) still shows time

## Collapsible Log Table Filter

### Initial State

- [ ] Load a log file
- [ ] Open Log Table view (Ctrl+L or via menu)
- [ ] **Verify:** Left panel contains signal filter controls
- [ ] **Verify:** Right panel contains the data table
- [ ] **Verify:** Splitter handle is visible between panels
- [ ] **Verify:** Initial sizes show filter panel narrower than table panel

### Collapsing Filter Panel

- [ ] Hover over splitter handle between filter and table
- [ ] **Verify:** Cursor changes to resize cursor
- [ ] Drag splitter handle to the left
- [ ] **Verify:** Filter panel collapses
- [ ] **Verify:** Table panel expands to fill space
- [ ] **Verify:** Table remains fully functional when filter collapsed

### Restoring Filter Panel

- [ ] With filter collapsed, drag splitter handle to the right
- [ ] **Verify:** Filter panel expands back
- [ ] **Verify:** Filter controls are still functional
- [ ] **Verify:** Previously selected filters are preserved

### Comparison with Timing Diagram

- [ ] Open both Timing Diagram and Log Table views
- [ ] **Verify:** Both use similar horizontal splitter pattern
- [ ] **Verify:** Splitter behavior is consistent between views
- [ ] **Verify:** Handle styling matches

### Filter Functionality When Collapsed/Expanded

- [ ] With filter panel visible, select some signals
- [ ] Collapse the filter panel
- [ ] **Verify:** Table still shows only selected signals
- [ ] Expand the filter panel
- [ ] **Verify:** Signal selection state is preserved
- [ ] Change signal selection
- [ ] **Verify:** Table updates correctly

## YAML Configuration

### Verify Map Viewer Still Works

- [ ] Load a log file
- [ ] Prepare a map viewer XML file
- [ ] Open Map Viewer (if available in your setup)
- [ ] **Verify:** Map viewer opens without errors
- [ ] **Verify:** Visual elements render correctly
- [ ] **Verify:** Colors and z-ordering appear correct

### Modify YAML Configuration

- [ ] Locate `python_plc_visualizer/tools/map_viewer/mappings_and_rules.yaml`
- [ ] Open the file in a text editor
- [ ] Modify a color in the `forecolor_mapping` section (e.g., change Red to a different hex value)
- [ ] Save the file
- [ ] Restart the application
- [ ] Open Map Viewer
- [ ] **Verify:** Color change is reflected in the map viewer

### Test Partial YAML

- [ ] Make a backup of `mappings_and_rules.yaml`
- [ ] Edit the YAML and remove the `render_as_text_types` section
- [ ] Save the file
- [ ] Restart the application
- [ ] **Verify:** Application starts without errors
- [ ] **Verify:** Map viewer uses fallback defaults for missing section
- [ ] Restore the backup file

### Test Invalid YAML

- [ ] Make a backup of `mappings_and_rules.yaml`
- [ ] Edit the YAML and introduce syntax errors (e.g., invalid indentation)
- [ ] Save the file
- [ ] Restart the application
- [ ] **Verify:** Application handles the error gracefully
- [ ] **Verify:** Console shows warning about invalid YAML
- [ ] **Verify:** Map viewer uses hardcoded fallback defaults
- [ ] Restore the backup file

### Verify Default Values

- [ ] Make a backup of `mappings_and_rules.yaml`
- [ ] Temporarily delete or rename the YAML file
- [ ] Restart the application
- [ ] **Verify:** Application starts without errors
- [ ] **Verify:** Map viewer works with hardcoded defaults
- [ ] **Verify:** Default colors and z-indices are applied
- [ ] Restore the YAML file

## Integration Testing

### All Fixes Together

- [ ] Load a log file
- [ ] **Verify:** Processing time appears in statistics
- [ ] Open Timing Diagram
- [ ] Open an interval plot for a signal
- [ ] **Verify:** Interval plot opens as tab
- [ ] Open Log Table view
- [ ] **Verify:** Filter is collapsible via splitter
- [ ] Collapse filter, expand it again
- [ ] Switch between all open tabs
- [ ] **Verify:** All views work correctly together
- [ ] Close some tabs
- [ ] Open new views
- [ ] **Verify:** No memory leaks or performance degradation

### Performance Check

- [ ] Load a large log file (> 10 MB)
- [ ] Note the processing time in statistics
- [ ] Open multiple interval plot tabs
- [ ] Open log table with filter
- [ ] Collapse/expand filter multiple times
- [ ] **Verify:** UI remains responsive
- [ ] **Verify:** No noticeable lag when switching tabs
- [ ] **Verify:** Memory usage is reasonable

## Regression Testing

### Existing Features Still Work

- [ ] Open Timing Diagram view
- [ ] **Verify:** Waveform displays correctly
- [ ] Zoom in/out on waveform
- [ ] **Verify:** Zoom controls work
- [ ] Pan left/right
- [ ] **Verify:** Pan controls work
- [ ] Filter signals
- [ ] **Verify:** Signal filtering works
- [ ] Open multiple Timing Diagram tabs
- [ ] **Verify:** Multiple timing diagrams work
- [ ] Use bookmarks
- [ ] **Verify:** Bookmark system works
- [ ] Sync views
- [ ] **Verify:** View synchronization works

## Sign-off

All tests passed: ☐ Yes ☐ No

Issues found:
```
(List any issues discovered during testing)
```

Tested by: ________________

Date: ________________

Build/Commit: ________________

