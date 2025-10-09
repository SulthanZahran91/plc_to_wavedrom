# **PLC Log Visualizer - Multi-Step Implementation Specs (Python + Qt)**

## **STEP 1: Project Setup & Log File Parser**

### Objective:
Create the foundation - a desktop application that can parse PLC log files and display the raw data.

### Technical Requirements:
1. **Project Structure:**
   - Python 3.10+ with PyQt6
   - Dependencies: `PyQt6`, `pytest`, `dataclasses`
   - Folder structure:
     ```
     plc_visualizer/
       __init__.py
       models/
         __init__.py
         data_types.py
       parsers/
         __init__.py
         base_parser.py
         default_parser.py
         parser_registry.py
       ui/
         __init__.py
         main_window.py
         file_upload_widget.py
         stats_widget.py
         data_table_widget.py
       utils/
         __init__.py
       tests/
         __init__.py
         test_parser.py
       main.py
     ```

2. **Data Types (models/data_types.py):**
   ```python
   from dataclasses import dataclass
   from datetime import datetime
   from typing import Literal, Union
   from enum import Enum

   class SignalType(Enum):
       BOOLEAN = "boolean"
       STRING = "string"
       INTEGER = "integer"

   @dataclass
   class LogEntry:
       signal_name: str
       timestamp: datetime
       value: Union[bool, str, int]
       signal_type: SignalType

   @dataclass
   class ParsedLog:
       entries: list[LogEntry]
       signals: set[str]
       time_range: tuple[datetime, datetime]

   @dataclass
   class ParseError:
       line: int
       content: str
       reason: str

   @dataclass
   class ParseResult:
       data: ParsedLog | None
       errors: list[ParseError]
   ```

3. **Parser Architecture (parsers/):**
   - **Base Class:** `BaseParser` - abstract class all parsers must inherit
   - **Default Parser:** Parse log format: `SIGNAL_NAME HH:MM:SS value type`
   - **Parser Registry:** Allow registering custom parsers
   - Handle multiple date/time formats
   - Validate each line and collect errors
   - Return structured data + parsing errors
   - **Streaming support:** Parse files line-by-line for memory efficiency
   - **Pluggable design:** Easy to add new parsers (CSV, XML, etc.) without modifying core logic

4. **UI Components (Qt Widgets):**
   - File upload with drag-and-drop zone (QWidget with dragEnterEvent)
   - Progress bar during parsing (QProgressBar)
   - Display parsing errors if any (QTextEdit with error formatting)
   - Show basic stats: total entries, unique signals, time range (custom QWidget)
   - Display raw parsed data in a table (QTableView with custom model)

### Testing Requirements:
1. **Unit Tests (tests/test_parser.py using pytest):**
   - Parse valid log entries correctly
   - Handle invalid lines gracefully
   - Parse boolean values (true/false, 0/1)
   - Parse string values
   - Parse integer values
   - Handle timestamps correctly
   - Detect signal types automatically
   - Return errors for malformed lines
   - Test streaming parsing for large files

2. **Test Data:**
   Create sample log file (`test_data/sample.log`):
   ```
   DEVICE_A MOTOR_START 10:30:45 true boolean
   DEVICE_A SENSOR_A 10:30:46 ready string
   DEVICE_A COUNTER_1 10:30:47 100 integer
   DEVICE_A MOTOR_START 10:30:50 false boolean
   DEVICE_A SENSOR_A 10:30:51 error string
   INVALID LINE HERE
   DEVICE_A COUNTER_1 10:30:52 150 integer
   ```

3. **Integration Tests (tests/test_ui.py using pytest-qt):**
   - Upload file and verify parsing completes
   - Verify UI shows correct number of entries
   - Verify error messages appear for invalid lines
   - Test drag-and-drop functionality

### User Expectations:
- [ ] User can click or drag-drop a log file onto the window
- [ ] User sees a progress bar while file is being parsed
- [ ] User sees a summary: "Parsed 1,247 entries, 45 unique signals, from 10:30:00 to 14:25:33"
- [ ] If there are parsing errors, user sees: "Warning: 3 lines could not be parsed" with expandable details
- [ ] User sees a table with columns: Device ID | Signal Name | Timestamp | Value | Type
- [ ] Table efficiently displays all entries (virtualized scrolling for 1GB+ files)
- [ ] User can load a different file and see new results
- [ ] Application starts quickly and uses minimal memory when idle

---

## **STEP 2: Basic Waveform Visualization**

### Objective:
Render signals as timing diagram waves using Qt Graphics View Framework.

### Technical Requirements:
1. **New Components (ui/):**
   - `waveform_view.py` - QGraphicsView for displaying waveforms
   - `waveform_scene.py` - QGraphicsScene containing all waveform items
   - `time_axis_item.py` - Custom QGraphicsItem for time scale
   - `signal_item.py` - Custom QGraphicsItem for single signal

2. **Waveform Renderer (ui/renderers/):**
   - `base_renderer.py` - Abstract base for signal renderers
   - `boolean_renderer.py` - Draw high/low square waves
   - `state_renderer.py` - Draw labeled state boxes for string/integer
   - Draw time axis with labels
   - Draw signal names on the left
   - Handle viewport transformations and scaling
   - **Hardware-accelerated rendering** via Qt's OpenGL backend

3. **Data Processing:**
   - Group log entries by signal name
   - Sort entries by timestamp for each signal
   - Calculate signal state durations

4. **UI Layout:**
   - Split view: Signal list (left) + Waveform canvas (right)
   - Show all signals initially
   - Fixed height per signal (e.g., 40px)
   - Scrollable canvas for many signals

5. **Styling:**
   - Boolean high = green, low = gray
   - String/integer states = blue boxes with centered text
   - Grid lines for time reference
   - Clear signal name labels

### Testing Requirements:
1. **Unit Tests (waveformRenderer.test.ts):**
   - Calculate correct pixel positions for timestamps
   - Draw boolean signal transitions correctly
   - Draw string state boxes with correct widths
   - Handle edge cases (single entry, no transitions)
   - Scale time axis correctly

2. **Visual Tests:**
   - Create test log with known pattern
   - Verify visual output matches expected diagram
   - Test with 1 signal, 10 signals, 100 signals

3. **Performance Tests:**
   - Render 100 signals in < 500ms
   - Canvas renders without blocking UI

### User Expectations:
- [ ] User sees timing diagram automatically after file is parsed
- [ ] Boolean signals show as square waves (high/low)
- [ ] String signals show as labeled boxes with the string value inside
- [ ] Integer signals show as labeled boxes with the number inside
- [ ] Time axis at top shows timestamps
- [ ] Signal names are clearly visible on the left
- [ ] User can scroll vertically to see all signals
- [ ] Diagram fills the available width
- [ ] Colors are distinct and readable

---

## **STEP 3: Time Navigation & Zoom**

### Objective:
Add interactive time navigation, zoom in/out, and panning.

### Technical Requirements:
1. **State Management (stores/viewportStore.ts):**
   ```typescript
   interface ViewportState {
     timeRange: { start: Date; end: Date };
     zoomLevel: number;
     setTimeRange: (start: Date, end: Date) => void;
     zoomIn: () => void;
     zoomOut: () => void;
     resetZoom: () => void;
   }
   ```

2. **Zoom Controls:**
   - Zoom in/out buttons
   - Zoom slider (1x to 100x)
   - Mouse wheel zoom on canvas
   - Reset zoom button
   - Display current zoom level

3. **Pan Controls:**
   - Click and drag on canvas to pan horizontally
   - Scrollbar for horizontal navigation
   - "Jump to time" input field
   - Previous/Next transition buttons

4. **Time Range Selector:**
   - Visual time range slider component
   - Shows full log time range
   - Draggable handles for start/end
   - Current viewport highlighted

5. **Rendering Optimization:**
   - Only render signals in visible time range
   - Implement viewport culling
   - Debounce zoom/pan events

### Testing Requirements:
1. **Unit Tests:**
   - Zoom calculations correct at various levels
   - Pan keeps timestamps aligned
   - Time range constraints enforced (can't pan beyond log)
   - Zoom focuses on canvas center

2. **Integration Tests:**
   - Mouse wheel zoom works
   - Drag to pan works
   - Zoom buttons work
   - Time range slider updates viewport
   - "Jump to time" works

3. **Performance Tests:**
   - Smooth zoom (no lag) up to 50x
   - Smooth pan across full log
   - Re-render time < 100ms

### User Expectations:
- [ ] User can zoom in/out using +/- buttons
- [ ] User can zoom with mouse wheel while hovering over canvas
- [ ] User can click and drag on canvas to pan left/right
- [ ] User sees zoom level displayed (e.g., "Zoom: 10x")
- [ ] User can click "Reset Zoom" to see full log again
- [ ] User sees a time range slider showing current viewport
- [ ] User can drag slider handles to change visible time range
- [ ] User can type a time and jump to that point
- [ ] Zooming feels smooth and responsive
- [ ] Signal labels remain visible while panning

---

## **STEP 4: Signal Filtering**

### Objective:
Allow users to filter which signals are displayed.

### Technical Requirements:
1. **Filter Components:**
   - `SignalFilter.tsx` - Main filter UI
   - Search bar with instant filtering
   - Checkbox list of all signals
   - "Select All" / "Deselect All" buttons
   - "Show only changed signals" toggle

2. **Filter Logic (utils/signalFilter.ts):**
   - Text search (case-insensitive, partial match)
   - Regex support (when query starts with `/`)
   - Filter by signal type (boolean/string/integer checkboxes)
   - Filter by activity (signals that changed vs. constant)
   - Combine multiple filter criteria with AND logic

3. **State Management:**
   ```typescript
   interface FilterState {
     searchQuery: string;
     selectedSignals: Set<string>;
     showOnlyChanged: boolean;
     typeFilters: Set<SignalType>;
     visibleSignals: string[];
   }
   ```

4. **UI Features:**
   - Show count: "Showing 15 of 127 signals"
   - Clear filters button
   - Save filter preset (name + restore)
   - Visual indicator when filters are active

5. **Performance:**
   - Debounce search input
   - Efficient set operations for signal selection
   - Only re-render when filter changes

### Testing Requirements:
1. **Unit Tests (signalFilter.test.ts):**
   - Text search matches correctly
   - Regex search works
   - Case-insensitive search
   - Type filter works (show only boolean signals)
   - "Changed only" filter works
   - Combining filters works correctly
   - Empty search shows all signals

2. **Integration Tests:**
   - Search updates canvas immediately
   - Selecting/deselecting signals updates display
   - Filter count is accurate
   - Clear filters restores all signals
   - Save/load preset works

### User Expectations:
- [ ] User sees a search bar above signal list
- [ ] Typing in search instantly filters signals (e.g., "MOTOR" shows all motor-related signals)
- [ ] User can use regex (e.g., `/MOTOR_\d+/`) for advanced filtering
- [ ] User sees checkboxes for each signal
- [ ] User can check/uncheck signals to show/hide them
- [ ] User can click "Select All" or "Deselect All"
- [ ] User sees signal type filters (Boolean, String, Integer) with checkboxes
- [ ] User can toggle "Show only changed signals" to hide constant signals
- [ ] User sees "Showing X of Y signals" count
- [ ] User can click "Clear Filters" to reset everything
- [ ] Canvas updates immediately when filter changes
- [ ] Performance remains good with 100+ signals

---

## **STEP 5: Interactive Measurement Tools**

### Objective:
Add cursors and measurement tools for precise analysis.

### Technical Requirements:
1. **Cursor System:**
   - Primary cursor (follows mouse)
   - Secondary cursor (click to place)
   - Show timestamp at cursor position
   - Show signal values at cursor
   - Display time delta between cursors

2. **Components:**
   - `Cursor.tsx` - Visual cursor line
   - `CursorInfo.tsx` - Info panel showing cursor data
   - `MeasurementPanel.tsx` - Shows delta measurements

3. **Interaction:**
   - Hover shows primary cursor with timestamp
   - Click places secondary cursor
   - Right-click removes secondary cursor
   - Keyboard arrows move primary cursor to next/prev transition

4. **Info Display:**
   - Floating panel near cursor showing:
     - Current timestamp
     - All signal values at this time
   - Separate panel showing:
     - Time between cursors (Δt)
     - Distance in milliseconds/seconds
     - Number of transitions between cursors

5. **Highlighting:**
   - Highlight region between two cursors
   - Show vertical line for each cursor
   - Different colors for primary (blue) vs secondary (red)

### Testing Requirements:
1. **Unit Tests:**
   - Cursor position calculates correct timestamp
   - Delta calculation correct
   - Signal value lookup at timestamp works
   - Snap-to-transition works

2. **Integration Tests:**
   - Click places cursor
   - Hover shows cursor
   - Info panel shows correct data
   - Keyboard navigation works
   - Right-click removes cursor

### User Expectations:
- [ ] User sees a vertical line following mouse on canvas
- [ ] User sees timestamp displayed at mouse position
- [ ] User clicks to place a permanent cursor (red line)
- [ ] User sees time difference between cursors (e.g., "Δt: 2.5s")
- [ ] User sees a panel showing all signal values at cursor position
- [ ] User can right-click to remove placed cursor
- [ ] User can press arrow keys to jump cursor to next signal transition
- [ ] Region between two cursors is highlighted
- [ ] Cursors remain visible while zooming/panning
- [ ] Info panel is readable and doesn't obstruct view

---

## **STEP 6: Export & Analysis Features**

### Objective:
Add data export and basic analysis tools.

### Technical Requirements:
1. **Export Functions:**
   - Export visible waveform as PNG/SVG
   - Export filtered data as CSV
   - Export measurement data (cursors, deltas)
   - Generate report with statistics

2. **Analysis Tools:**
   - Transition counter per signal
   - State duration calculator (how long in each state)
   - Pattern finder (find all times where signal A goes high, then B goes high within X seconds)
   - Frequency analysis (average time between transitions)

3. **Components:**
   - `ExportDialog.tsx` - Export options modal
   - `AnalysisPanel.tsx` - Analysis tools sidebar
   - `StatisticsView.tsx` - Display signal statistics

4. **Pattern Matching:**
   ```typescript
   interface Pattern {
     conditions: Array<{
       signal: string;
       value: any;
       timing: { after?: string; within?: number };
     }>;
   }
   ```

5. **Statistics Display:**
   - Per signal: transition count, min/max/avg duration per state
   - Overall: busiest time periods, most active signals
   - Table and chart views

### Testing Requirements:
1. **Unit Tests:**
   - PNG export creates valid image
   - CSV export has correct format
   - Transition counting accurate
   - Duration calculations correct
   - Pattern matching finds all matches

2. **Integration Tests:**
   - Export dialog opens and works
   - Download triggers correctly
   - Analysis results display correctly
   - Pattern finder UI works

3. **Data Validation:**
   - Test pattern finder with known patterns
   - Verify statistics match manual calculations
   - Test export with various filter states

### User Expectations:
- [ ] User can click "Export" button
- [ ] User sees export options: PNG Image, SVG Image, CSV Data
- [ ] User can export current view as image (what's visible on canvas)
- [ ] User can export filtered data as CSV
- [ ] User sees "Analysis" panel with tabs: Statistics, Pattern Finder
- [ ] In Statistics tab, user sees table with: Signal | Transitions | Avg High Time | Avg Low Time
- [ ] User can click on a signal to see detailed breakdown
- [ ] In Pattern Finder, user can define: "When MOTOR_START goes true, find SENSOR_A changes within 5 seconds"
- [ ] User sees list of matching timestamps
- [ ] User can click a match to jump canvas to that time
- [ ] All exports have sensible filenames with timestamps

---

## **STEP 7: Performance Optimization & Polish**

### Objective:
Optimize for large files (10,000+ entries, 100+ signals) and add polish.

### Technical Requirements:
1. **Performance Improvements:**
   - Implement Web Worker for file parsing
   - Use virtual scrolling for signal list
   - Canvas viewport culling (only render visible signals)
   - Memoize expensive calculations
   - Implement binary search for time-based lookups

2. **Large File Handling:**
   - Streaming parser for files > 10MB
   - Progressive loading indicator
   - Memory-efficient data structures
   - Option to sample data (show every Nth entry)

3. **Polish Features:**
   - Dark mode theme
   - Keyboard shortcuts guide (? key)
   - Tooltips on all buttons
   - Responsive design (works on tablet)
   - Settings panel: theme, performance options

4. **Error Handling:**
   - Graceful handling of corrupted files
   - User-friendly error messages
   - Recovery from parsing errors
   - Browser compatibility warnings

5. **Accessibility:**
   - Keyboard navigation throughout app
   - ARIA labels on interactive elements
   - Screen reader support for data
   - High contrast mode support

### Testing Requirements:
1. **Performance Tests:**
   - Parse 10,000 entry file in < 3 seconds
   - Render 100 signals in < 500ms
   - Smooth zoom/pan with 100 signals
   - Memory usage < 200MB for typical files

2. **Load Tests:**
   - Test with various file sizes: 100KB, 1MB, 10MB, 50MB
   - Test with various signal counts: 10, 50, 100, 500
   - Test with extreme zoom levels

3. **Browser Tests:**
   - Test on Chrome, Firefox, Safari, Edge
   - Test on Windows, Mac, Linux
   - Verify responsive design on tablet

4. **Accessibility Tests:**
   - Run aXe accessibility checker
   - Test keyboard-only navigation
   - Test with screen reader

### User Expectations:
- [ ] Large files (10MB+) load without freezing browser
- [ ] User sees progress bar during parsing: "Processing: 45%"
- [ ] App remains responsive even with 500 signals
- [ ] User can toggle dark mode
- [ ] User can press ? to see keyboard shortcuts
- [ ] User sees tooltips when hovering over buttons
- [ ] App works well on tablet (responsive layout)
- [ ] User can access settings: theme, performance mode
- [ ] If file is corrupted, user sees helpful error message, not crash
- [ ] App provides helpful onboarding for first-time users
- [ ] All features work with keyboard only

---

## **Testing Strategy Summary**

### For Each Step:
1. **Write tests BEFORE implementing features** (TDD approach)
2. **Run tests after implementation** to verify
3. **Add regression tests** if bugs are found
4. **Update tests** when requirements change

### Test Commands:
```bash
npm test                    # Run all tests
npm test -- --coverage     # With coverage report
npm test -- --watch        # Watch mode during development
```

### Success Criteria:
- All unit tests pass
- Code coverage > 80%
- All user expectations checked off
- No console errors or warnings
- Performance metrics met

---
