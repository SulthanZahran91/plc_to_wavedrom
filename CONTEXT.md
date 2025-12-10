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
    *   `parse_files(file_paths)`: Kick off a parse job for the provided file paths.
    *   `clear_session()`: Reset all parsed state.
    *   `add_bookmark(timestamp, label, description)`: Add a new bookmark.
    *   `sync_all_views(target_time)`: Synchronize all views to the specified time.

### `models/`
*   **`data_types.py`**: Core structures: `LogEntry`, `ParsedLog`, `SignalType`.
*   **`chunked_log.py`**: `ChunkedParsedLog` for memory-efficient storage (LRU cache of `TimeChunk`s).
    *   `get_entries_in_range(start_time, end_time)`: Get all entries within a time range.
    *   `prefetch_chunks(start_time, end_time)`: Prefetch chunks in a time range.
    *   `clear_cache()`: Clear all cached chunks from memory.
*   **`bookmark.py`**: Manages user bookmarks.

### `parsers/`
*   **`parser_registry.py`**: Singleton registry for auto-detecting parsers.
    *   `register(parser, is_default)`: Register a parser.
    *   `detect_parser(file_path)`: Auto-detect which parser can handle the file.
    *   `parse(file_path, parser_name, num_workers)`: Parse a file using auto-detection or specified parser.
*   **`base_parser.py`**: `GenericTemplateLogParser` with regex fast-paths (`_fast_ts`, `_parse_line_hot`).
    *   `parse(file_path, num_workers)`: Parse a file.
    *   `parse_time_window(file_path, start_time, end_time)`: Parse only entries within a specific time window.
*   **`plc_parser.py`**: `PLCDebugParser` implementation with an "ultra-fast" bracket-delimited parser (`_fast_parse_line`).
    *   `parse_time_window(file_path, start_time, end_time)`: Optimized time-window parsing for bracket-delimited format.
*   **`mcs_parser.py`**: `MCSLogParser` for MCS/AMHS log format with `[ACTION=CommandID, CarrierID]` headers and `[Key=Value]` pairs.
    *   `can_parse(file_path)`: Detect MCS log format.
    *   `_parse_line_to_entries(line)`: Parse a single line into multiple signal entries.
    *   `parse_time_window(file_path, start_time, end_time)`: Optimized time-window parsing.
*   **`plc_tab_parser.py`**, **`csv_signal_parser.py`**: Specialized parsers for other formats.

### `ui/`
*   **`main_window.py`**: Primary UI container. Uses `SplitPaneManager`.
    *   `_init_ui()`: Initialize the user interface.
    *   `_bind_session_manager()`: Connect session manager signals to window handlers.
    *   `_add_timing_view()`: Add a new timing diagram view.
*   **`theme.py`**: Defines application styles (colors, fonts).
*   **`components/`**:
    *   **`split_pane_manager.py`**: Manages flexible tabbed/split layouts.
    *   **`signal_filter_widget.py`**: Complex filtering logic (regex, presets, "show changed").
    *   **`waveform/`**:
        *   **`waveform_view.py`**: Container for the scene.
            *   `set_data(parsed_log)`: Set the data to visualize.
            *   `set_visible_signals(signal_names)`: Update which signals are visible.
            *   `set_viewport_state(viewport_state)`: Set the viewport state manager.
        *   **`waveform_scene.py`**: Manages `SignalItem`s and `TimeAxisItem`. Supports chunked reloading.
            *   `set_data(parsed_log, lazy, chunk_manager)`: Set the parsed log data and render waveforms.
            *   `set_visible_signals(signal_names)`: Update which signals are visible and rebuild the scene.
            *   `set_time_range(start, end)`: Update the visible time range for viewport culling.
        *   **`signal_item.py`**: Renders waveforms using `BooleanRenderer` or `StateRenderer`.
        *   **`time_axis_item.py`**, **`grid_lines_item.py`**: Visual guides.
        *   **`zoom_controls.py`**, **`pan_controls.py`**: Navigation widgets.
*   **`windows/`**:
    *   **`timing_window.py`**: Embeddable view for waveforms.
    *   **`log_table_window.py`**: Tabular view of logs.
    *   **`map_viewer_window.py`**: Container for the Map Viewer tool with carrier tracking controls.
        *   `_on_track_carriers_toggled(state)`: Handle carrier tracking toggle.
        *   `_on_search_carrier()`: Search and highlight carrier by ID on the map.
*   **`dialogs/`**: `bookmark_dialog.py`, `help_dialog.py`.

### `utils/`
*   **`chunk_manager.py`**: Connects `ChunkedParsedLog` to parsers for on-demand loading.
    *   `get_entries_in_range(start_time, end_time, with_prefetch)`: Get entries in a time range, with optional prefetching.
    *   `clear_cache()`: Clear all cached chunks.
*   **`waveform_data.py`**: `SignalData` structure for visualization (lazy state computation).
*   **`merge.py`**: Logic to combine multiple parsed logs.

### `validation/`
*   **`validator.py`**: `SignalValidator` orchestrates validation rules.
    *   `validate_device(device_id, signal_data_list)`: Validate all signals for a specific device.
    *   `validate_all(parsed_log, signal_data_list)`: Validate all devices in a log.
*   **`rule_loader.py`**: Loads rules from YAML.
*   **`pattern_validators/`**: Contains specific validators like `SequenceValidator`.

### `tools/map_viewer/`
*   **`renderer.py`**: `MapRenderer` (QGraphicsView) for visualizing system layout.
    *   `set_objects(objects)`: Render parsed objects into the scene.
    *   `update_rect_color_by_unit(unit_id, block_color, arrow_color, text_overlay_info)`: Update colors/overlays by UnitId.
    *   `highlight_unit(unit_id)`: Highlight and center view on a specific unit by UnitId.
*   **`state_model.py`**: `UnitStateModel` manages state-to-color mapping and carrier tracking.
    *   `enable_carrier_tracking`: Property to toggle carrier tracking mode.
    *   `get_carrier_location(carrier_id)`: Get current location (UnitId) of a carrier.
    *   `on_signal(event)`: Process signal events; intercepts `CurrentLocation` signals when tracking enabled.
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
*   **Carrier Tracking:** Map Viewer feature to display CarrierID at CurrentLocation (disabled by default, MCS/AMHS logs only). 
    *   **Display Logic:** Single carrier shows CarrierID (truncated from start for long IDs); multiple carriers show count (e.g., "2x", "3x").
    *   **Color Gradient:** Unit background color changes based on carrier count: 0=default, 1=green (#90EE90), 2=yellow (#FFD700), 3=orange (#FFA500), 4+=red gradient.
    *   **Info Box:** Left-clicking a unit shows detailed carrier list and count in the info panel.
    *   **Edge Cases:** Validates CurrentLocation signals exist before enabling. Handles null/empty locations by clearing overlays. Updates count when carriers move.
    *   **Implementation:** `state_model._get_carrier_count_color()` determines block color; `state_model._update_unit_display()` manages overlay and color logic; `renderer._show_info()` displays carrier details.
