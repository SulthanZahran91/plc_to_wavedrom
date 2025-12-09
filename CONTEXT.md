# Context: PLC Log Visualizer

## System Overview
The **PLC Log Visualizer** is a high-performance desktop application for analyzing and visualizing industrial PLC logs. It is built with **PySide6** for the UI and leverages **Python's multiprocessing** and **array** modules for efficient data handling. The system is designed to handle large log files (gigabyte-scale) through chunking and lazy loading.

## Architecture Map
Data flows from the entry point through parsing to the UI as follows:

1.  **Entry:** `main.py` initializes `MainWindow` and handles platform-specific (Wayland) window sizing.
2.  **Orchestration:** `MainWindow` delegates logic to `SessionManager` (`app/session_manager.py`), which manages the application state.
3.  **Parsing:** `SessionManager` spawns a `ParserThread`, which uses `ParserRegistry` (`parsers/parser_registry.py`) to select the correct parser.
4.  **Processing:** Parsers (e.g., `PLCDebugParser`) parse logs using regex fast-paths or templates and produce `ParsedLog` objects.
5.  **Storage:** Data is stored in `ChunkedParsedLog` (`models/chunked_log.py`), managed by `ChunkManager` (`utils/chunk_manager.py`) to load time-windows on demand.
6.  **Visualization:**
    *   **Waveform:** `WaveformView` renders signals using `WaveformScene` and `SignalItem`.
    *   **Map:** `MapViewer` renders a spatial view of the system based on XML/YAML configuration.
    *   **Validation:** `SignalValidator` checks signal patterns against defined rules.

## Key File Breakdown

### `app/`
*   **`session_manager.py`**: Central coordinator. Manages parsing threads, bookmarks, and synchronizes time across views (`sync_all_views`).

### `models/`
*   **`data_types.py`**: Core structures: `LogEntry`, `ParsedLog`, `SignalType`.
*   **`chunked_log.py`**: `ChunkedParsedLog` for memory-efficient storage (LRU cache of `TimeChunk`s).
*   **`bookmark.py`**: Manages user bookmarks.

### `parsers/`
*   **`parser_registry.py`**: Singleton registry for auto-detecting parsers.
*   **`base_parser.py`**: `GenericTemplateLogParser` with regex fast-paths (`_fast_ts`, `_parse_line_hot`).
*   **`plc_parser.py`**: `PLCDebugParser` implementation with an "ultra-fast" bracket-delimited parser (`_fast_parse_line`).
*   **`plc_tab_parser.py`**, **`csv_signal_parser.py`**: Specialized parsers for other formats.

### `ui/`
*   **`main_window.py`**: Primary UI container. Uses `SplitPaneManager`.
*   **`theme.py`**: Defines application styles (colors, fonts).
*   **`components/`**:
    *   **`split_pane_manager.py`**: Manages flexible tabbed/split layouts.
    *   **`signal_filter_widget.py`**: Complex filtering logic (regex, presets, "show changed").
    *   **`waveform/`**:
        *   **`waveform_view.py`**: Container for the scene.
        *   **`waveform_scene.py`**: Manages `SignalItem`s and `TimeAxisItem`. Supports chunked reloading.
        *   **`signal_item.py`**: Renders waveforms using `BooleanRenderer` or `StateRenderer`.
        *   **`time_axis_item.py`**, **`grid_lines_item.py`**: Visual guides.
        *   **`zoom_controls.py`**, **`pan_controls.py`**: Navigation widgets.
*   **`windows/`**:
    *   **`timing_window.py`**: Embeddable view for waveforms.
    *   **`log_table_window.py`**: Tabular view of logs.
    *   **`map_viewer_window.py`**: Container for the Map Viewer tool.
*   **`dialogs/`**: `bookmark_dialog.py`, `help_dialog.py`.

### `utils/`
*   **`chunk_manager.py`**: Connects `ChunkedParsedLog` to parsers for on-demand loading.
*   **`waveform_data.py`**: `SignalData` structure for visualization (lazy state computation).
*   **`merge.py`**: Logic to combine multiple parsed logs.

### `validation/`
*   **`validator.py`**: `SignalValidator` orchestrates validation rules.
*   **`rule_loader.py`**: Loads rules from YAML.
*   **`pattern_validators/`**: Contains specific validators like `SequenceValidator`.

### `tools/map_viewer/`
*   **`renderer.py`**: `MapRenderer` (QGraphicsView) for visualizing system layout.
*   **`config.py`**: Loads mapping rules from `mappings_and_rules.yaml`.
*   **`playback_demo.py`**: Standalone demo for the map viewer.

### `services/`
*   **`analytics/`**: Placeholder for future analytics services.

### `config/`
*   **`signal_validation_rules.yaml`**: Default rules for signal validation.
*   **`UI_USAGE.md`**: Documentation for UI usage.

### `scripts/`
*   **`generate_sample_logs.py`**: Utility to generate large sample log files for testing.
*   **`test_chunked_loading.py`**: Scripts to verify chunked loading performance.

### `tests/`
*   Contains integration and unit tests (e.g., `test_multi_view_system.py`, `test_parse_timing.py`) ensuring system stability.

### Root Scripts
*   **`generate_random_log.py`**: Quick script for generating random test logs.
*   **`test_validation_ui.py`**, **`test_validator.py`**: Standalone scripts for testing validation logic and UI.

## "Gotchas" & Patterns

*   **Parser Registry:** New parsers must be registered in `parser_registry.py`.
*   **Performance:**
    *   **Fast Paths:** `PLCDebugParser` uses manual string parsing (`_fast_parse_line`) which is significantly faster than regex.
    *   **Lazy Computation:** `SignalData` computes states only when needed.
    *   **Chunking:** Large files are handled by `ChunkedParsedLog` and `ChunkManager`.
*   **Threading:** Parsing runs in `QThread` (`ParserThread`) + `ProcessPoolExecutor`.
*   **Dependencies:** `requirements.txt` lists `PyQt6`, but code uses `PySide6`.
*   **Platform Specifics:** `main.py` has Wayland-specific window sizing logic.
*   **Temporary Files:** Use `/tmp` for temporary storage.
