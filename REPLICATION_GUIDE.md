# PLC Log Visualizer – Full Replication Guide

This document describes the PLC Log Visualizer codebase in enough detail for an experienced engineer to recreate every subsystem without direct access to the source. The guide is organized top–down and covers functional behaviour, module responsibilities, communication patterns, and implementation details (including data structures, algorithms, Qt widget hierarchies, and concurrency strategies).

---

## 1. Product Overview
- **Goal**: Load one or more PLC log files, parse them into structured entries, and offer rich exploration tools (statistics, tabular browsing, signal waveform visualisation, filtering, map overlays, and transition analytics).
- **Primary interface**: A desktop GUI built with PySide6 (Qt for Python).
- **Secondary tooling**: Log generators, chunked loading demos, and a reusable map viewer package.
- **Supported log dialects**: Structured formats (`plc_debug`, `plc_tab`, `csv_signal`) with automatic parser detection. Adding new dialects stays straightforward via the parser registry.
- **Performance targets**: Handle tens of thousands of log rows interactively. Parsing runs on a background thread while waveform preprocessing can hop to a process pool for large datasets.

High-level flow:
1. User drops log files into the GUI or browses for them.
2. Files are parsed sequentially on a worker thread. Per-file results and captured errors are merged.
3. Parsed entries are processed into per-signal time-series and waveform-friendly structures.
4. Visual components subscribe to a shared `ViewportState` to coordinate zoom, pan, and time range selection.
5. Users explore signals through the timing diagram, log table, interval dialog, and optional map viewer.

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
- `plc_parser.PLCDebugParser`, `plc_tab_parser.PLCTabParser`, and `csv_signal_parser.CSVSignalParser` register themselves on import. There is no default parser shipped; auto-detection depends entirely on the registered parsers’ `can_parse` implementations (or an explicit parser name).

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
    └── QVBoxLayout (margins 18, spacing 16)
        ├── FileUploadWidget
        ├── QProgressBar (hidden until parsing)
        ├── Stats container (QWidget → QVBoxLayout → StatsWidget)
        ├── Buttons container (QGridLayout, 2×2)
        │   ├── "Open Timing Diagram"
        │   ├── "Open Log Table"
        │   ├── "Open Map Viewer"
        │   └── "Plot Signal Intervals"
        └── Stretch
```

The timing diagram, log table, map viewer, and interval dialog open as separate top-level windows; the main window collects data and launches them.

### 7.2 Key Attributes
- `_current_files`, `_file_results`, `_merged_parsed_log` — track the active parse job and merged result.
- `_signal_data_list`, `_signal_data_map` — cache processed signals for reuse across secondary windows.
- `_parser_thread` — background worker handling parsing lifecycle.
- `_timing_window`, `_table_window`, `_map_viewer_window` — references that allow live updates and focus/raise behaviour.
- `stats_widget` — displays aggregated metrics and is recreated only when needed.

### 7.3 Event Flow
1. **File selection** (`_on_files_selected`): normalises paths, warns for missing files, deduplicates, hands off to `_parse_files`.
2. **Parsing kickoff** (`_parse_files`): aborts if another job is running, clears previous results, disables uploads, shows progress, clears secondary windows, and spins up `ParserThread`.
3. **Progress** (`_on_parse_progress`): converts the progress bar to determinate mode and shows `Parsing i/n file(s) - filename`.
4. **Completion** (`_on_parse_finished`):
   - Merges results, updates stats, and builds `SignalData`.
   - Refreshes timing diagram, log table, and map viewer windows if already open.
   - Updates upload widget status (e.g., `✓ Loaded 3 of 3 file(s) with 2 error(s)`), re-enables uploads, and toggles navigation buttons based on whether data exists.
   - Emits warnings for partial failures or high error counts.
5. **Errors** (`_on_parse_error`): hides progress, re-enables uploads, shows a critical dialog, resets status text, and disposes the worker thread.
6. **Navigation buttons**: `Timing Diagram`, `Log Table`, and `Plot Signal Intervals` remain disabled until successful parsing; the map viewer can always open (it will prompt for map files if needed).

### 7.4 Wayland Handling
`_show_window` (defined in `main.py`) applies Wayland-safe sizing by setting relaxed maximums after the first event loop tick. `MainWindow.resizeEvent` logs geometry when running under Wayland to help debug compositor quirks.

---

## 8. UI Component Catalogue

### 8.1 FileUploadWidget
- Drop-zone `QFrame` with emoji label plus a “Browse for Files” button.
- Accepts drag-and-drop, filters duplicates, emits `files_selected(list[str])`, and exposes `set_status(text)` for progress/success/error feedback.

### 8.2 StatsWidget
- Displays entry/device/signal counts, overall time range, and error totals.
- Shows detailed error lines in a yellow panel when parse errors occur.
- Methods: `update_stats(ParseResult)` and `clear()`.

### 8.3 TimingDiagramWindow
- Split view (`QSplitter`) hosting `SignalFilterWidget` (left) and waveform stack (right).
- Instantiates `ViewportState`, `ZoomControls`, `WaveformView`, `PanControls`, and `TimeRangeSelector`.
- `set_data(parsed_log, signal_data)` loads waveforms, populates filters, enables controls, and initialises a 10-second starting window (clamped to log length).
- Exposes `viewport_state` for cross-window coordination (map viewer syncs to its `time_range_changed` signal).

### 8.4 SignalFilterWidget
- Debounced search (with `/regex` support), Boolean/String/Integer toggles, “show only signals with changes”, preset save/load, Select All / Deselect All buttons, and tri-state device tree.
- Status label reports visible counts; the filter is disabled until signals are loaded.
- Emits `visible_signals_changed` and `plot_intervals_requested`.

### 8.5 WaveformView & Scene
- `WaveformView` (QGraphicsView) enables antialiasing, pins the time axis, and maps wheel gestures to zoom commands (forwarded as `wheel_zoom` to the viewport).
- `WaveformScene` tracks signal rows, label column, time axis, grid lines, and transition markers.
  - Layout constants: 180 px label width, 60 px per signal row, 30 px time axis height.
  - Supports `set_data`, `set_visible_signals`, `set_time_range`, and `refresh_layout`.
- Renderers: `BooleanRenderer` (square waves) and `StateRenderer` (labelled spans). Both use `BaseRenderer.clip_states` to trim data to the visible window.
- `TransitionMarkerItem` and `GridLinesItem` provide markers and adaptive grid spacing.

### 8.6 LogTableWindow & DataTableWidget
- `LogTableWindow` reuses `SignalFilterWidget` and forwards filter changes to the table.
- `DataTableWidget` combines `CopyPasteTableView` with `LogDataModel` columns (Device, Signal, Timestamp `%H:%M:%S`, Value, Type) and a row-count label (e.g., “125 of 450 entries”).
- `filter_signals` matches `device::signal` keys and updates the count label (`0 of N` when nothing is selected).

### 8.7 IntegratedMapViewer
- Wraps `tools/map_viewer` components (`MapParser`, `MapRenderer`, `UnitStateModel`, `MediaControls`).
- Loads XML maps, YAML mapping/color policies, and links `SignalData` to unit IDs.
- Playback controls allow play/pause, speed adjustments, seeks, and manual time input. `update_time_position` lets the map follow the waveform’s visible start time.

### 8.8 ViewportState
- QObject that centralises the full time range, visible window, zoom level, and visible duration.
- Signals: `time_range_changed(start, end)` and `duration_changed(seconds)` keep controls and views synchronised.
- Methods include `set_full_time_range`, `set_time_range`, `set_visible_duration`, `zoom_in/out`, `reset_zoom`, `pan`, and `jump_to_time`. Duration clamps prevent extreme zoom.

### 8.9 SignalIntervalDialog
- Generates duration analytics for a single signal’s transitions.
- Renders a bar chart (`IntervalPlotWidget`) and table (change index, timestamps, value transitions, durations).
- Detects when a signal lacks transitions and responds with a friendly info dialog instead of an empty plot.

---

## 9. Background Processing & Thread Safety

- Parsing happens on `ParserThread`; the GUI stays responsive.
- Large waveform preprocessing may run in a subprocess pool. Because Qt GUI elements (PySide6) cannot be touched off the main thread, all signals emitted by `ParserThread` deliver plain Python objects (`ParseResult`, dicts, lists), and the UI rebuilds the scene on the main thread.
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
- Existing coverage is light: `plc_visualizer/tests/test_viewport_state.py` exercises zoom/pan math, while `scripts/test_chunked_loading.py` and `test_chunked_loading_quick.py` act as executable smoke tests for streaming. Additional parser/UI tests are future work.
- Suggested coverage areas:
  - Parser regexes handle both valid and malformed lines.
  - Type inference and timestamp parsing.
  - Merge utilities combine logs accurately.
  - Viewport state transitions (zoom, pan, jump, clamping).
  - Signal processing yields correct state durations.
  - UI-level tests (with pytest-qt) verify filter interactions, window launches, and map viewer integration.

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
   - Concrete parsers with regex/CSV patterns (`plc_parser.py`, `plc_tab_parser.py`, `csv_signal_parser.py`).
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

By following this guide, a developer can reimplement the PLC Log Visualizer’s capabilities—including parsing, real-time waveform rendering, interactive filtering, and analytics—without direct access to the original source. The architecture emphasises modularity: parsers are pluggable, signal processing is reusable outside the GUI, and each UI component exposes clear responsibilities with Qt (PySide6) signals/slots for integration.
