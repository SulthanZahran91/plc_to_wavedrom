<!-- 45499d27-7988-421e-9ea8-1499c14aa1c0 ca25a723-1792-4fec-980a-b1e88e17c671 -->
# Enhanced Keyboard Shortcuts

## Overview

Add better keyboard shortcuts throughout the application for improved navigation and workflow efficiency. All new shortcuts must be documented in the help dialog.

## Current State

- Basic shortcuts exist: Ctrl+T/L/M (new views), Ctrl+B (bookmarks), F1 (help)
- CopyPasteTableView already implements Ctrl+C for copying
- No tab switching shortcuts
- No keyboard navigation in timing diagram or map viewer
- Help dialog exists but needs updating

## Shortcuts to Implement

### 1. Tab Navigation (ViewTabWidget & SplitPaneManager)

**Ctrl+PgDn** - Switch to next tab in active pane

**Ctrl+PgUp** - Switch to previous tab in active pane

**Ctrl+W** - Close current tab (standard)

**Ctrl+Tab** - Switch to next tab (alternative)

**Ctrl+Shift+Tab** - Switch to previous tab (alternative)

### 2. Timing Diagram View Navigation

**Left Arrow** - Pan left (move backward in time)

**Right Arrow** - Pan right (move forward in time)

**Up Arrow** - Scroll up through signals

**Down Arrow** - Scroll down through signals

**Home** - Jump to start of data

**End** - Jump to end of data

**+/=** - Zoom in

**-** - Zoom out

### 3. Map Viewer Navigation

**Left Arrow** - Skip backward 10 seconds

**Right Arrow** - Skip forward 10 seconds

**Space** - Play/Pause

**Home** - Jump to start

**End** - Jump to end

### 4. Log Table (already has copy, verify it works)

**Ctrl+C** - Copy selected cells (already implemented via CopyPasteTableView)

**Ctrl+F** - Focus search/filter box (if not already there)

### 5. Global Shortcuts (already implemented, just document)

**F1** - Help

**Ctrl+T** - New Timing Diagram

**Ctrl+L** - New Log Table

**Ctrl+M** - New Map Viewer

**Ctrl+B** - Add Bookmark

**Ctrl+Shift+B** - Show Bookmarks

**Ctrl+]** - Next Bookmark

**Ctrl+[** - Previous Bookmark

## Implementation Plan

### Phase 1: Tab Navigation

**File**: `view_tab_widget.py`

- Override `keyPressEvent` in ViewTabWidget
- Implement Ctrl+PgDn/PgUp to switch tabs
- Implement Ctrl+W to close current tab
- Handle Ctrl+Tab / Ctrl+Shift+Tab

**File**: `split_pane_manager.py`

- Install event filter on panes to catch tab navigation shortcuts
- Route shortcuts to appropriate pane

### Phase 2: Timing Diagram Navigation

**File**: `timing_window.py` or `waveform_view.py`

- Override `keyPressEvent` to handle arrow keys
- Connect to existing pan/zoom controls
- Left/Right: emit pan signals
- Up/Down: scroll viewport
- Home/End: jump to time boundaries
- +/=/-: trigger zoom

### Phase 3: Map Viewer Navigation

**File**: `map_viewer_window.py`

- Override `keyPressEvent`
- Left/Right: call `_skip_backward()` / `_skip_forward()`
- Space: call `_toggle_play()`
- Home/End: jump to start/end time

### Phase 4: Update Help Dialog

**File**: `help_dialog.py`

- Update "Shortcuts" tab with ALL new shortcuts
- Organize by context (Global, Tab Management, Navigation)
- Update Quick Reference table
- Add navigation tips for each view type

### Phase 5: Testing

- Test all shortcuts in each context
- Verify no conflicts with existing shortcuts
- Ensure focus handling works correctly
- Test on different platforms if possible

## Technical Details

### Event Handling Approach

- Use `keyPressEvent` override for view-specific shortcuts
- Use `QShortcut` for global shortcuts (already done in MainWindow)
- Consider `installEventFilter` for tab widget shortcuts
- Ensure shortcuts don't interfere with text input widgets

### Focus Management

- Shortcuts should only work when relevant view has focus
- Tab navigation should work when any pane has focus
- Global shortcuts work regardless of focus (via QShortcut)

### Tooltip Updates

- Add keyboard shortcut hints to button tooltips
- Example: "Pan left (← or click)"

## Help Documentation Updates

### Shortcuts Tab Structure

```
Keyboard Shortcuts
├── Global Shortcuts
│   ├── File & Views
│   └── Help
├── Tab Management
│   ├── Switching Tabs
│   └── Closing Tabs
├── Timing Diagram Navigation
│   ├── Time Navigation
│   ├── Signal Navigation
│   └── Zoom
├── Map Viewer Navigation
│   ├── Playback Control
│   └── Time Jumping
├── Log Table
│   └── Selection & Copy
└── Quick Reference Card (updated table)
```

## Files to Modify

- `ui/components/view_tab_widget.py` - tab navigation shortcuts
- `ui/components/split_pane_manager.py` - event filtering for tab shortcuts
- `ui/windows/timing_window.py` - timing diagram navigation
- `ui/windows/map_viewer_window.py` - map viewer navigation
- `ui/dialogs/help_dialog.py` - comprehensive shortcut documentation

## Benefits

- Keyboard-driven workflow for power users
- Standard shortcuts (Ctrl+PgDn/Up) feel native
- Navigation without mouse improves efficiency
- Comprehensive help makes shortcuts discoverable
- Better accessibility overall

### To-dos

- [x] 
- [x] 
- [x] 
- [x] 