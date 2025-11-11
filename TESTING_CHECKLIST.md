# Multi-View Window Manager - Testing Checklist

This checklist covers manual testing for the new multi-view system features.

##  Split Pane Functionality

### Basic Split Operations
- [ ] Start application and load test data
- [ ] Open a Timing Diagram (Ctrl+T)
- [ ] Verify initial view appears as a tab in single pane
- [ ] Open another Timing Diagram (Ctrl+T again)
- [ ] Verify it appears as a second tab in the same pane
- [ ] Click between tabs to verify tab switching works

### Drag-to-Split - Horizontal
- [ ] Drag a tab toward the top edge
- [ ] Verify blue drop zone appears within 20px of edge
- [ ] Release to create horizontal split
- [ ] Verify pane splits into top and bottom sections
- [ ] Verify dragged tab is now in the new pane
- [ ] Verify both panes are resizable by dragging the splitter

### Drag-to-Split - Vertical
- [ ] Drag a tab toward the left edge
- [ ] Verify blue drop zone appears
- [ ] Release to create vertical split
- [ ] Verify pane splits into left and right sections
- [ ] Try dragging to right edge as well
- [ ] Verify all directional splits work (left, right, top, bottom)

### Maximum Panes Constraint
- [ ] Create splits until you have 4 panes total
- [ ] Try to create a 5th split
- [ ] Verify warning dialog appears: "Maximum of 4 panes allowed"
- [ ] Verify no additional pane is created

### Pane Merging
- [ ] Close all tabs in one pane (using X button on tabs)
- [ ] Verify pane automatically merges back
- [ ] Verify remaining panes resize to fill space
- [ ] Test closing tabs from different panes
- [ ] Verify panes merge correctly in various configurations

### Tab Context Menu
- [ ] Right-click on a tab
- [ ] Verify context menu appears with:
  - "Close Tab"
  - "Close Other Tabs"
  - "Close All Tabs"
- [ ] Test "Close Tab" - verify single tab closes
- [ ] Test "Close Other Tabs" - verify all others close
- [ ] Test "Close All Tabs" - verify all tabs in pane close

---

##  Time Synchronization

### Sync Button Behavior
- [ ] Launch app without loading data
- [ ] Verify "Sync Views" button is disabled (grayed out)
- [ ] Load test data
- [ ] Verify "Sync Views" button becomes enabled

### Single View Type Sync
- [ ] Open two Timing Diagram views (Ctrl+T twice)
- [ ] Split them side-by-side
- [ ] Navigate to time 10:00:00 in first view
- [ ] Navigate to time 11:00:00 in second view
- [ ] Click on first view to make it active
- [ ] Click "Sync Views" button
- [ ] Verify second view jumps to ~10:00:00

### Multi View Type Sync
- [ ] Open Timing Diagram (Ctrl+T)
- [ ] Open Log Table (Ctrl+L)
- [ ] Open Map Viewer (Ctrl+M)
- [ ] Split them into 3 visible panes
- [ ] Navigate Timing Diagram to specific time (e.g., 14:32:15)
- [ ] Make Timing Diagram the active view (click it)
- [ ] Click "Sync Views" button
- [ ] Verify Log Table scrolls to that timestamp
- [ ] Verify Map Viewer updates to show state at that time
- [ ] Verify all views show synchronized time

### Sync Edge Cases
- [ ] Try clicking "Sync Views" with no active view
- [ ] Verify appropriate error message
- [ ] Try clicking "Sync Views" with only Log Table open (no timing view)
- [ ] Verify appropriate behavior or message

---

##  Bookmark System

### Adding Bookmarks via Keyboard
- [ ] Open Timing Diagram and load data
- [ ] Navigate to an interesting time
- [ ] Press Ctrl+B
- [ ] Verify dialog appears asking for bookmark label
- [ ] Enter label: "Test Bookmark 1"
- [ ] Press Enter
- [ ] Verify confirmation message appears
- [ ] Navigate to different time
- [ ] Press Ctrl+B again
- [ ] Enter label: "Test Bookmark 2"
- [ ] Verify second bookmark is added

### Bookmark Dialog
- [ ] Press Ctrl+Shift+B
- [ ] Verify bookmark dialog opens
- [ ] Verify table shows both bookmarks with:
  - Timestamp column
  - Label column
  - Description column
- [ ] Verify bookmarks are sorted by timestamp (earliest first)

### Jumping to Bookmarks - Dialog
- [ ] In bookmark dialog, click on first bookmark
- [ ] Press Enter (or double-click)
- [ ] Verify dialog closes
- [ ] Verify all views jump to that timestamp
- [ ] Open dialog again (Ctrl+Shift+B)
- [ ] Select second bookmark and press Enter
- [ ] Verify all views jump to second bookmark timestamp

### Jumping to Bookmarks - Keyboard
- [ ] Press Ctrl+] (next bookmark)
- [ ] Verify views jump to next bookmark
- [ ] Press Ctrl+] again
- [ ] Verify it wraps to first bookmark
- [ ] Press Ctrl+[ (previous bookmark)
- [ ] Verify views jump to previous bookmark
- [ ] Press Ctrl+[ multiple times
- [ ] Verify it wraps around correctly

### Adding Bookmarks from Dialog
- [ ] Open bookmark dialog (Ctrl+Shift+B)
- [ ] Click "Add Bookmark" button
- [ ] Enter label and optional description
- [ ] Verify new bookmark appears in list
- [ ] Verify list remains sorted by timestamp

### Deleting Bookmarks
- [ ] Open bookmark dialog
- [ ] Select a bookmark
- [ ] Click "Delete" button
- [ ] Verify confirmation dialog appears
- [ ] Confirm deletion
- [ ] Verify bookmark is removed from list
- [ ] Close and reopen dialog
- [ ] Verify deletion persisted

### Bookmark Persistence
- [ ] Add several bookmarks
- [ ] Clear the session (Clear button)
- [ ] Verify bookmarks are cleared
- [ ] Load data again
- [ ] Verify bookmarks list is empty (session-specific)

---

##  View Management

### Menu System
- [ ] Click "View" menu
- [ ] Verify options appear:
  - "New Timing Diagram" (Ctrl+T)
  - "New Log Table" (Ctrl+L)
  - "New Map Viewer" (Ctrl+M)
  - "Plot Signal Intervals"
- [ ] Test each menu item
- [ ] Verify views are created correctly

### Bookmarks Menu
- [ ] Click "Bookmarks" menu
- [ ] Verify options appear:
  - "Add Bookmark at Current Time" (Ctrl+B)
  - "Show Bookmarks" (Ctrl+Shift+B)
  - "Next Bookmark" (Ctrl+])
  - "Previous Bookmark" (Ctrl+[)
- [ ] Test each menu item
- [ ] Verify keyboard shortcuts work

### Multiple Views of Same Type
- [ ] Open 3 Timing Diagrams
- [ ] Verify each has its own tab
- [ ] Verify all share the same viewport state
- [ ] Change time in one view
- [ ] Click "Sync Views"
- [ ] Verify all three timing diagrams sync

### View Isolation
- [ ] Open Timing Diagram and Log Table in different panes
- [ ] Navigate to different times in each
- [ ] Close one pane
- [ ] Verify other pane continues working
- [ ] Verify no errors or crashes

---

##  Data Loading & Updates

### Loading Data with Open Views
- [ ] Open several views in split panes
- [ ] Load test data
- [ ] Verify all open views receive the data
- [ ] Verify timing diagrams show waveforms
- [ ] Verify log tables show entries
- [ ] Verify map viewer updates

### Clearing Data with Open Views
- [ ] With multiple views open and data loaded
- [ ] Click "Clear" button
- [ ] Verify all views clear their data
- [ ] Verify views remain open (not closed)
- [ ] Verify "Sync Views" button becomes disabled
- [ ] Verify views are ready for new data

### Opening Views Before Data Load
- [ ] Start fresh (no data loaded)
- [ ] Open Timing Diagram (Ctrl+T)
- [ ] Verify empty/placeholder state
- [ ] Load test data
- [ ] Verify view populates with data

---

##  Layout Persistence

### Window Resize
- [ ] Create 4-pane layout
- [ ] Resize main window
- [ ] Verify all panes resize proportionally
- [ ] Verify no layout breaking

### Splitter Adjustment
- [ ] Create 2-pane vertical split
- [ ] Drag the splitter to resize panes
- [ ] Verify both panes resize smoothly
- [ ] Test with 4 panes and multiple splitters
- [ ] Verify all splitters work independently

---

##  Performance & Stability

### Large Numbers of Tabs
- [ ] Create 10+ tabs in a single pane
- [ ] Verify tab scrolling works
- [ ] Verify switching between tabs is responsive
- [ ] Close all tabs
- [ ] Verify no memory leaks or crashes

### Rapid Split/Merge
- [ ] Rapidly create and destroy splits
- [ ] Drag tabs between panes quickly
- [ ] Close panes in various orders
- [ ] Verify no crashes or UI glitches

### Sync with Large Data
- [ ] Load large log file (10,000+ entries)
- [ ] Create 4 panes with different views
- [ ] Click "Sync Views"
- [ ] Verify sync completes without lag
- [ ] Verify all views update correctly

---

##  Known Issues to Watch For

Document any issues found:

1. **Issue**: 
   - Steps to reproduce:
   - Expected behavior:
   - Actual behavior:

2. **Issue**:
   - Steps to reproduce:
   - Expected behavior:
   - Actual behavior:

---

##  Final Integration Test

### Complete Workflow
- [ ] Start application fresh
- [ ] Load sample PLC log data
- [ ] Open Timing Diagram (Ctrl+T)
- [ ] Navigate timeline and identify 3 interesting events
- [ ] Add bookmarks at each event (Ctrl+B)
- [ ] Open Log Table (Ctrl+L)
- [ ] Drag to create side-by-side split
- [ ] Open Map Viewer (Ctrl+M) in third pane
- [ ] Use Ctrl+[ and Ctrl+] to navigate between bookmarks
- [ ] Verify all views stay synchronized
- [ ] Click "Sync Views" to verify manual sync
- [ ] Close one pane by closing all its tabs
- [ ] Verify layout adjusts correctly
- [ ] Open bookmark dialog (Ctrl+Shift+B)
- [ ] Jump to a bookmark from dialog
- [ ] Verify all remaining views update
- [ ] Close application
- [ ] Verify clean exit with no errors

---

## Test Results Summary

**Date**: ___________
**Tester**: ___________
**Total Tests**: ___________
**Passed**: ___________
**Failed**: ___________
**Notes**:

