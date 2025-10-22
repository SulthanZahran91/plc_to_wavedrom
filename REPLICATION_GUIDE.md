# PLC Log Visualizer – Full Replication Guide

This document describes the PLC Log Visualizer codebase in enough detail for an experienced engineer to recreate every subsystem without direct access to the source. The guide is organized top–down and covers functional behaviour, module responsibilities, communication patterns, and implementation details (including data structures, algorithms, Qt widget hierarchies, and concurrency strategies).

---

## 1. Product Overview
- **Goal**: Load one or more PLC log files, parse them into structured entries, and offer rich exploration tools (statistics, tabular browsing, signal waveform visualisation, filtering, and transition analytics).
- **Primary interface**: A desktop GUI built with PyQt6.
- **Secondary tooling**: Log generators for testing and sample data.
- **Supported log dialects**: Two structured formats (`plc_debug` and `plc_tab`), with automatic parser detection. Adding new dialects should be straightforward via the parser registry.
- **Performance targets**: Handle tens of thousands of log rows interactively. Parsing and waveform preprocessing are offloaded to background threads/processes to keep the UI responsive.

High-level flow:
1. User drops log files into the GUI or browses for them.
2. Files are parsed concurrently. Per-file results and captured errors are merged.
3. Parsed entries are processed into per-signal time-series and waveform-friendly structures.
4. Visual components subscribe to a shared viewport state to coordinate zoom, pan, and time range selection.
5. Users filter signals, inspect tabular data, open transition interval plots, and reorder waveform rows via drag-and-drop.

---

## 2. Environment & Dependencies
To rebuild the project, match the following environment:

| Dependency      | Purpose                                               | Notes                                              |
|-----------------|-------------------------------------------------------|----------------------------------------------------|
| Python ≥ 3.10   | Language runtime                                      | Uses typing features such as `list[str]`, `|`      |
| PySide6 ≥ 6.6   | GUI toolkit                                           | Widgets, events, QGraphicsScene rendering          |
| parse ≥ 1.20    | Optional templated parsing support                    | Only needed if a parser subclass uses parse templates |
|                 |                                                       |                                                    |
| pytest, pytest-qt | Automated testing                                   | Optional when reimplementing                       |

Recommended project scaffolding:
- Package root `plc_visualizer` (Python package).
- Entry script `main.py` that boots the Qt app.
- CLI tools (optional) can live under `python -m plc_visualizer.scripts.<name>`.

---

## 3. Core Data Model

### 3.1 Enumerations & Types
`SignalType` is an `Enum` with values `BOOLEAN`, `STRING`, `INTEGER`. The system assumes these for rendering choices. (The base parser also supports an optional FLOAT type if future needs arise.)

### 3.2 Structured Records
- **`LogEntry`**
  - Fields: `device_id`, `signal_name`, `timestamp` (`datetime`), `value` (`bool | str | int`), `signal_type`.
  - `__repr__` returns a concise debug string.
- **`ParsedLog`**
  - Fields: `entries` (list of `LogEntry`), `signals` (set of `device_id::signal_name`), `devices` (set of device IDs), `time_range` (tuple `(start_dt, end_dt)`).
  - `__post_init__` populates `signals`, `devices`, and `time_range` if missing.
  - Computed properties: `entry_count`, `signal_count`, `device_count`.
- **`ParseError`**
  - Fields: `line`, `content`, `reason`, `file_path` (optional). Allows linking errors to files.
- **`ParseResult`**
  - Fields: `data` (`ParsedLog | None`), `errors` (list of `ParseError`).
  - Convenience properties: `success`, `has_errors`, `error_count`.

### 3.3 Signal Post-Processing Structures
- **`SignalState`**: `start_time`, `end_time`, `value`; computed duration property.
- **`SignalData`**: bundles `name`, `device_id`, fully qualified `key`, `signal_type`, the original `entries`, and precomputed `states`.
  - `has_transitions` indicates multiple distinct states.
  - `display_label` returns `"DEVICE -> SIGNAL"`.

---

## 4. Parsing Architecture

### 4.1 Parser Registry
- Singleton `ParserRegistry` maintains a dictionary `{name: parser_instance}` plus an optional default parser.
- Key methods:
  - `register(parser, is_default=False)`
  - `detect_parser(file_path)` iterates registered parsers, calling `can_parse`. First positive match wins; fallback to default parser if detection fails.
  - `parse(file_path, parser_name=None, num_workers=0)` chooses a parser (auto or explicit) and returns `ParseResult`.
  - `get_parser_names()` returns registered names, used by tooling (e.g., sample log generator).
- `plc_parser.PLCDebugParser` and `plc_tab_parser.PLCTabParser` register themselves on import. There is no “default” parser shipped in this branch; auto-detection depends entirely on the two specialised parsers.

### 4.2 `GenericTemplateLogParser` Base Class
All concrete parsers inherit from this class, which provides:
- Configurable class attributes:
  - `LINE_RE`: compiled regex with named groups (preferred for speed).
  - `TEMPLATE`: fallback Parse module template string (unused in current subclasses).
  - `TYPE_MAP`: maps dtype tokens to `SignalType`.
  - `TIMESTAMP_FORMAT`: `%Y-%m-%d %H:%M:%S.%f` by default with a custom `_fast_ts` for speed.
  - `DEVICE_ID_REGEX`: identifies device IDs inside the “path” portion, defaulting to `[A-Za-z0-9_-]+-\d+`.
  - Batch/IO tunables: `BUFFER_SIZE`, `BATCH_SIZE`, `LINES_PER_BATCH`.
  - Behaviour toggles: `INFER_TYPES` (auto-detect ints/bools), `USE_CHRONO_DETECTION` (skip sort when input is already chronological).
- Parsing paths:
  1. **Single-threaded** (`_parse_single`):
     - Streams file line-by-line.
     - Uses `_parse_line_hot` to interpret (regex or parse template).
     - Batches unique signal/device strings before updating sets to reduce churn.
     - Tracks timestamp monotonicity; sorts at the end if out-of-order entries detected.
  2. **Concurrent** (`_parse_concurrent`):
     - Splits file into batches of `LINES_PER_BATCH`.
     - Dispatches `_parse_lines_batch` to either `ThreadPoolExecutor` or `ProcessPoolExecutor`.
     - Workers return lightweight tuples `(device_id, signal_name, ts_str, value, signal_type)` plus aggregated sets/errors to minimize pickling overhead.
     - Parent process converts timestamp strings to `datetime` (using `_fast_ts` when possible) and merges results.
  3. **Streaming** (`parse_streaming`) yields `LogEntry` objects sequentially without materializing the full list.
- `can_parse(file_path)` peeks at up to five non-empty lines and checks them against `LINE_RE` or `TEMPLATE`. Requires ≥60% match to return `True`.
- Utility helpers handle type inference (`_infer_type_fast`), numeric parsing with base detection, boolean normalisation, and timestamp parsing.

### 4.3 Concrete Parsers
1. **`PLCDebugParser` (`name="plc_debug"`):**
   - Regex matches lines such as
     ```
     2025-09-22 13:00:00.199 [Debug] [/AreaA/Line01/Robot-01@Main] [INPUT2:I_MOVE_IN] (Boolean) : ON
     ```
   - Captures `ts`, `path`, `signal` (`category:signal`), `dtype`, and `value`.
   - Device ID extracted from path via default regex. Signal key becomes `DEVICE@unit::SIGNAL`.
2. **`PLCTabParser` (`name="plc_tab"`):**
   - Targets tab-delimited lines:
     ```
     2025-09-22 14:05:00.500 [] CellB/Assembly/Robot-02@Backup    OUTPUT1:CLAMP_ENGAGED    OUT    ON ...
     ```
   - Recognises optional direction/location fields; dtype inferred from `(dtype)` token or raw value.
   - Custom device regex `([A-Za-z0-9_-]+)(?:@[^\]]+)?$` (allows device IDs without numeric suffix).

### 4.4 Error Handling & Merging
- `_parse_line_hot` raises `ValueError` for unmatched lines, invalid timestamps, unknown types, or missing device IDs. The caller wraps errors into `ParseError` (line number + reason).
- `utils.merge.merge_parse_results` accepts `{file_path: ParseResult}`:
  - Aggregates successful `ParsedLog` objects via `merge_parsed_logs` (concatenates entries, unions signals/devices, recalculates overall time range).
  - Rewrites error entries to ensure `file_path` is populated.
  - Returns a single `ParseResult` with merged data and combined errors.

### 4.5 Background Thread & Multiprocessing
- GUI parsing is delegated to `ParserThread` (subclass of `QThread`):
  - Iterates provided file paths, calling `parser_registry.parse`.
  - Emits signals:
    - `progress(current_index, total, file_path)`
    - `finished(aggregated_result, per_file_results, signal_data_list)`
    - `error(message)`
  - For large datasets (`entry_count >= 10_000`), waveform preprocessing (`process_signals_for_waveform`) is offloaded to a shared `ProcessPoolExecutor` (spawn context when available). A class-level `shutdown_executor` is registered with `atexit`.

---

## 5. Signal Processing Pipeline

1. **Grouping**: `group_by_signal(parsed_log)` returns a dictionary keyed by `(device_id, signal_name)` with chronological `LogEntry` lists. Ensures per-signal entries are sorted.
2. **State Extraction**: `calculate_signal_states(entries, time_range)` iterates sorted entries and produces contiguous `SignalState` spans from each timestamp to the next (or to `ParsedLog.time_range[1]` for the last entry).
3. **Packaging**: `process_signals_for_waveform(parsed_log)` wraps the above, yielding a sorted list of `SignalData` objects. Sorting is by `(device_id, signal_name)` for consistent display order.
4. **Transition Detection**: Later, the UI renderers call `BaseRenderer.clip_states` to clip states to the visible time window while preserving continuity at boundaries. This clipped list drives drawing and transition marker creation.

---

## 6. Application Entry Point

### 6.1 `main.py`
```python
app = QApplication(sys.argv)
app.setApplicationName("PLC Log Visualizer")
window = MainWindow()
_show_window(window, app)
sys.exit(app.exec())
```
`_show_window` works around Wayland quirks by showing the window normally, then applying a “relaxed” maximum size on the next event loop tick. On X11/Windows, it simply calls `showMaximized()`.

---

## 7. MainWindow Layout & Responsibilities

### 7.1 Overall Composition
```
QMainWindow
└── QWidget (central)
    └── QVBoxLayout
        ├── FileUploadWidget
        ├── QProgressBar (hidden until parsing)
        ├── QSplitter (horizontal)
        │   ├── Left Panel (QVBoxLayout)
        │   │   ├── StatsWidget (within a holder container for easy recreation)
        │   │   └── SignalFilterWidget
        │   └── Right Panel QSplitter (vertical)
        │       ├── Waveform Container (QVBoxLayout)
        │       │   ├── ZoomControls
        │       │   ├── WaveformView (QGraphicsView)
        │       │   ├── PanControls
        │       │   └── TimeRangeSelector
        │       └── DataTableWidget
        └── Bottom Action Bar (Load New File button aligned left)
```

### 7.2 Key Attributes
- Current file list, merged `ParsedLog`, mapping of `signal_key -> SignalData`, and the list of visible signals.
- Shared `ViewportState` instance coordinating zoom/pan among waveform, controls, and selectors.
- Parser thread instance reference for lifecycle management.
- Stats widget holder references (`_stats_holder`, `_stats_holder_layout`) to survive deletion/recreation when the widget is destroyed.

### 7.3 Event Flow
1. **File selection** (`_on_files_selected`):
   - Validates paths, warns about missing files, deduplicates, stores `_current_files`, and calls `_parse_files`.
2. **Parsing kickoff** (`_parse_files`):
   - Blocks parallel parsing if a job is in progress.
   - Resets UI: clears previous results, disables upload widget, shows progress bar, resets waveform/table/filter.
   - Disconnects previous viewport signals to avoid duplicate slots.
   - Starts `ParserThread`, connecting to `finished`, `progress`, `error`.
3. **Parsing progress**:
   - Updates progress bar label with `Parsing i/n file(s) – filename`.
4. **Parsing completion** (`_on_parse_finished`):
   - Hides progress bar, re-enables upload widget, stores per-file results.
   - Populates waveform view, data table, and filter with processed signal data.
   - Configures `ViewportState`:
     - `set_full_time_range(start, end)`
     - Initial zoom to the first 10 seconds (clamped to end).
     - Connects `time_range_changed` and `zoom_level_changed` to UI controls.
   - Updates status text and displays warnings for partial failures.
   - Shows “Load New File” button.
5. **Error states** (`_on_parse_error`, parse failure path):
   - Resets UI, shows a QMessageBox with the failure reason, ensures thread is cleaned up.
6. **Load New File**:
   - Resets all UI elements and disables navigation controls.
7. **Viewport updates**:
   - Zoom buttons, slider, mouse wheel, and `TimeRangeSelector` feed the shared `ViewportState`.
   - `time_range_changed` updates the waveform scene (`set_time_range`), `TimeRangeSelector`, and `PanControls` scroll bar.
   - `PanControls` jump-to-time and scrollbar use `ViewportState.jump_to_time` / `set_time_range`.
8. **Signal filtering**:
   - `SignalFilterWidget.visible_signals_changed` triggers waveform visibility updates and table filtering.
9. **Interval plotting**:
   - When the filter widget emits `plot_intervals_requested`, the window opens `SignalIntervalDialog` for the selected signal.

### 7.4 Wayland Handling
`resizeEvent` logs geometry details when running on Wayland for debugging. `_show_window` sets minimum size (960×720) and clamps the maximum to 10–12% margins within the available screen geometry.

---

## 8. UI Component Catalogue

### 8.1 FileUploadWidget
- Composition:
  - `QFrame` drop zone with dashed border and emoji label.
  - “Browse for Files” button.
- Features:
  - Accepts drag-and-drop of files (`QDragEnterEvent`, `QDropEvent`).
  - Filters URLs to valid files only.
  - Emits `files_selected` (list of absolute paths).
  - `set_status(text)` changes the central label (used for feedback: e.g., “Parsing…”).

### 8.2 StatsWidget
- Displays aggregated statistics:
  - Entry count, unique devices, unique signals, time range, error count.
  - If errors exist, shows a yellow `QTextEdit` with per-error details (`[filename] Line N: reason`).
- Styling emphasises success vs. failure (green vs. red fonts).
- Public methods: `update_stats(ParseResult)` and `clear()`.
- Needs to survive recreation, hence MainWindow stores the surrounding holder widget and reinstantiates the widget to avoid stale references when Qt destroys it.

### 8.3 DataTableWidget
- Wrapper around a custom `QAbstractTableModel` (`LogDataModel`) and a `CopyPasteTableView`.
- Columns: Device ID, Signal Name, Timestamp (formatted `%H:%M:%S`), Value, Type.
- Row count label shows totals and filtered counts (e.g., “125 of 450 entries”).
- `filter_signals(signal_keys)` retains only entries with matching `device::signal` keys. Empty selection → “0 of N entries”.
- `CopyPasteTableView` enables Ctrl+C copies, tab-separated rows, and a context menu. Paste functionality is intentionally disabled.

### 8.4 SignalFilterWidget
- Purpose: Let users search, filter, and select which signals appear in the waveform and table.
- State:
  - `SignalInfo` objects (immutable dataclass) derived from `SignalData`.
  - Search string with debounce (200 ms).
  - Type filters (Boolean/String/Integer via checkboxes).
  - Toggle for “Show only signals with changes”.
  - Preset management (save/load via `QComboBox` + `QInputDialog`).
  - Device tree: top-level items per device, child items per signal with tri-state selection.
  - Selected signals tracked as a set of keys; `visible_signals_changed` emits only those both filtered in and selected.
- Buttons:
  - Select All / Deselect All (affect current filtered subset).
  - Clear Filters resets to default (all signals selected, no search, all types visible).
  - Plot Change Intervals (enabled only when exactly one signal is selected; emits `plot_intervals_requested(key)`).
- Tree-building occurs lazily on first `showEvent` to avoid expensive UI work while hidden.

### 8.5 WaveformView & Scene

**WaveformView (QGraphicsView)**
- Holds a `WaveformScene`. Enables antialiasing and smooth transforms.
- Disables scrollbars when possible and pins the transformation anchor under the mouse.
- Overrides:
  - `resizeEvent` to update scene width and re-pin the time axis.
  - `scrollContentsBy` to keep the time axis fixed while scrolling vertically.
  - `wheelEvent` to map Ctrl+wheel to zoom (emits `wheel_zoom` delta).
- `set_data(parsed_log, signal_data_list)` resets the view, ensures the time axis is visible, and positions the scene at the top-left.

**WaveformScene (QGraphicsScene)**
- Dimensions: `LABEL_WIDTH` (180 px) for labels, `SIGNAL_HEIGHT` (60 px per track), `TIME_AXIS_HEIGHT` (30 px).
- Maintains:
  - `signal_data_map` (`key -> SignalData`).
  - `visible_signal_names` (ordered list).
  - Graphics items:
    - `GridLinesItem` (dotted vertical lines).
    - `TimeAxisItem` (top row with ticks and labels).
    - For each signal: a `SignalRowItem` containing a `SignalLabelItem` and a `SignalItem`.
- `set_visible_signals` rebuilds the scene using only selected keys, preserving order across rebuilds by intersecting with `all_signal_names`.
- `update_width` adjusts scene rects, grid lines, time axis width, and each signal’s waveform width.
- `set_time_range(start, end)` forwards the new visible span to the time axis, grid, and every `SignalItem`.
- Drag-and-drop: `SignalRowItem` is `ItemIsMovable`. On drop, the scene reorders `visible_signal_names` according to item Y positions, allowing users to re-stack waveform rows.

**Rendering details**
- `SignalLabelItem` paints a light-grey panel with device name (bold) and signal name.
- `SignalItem` renders waveform content:
  - Chooses a renderer based on `SignalType`.
  - Ensures clipping within its bounding rect.
  - Recreates QPainterPath objects when the time range or width changes.
  - Generates `TransitionMarkerItem` vertical lines where values change; tooltips show timestamp and value transition, clicking toggles highlight.
- Renderers:
  - `BooleanRenderer`: Draws square waves with high/low states, fills high regions with translucent green.
  - `StateRenderer`: Draws labeled boxes spanning each state (strings, integers).
  - Both rely on `BaseRenderer` helpers for time-to-x conversion, pen/brush creation, and state clipping at the viewport boundaries.

### 8.6 ZoomControls
- Widgets: “−” button, slider (logarithmic scale 1× – 1000×), “+” button, clickable label showing the current zoom (allows manual entry), and “Reset” button.
- Signals: `zoom_in_clicked`, `zoom_out_clicked`, `reset_zoom_clicked`, `zoom_level_changed`.
- `set_zoom_level(zoom)` updates slider position and button enabled state; uses logarithmic mapping to convert zoom levels to slider ticks.

### 8.7 PanControls
- Components: left/right arrow buttons, horizontal scrollbar (0–1000), time input (`HH:MM[:SS]`), “Go” button.
- Signals:
  - `pan_left_clicked`, `pan_right_clicked`.
  - `jump_to_time(datetime)` emitted when the user enters a valid time.
  - `scroll_changed(float_fraction)`.
- `set_scroll_position(position, visible_fraction)` adjusts scrollbar value and page step (so the thumb size roughly matches the visible percentage of the timeline).
- `set_time_range(start, end)` stores bounds and updates tooltips.

### 8.8 TimeRangeSelector
- Custom QWidget showing the full log time span as a bar with a highlighted sub-range.
- Interaction:
  - Drag left/right handles to adjust start/end.
  - Drag within the highlighted area to pan the window.
- Emits `time_range_changed(start_datetime, end_datetime)` whenever selection changes.
- Maintains consistent constraints (cannot invert start/end, clamps to overall range).

### 8.9 ViewportState
- QObject managing the canonical visible time window and zoom level.
- Holds:
  - `_full_start`, `_full_end`.
  - `_visible_start`, `_visible_end`.
  - `_zoom_level` (float).
- Signals: `time_range_changed(start, end)`, `zoom_level_changed(level)`.
- Methods:
  - `set_full_time_range(start, end)` resets zoom to 1×.
  - `set_time_range(start, end)` clamps to full range and emits both signals.
  - `zoom_in/out(factor)`, `set_zoom_level(zoom)`, `reset_zoom()`.
  - `pan(delta_seconds)` shifts the window.
  - `jump_to_time(target)` centers the view around the target.
- Ensures zoom boundaries between `min_zoom = 1.0` and `max_zoom = 1000.0`.

### 8.10 SignalIntervalDialog
- Opens when a single signal is selected for interval plotting.
- Steps:
  1. Converts consecutive `SignalState` pairs into `IntervalPoint` entries.
  2. Displays an `IntervalPlotWidget` bar chart (duration vs. change index).
  3. Shows a table listing change index, from/to values, timestamp, and duration (seconds).
- Provides user feedback if the signal lacks transitions (handled in MainWindow before instantiation).

---

## 9. Background Processing & Thread Safety

- Parsing happens on `ParserThread`; the GUI stays responsive.
- Large waveform preprocessing may run in a subprocess pool. Because PyQt GUI elements cannot be touched off the main thread, all signals emitted by `ParserThread` deliver plain Python objects (`ParseResult`, dicts, lists), and the UI rebuilds the scene on the main thread.
- String interning (`sys.intern`) in the parser reduces memory churn for repeated device/signal names.
- Batch size constants and `LINES_PER_BATCH` can be tuned depending on log size and hardware.
- The process pool is a singleton per class (`ParserThread._executor`) to avoid repeated initialization cost.

---

## 10. Error & Status Feedback

- **Missing files**: Immediately warn via `QMessageBox.warning`.
- **Parsing errors**:
  - Per-file errors aggregated in `StatsWidget`.
  - Critical failure (no successes) triggers a red `QMessageBox.critical`.
  - Partial successes (some errors or failed files) pop a warning message listing failed filenames.
- **Progress**: Indeterminate bar at start switches to determinate range once the number of files is known.
- **Status texts**: File upload label shows plain English summary (e.g., `✓ Loaded 2 of 3 file(s) with 4 error(s)`).

---

## 11. Auxiliary Tooling

### 11.1 Random Log Generator (`generate_random_log.py`)
- Capabilities:
  - Generate logs for individual parser formats or bulk output of ~30 MB per parser.
  - Encapsulates `StructuredSignal` definitions, random value generators, timestamp formatting, and CLI arguments (signals count, line count, output paths).
  - Example CLI usage:
    ```
    python generate_random_log.py --parser plc_debug --lines 5000 --out logs/debug.log
    ```
  - Bulk mode writes multiple files per registered parser, using `ParserRegistry.get_parser_names()` to stay in sync.

### 11.2 Sample Log Script (`scripts/generate_sample_logs.py`)
- Generates canonical small log files for each known parser.
- Usage:
  ```
  python -m plc_visualizer.scripts.generate_sample_logs --output-dir sample_logs/generated
  ```
- When executed, it prints which parsers were covered and which lacked generator functions.

### 11.3 Sample Data Directory
- `sample_logs/plc_debug_parser.log` and `sample_logs/plc_tab_parser.log` showcase expected formats for testing or demo purposes.

---

## 12. Testing Strategy

- Tests rely on `pytest` and `pytest-qt`.
- Existing suite is light (notably `tests/test_viewport_state.py` and an older parser test referencing a deprecated `DefaultParser`). Reimplementation can modernise the tests to align with the two active parsers.
- Suggested coverage areas:
  - Parser regexes handle both valid and malformed lines.
  - Type inference and timestamp parsing.
  - Merge utilities combine logs accurately.
  - Viewport state transitions (zoom, pan, jump, clamping).
  - Signal processing yields correct state durations.
  - UI-level tests (with pytest-qt) can verify signal emissions when filters are toggled.

---

## 13. Extending the System

### 13.1 Adding New Parsers
1. Create a subclass of `GenericTemplateLogParser`.
2. Define `name`, `LINE_RE` (or `TEMPLATE`), and optional overrides (timestamp format, device regex).
3. Add any parser-specific logic (e.g., field normalization) inside `_parse_line_hot` by overriding it or by pre-processing the regex dict before calling the base implementation.
4. Register the parser:
   ```python
   from .parser_registry import parser_registry
   parser_registry.register(MyNewParser(), is_default=False)
   ```
5. Provide log generators (optional) and update sample scripts/tests.

### 13.2 Headless/CLI Mode (Future)
- Not currently implemented but feasible by reusing the parser registry and signal processing utilities:
  - Accept file paths via CLI.
  - Call `parser_registry.parse` for each file.
  - Use `merge_parse_results` and `process_signals_for_waveform`.
  - Emit summary statistics in JSON/YAML (counts, time range, per-signal states).
  - Could live under `python -m plc_visualizer.cli` once built.

### 13.3 GUI Enhancements
- Because the waveform relies on QGraphicsScene/QGraphicsView, additional features (e.g., zooming via rubber-band selection, exporting images) can be implemented by adding new tools to `WaveformView`.
- Drag-and-drop reordering is already in place through `SignalRowItem`. Persisting the order would require saving the sequence of `visible_signal_names` and reapplying it when filters change.

---

## 14. Replication Checklist
Follow this checklist to recreate the project from scratch:

1. **Project scaffolding**
   - Create `plc_visualizer` package with subpackages `models`, `parsers`, `ui`, `utils`, `tests`, `scripts`.
   - Add `pyproject.toml` or `setup.cfg` declaring dependencies above.
2. **Define core models** (`models/data_types.py`)
   - Implement `SignalType`, `LogEntry`, `ParsedLog`, `ParseError`, `ParseResult`.
3. **Build utilities**
   - `utils/waveform_data.py` with grouping/state functions.
   - `utils/merge.py` for parse result aggregation.
   - `utils/viewport_state.py` for zoom/pan management.
4. **Implement parser infrastructure**
   - `parsers/base_parser.py` with `BaseParser` + `GenericTemplateLogParser`.
   - `parsers/parser_registry.py` (singleton).
   - Concrete parsers with regex patterns (`plc_parser.py`, `plc_tab_parser.py`).
5. **Create signal processing threads**
   - `ParserThread` inside `ui/main_window.py`, including process pool offload.
6. **Construct UI components**
   - `FileUploadWidget`, `StatsWidget`, `DataTableWidget` (+ model + `CopyPasteTableView`).
   - Filtering controls (`SignalFilterWidget`).
   - Waveform rendering stack (`WaveformView`, `WaveformScene`, `SignalRowItem`, `SignalItem`, renderers, label/time/grid items, transition markers).
   - Navigation widgets (`ZoomControls`, `PanControls`, `TimeRangeSelector`, `ClickableLabel`).
   - Interval dialog (`signal_interval_dialog.py`).
7. **Assemble MainWindow**
   - Layout described in section 7, with signal-slot wiring for all interactions.
   - Manage viewport state connections and cleanup (`_finalize_parser_thread`, stats widget recreation).
8. **Entry point**
   - `main.py` to instantiate QApplication and show MainWindow (Wayland-safe).
9. **Support scripts**
   - Random log generator and sample log script for developer convenience.
10. **Optional tests**
    - Port or write new pytest suites exercising parsers and utilities.

---

## 15. Operational Notes
- The GUI expects log files encoded in UTF-8 (with BOM tolerated). Other encodings require extension.
- Very large logs (≥10k entries) trigger process-based signal processing; ensure the platform allows multiprocessing via “spawn” context (provided by Python on Windows/macOS; Linux default is “fork” but code falls back gracefully).
- When running on Wayland, the window size logic avoids the traditional `showMaximized()` call to prevent blank surfaces; ensure similar handling if targeting other compositors.
- The waveform scene clears existing QGraphicsItems and repopulates them frequently (on filter changes, zoom updates). Keep rendering lightweight and reuse objects where possible if extending functionality.

---

By following this guide, a developer can reimplement the PLC Log Visualizer’s capabilities—including parsing, real-time waveform rendering, interactive filtering, and analytics—without direct access to the original source. The architecture emphasises modularity: parsers are pluggable, signal processing is reusable outside the GUI, and each UI component exposes clear responsibilities with PyQt signals/slots for integration.
