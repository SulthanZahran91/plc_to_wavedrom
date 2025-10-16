# PLC Log Visualizer - Agent INIT

## TL;DR
- Desktop app built with PyQt6 to parse PLC logs, merge multiple files, and render synchronized waveforms plus data tables.
- Two parser flavors (`plc_debug`, `plc_tab`) extend a high-performance base parser with regex/template fast paths and multiprocessing helpers.
- Waveform rendering flows: raw logs -> `ParsedLog` -> `process_signals_for_waveform` -> `WaveformScene/WaveformView`, coordinated by `MainWindow` and `ViewportState`.
- Prefer `uv` for dependency management and launching (`uv sync`, `uv run python python_plc_visualizer/main.py`).

## Runbook
- `uv sync` - set up the virtual environment declared in `pyproject.toml`.
- `uv run python python_plc_visualizer/main.py` - launch the GUI (Wayland-safe sizing handled in `main.py`).
- `uv run pytest` - execute PyTest suite (currently limited but covers parser contracts and viewport state).
- Sample logs live in `python_plc_visualizer/sample_logs`; generate larger fixtures via `uv run python python_plc_visualizer/generate_random_log.py`.

## Layout Overview
| Path | Role |
| --- | --- |
| `python_plc_visualizer/main.py` | PyQt entrypoint configuring the app and showing `MainWindow` with Wayland-friendly sizing logic. |
| `python_plc_visualizer/plc_visualizer/models/data_types.py` | Domain dataclasses: `LogEntry`, `ParsedLog`, `ParseResult`, `ParseError`, `SignalType`. Everything downstream consumes these shapes. |
| `python_plc_visualizer/plc_visualizer/parsers/base_parser.py` | Performance-focused foundation: fast timestamp parsing, regex/template selection, numeric inference, optional multiprocessing for heavy workloads. Implement `GenericTemplateLogParser` subclasses here. |
| `python_plc_visualizer/plc_visualizer/parsers/plc_parser.py` & `plc_tab_parser.py` | Concrete parser registrations for bracketed debug logs vs tab-separated exports; both register themselves with the singleton `parser_registry`. |
| `python_plc_visualizer/plc_visualizer/parsers/parser_registry.py` | Central registry choosing the appropriate parser via `can_parse`; falls back to a default if provided. |
| `python_plc_visualizer/plc_visualizer/ui/main_window.py` | Orchestrates file uploads, background parsing (`ParserThread`), stats, waveform view, data table, zoom/pan, and signal filtering widgets. |
| `python_plc_visualizer/plc_visualizer/ui/` | Widget library: drag-drop uploader, stats panel, filter tree, waveform scene/view, zoom & pan controls, copy-friendly table view, etc. |
| `python_plc_visualizer/plc_visualizer/utils/` | Merging helpers (`merge_parsed_logs`, `merge_parse_results`), waveform processors (`SignalData`, `SignalState`, `process_signals_for_waveform`), and viewport state management (`ViewportState`). |
| `python_plc_visualizer/scripts/` | Helper scripts (e.g., automation hooks); check per-script docstrings for guidance. |
| `python_plc_visualizer/test_data` & root `test_data` | Fixture samples mirroring common PLC log shapes. |

## Data & Control Flow
1. **File selection** - `FileUploadWidget` emits paths to `MainWindow._on_files_selected`.
2. **Parsing** - `ParserThread` sequentially calls `parser_registry.parse` for each file; individual parser subclasses parse into `ParseResult`.
3. **Aggregation** - `merge_parse_results` combines successes into a single `ParsedLog`, retaining per-file `ParseError` metadata.
4. **Signal prep** - `process_signals_for_waveform` groups entries (`group_by_signal`) and builds `SignalData`/`SignalState` sequences; large datasets may spawn a subprocess via `ParserThread._compute_signal_data`.
5. **UI update** - `StatsWidget` shows metrics/errors, `DataTableWidget` lists entries, `SignalFilterWidget` populates device/signal tree, and `WaveformView/WaveformScene` render timelines coordinated by `ViewportState` zoom/pan events.

## Key PyQt Components
- `MainWindow` wires everything; note `_viewport_state` and `_signal_data_list` caching for responsive filtering/zooming.
- `WaveformView` keeps the time axis pinned during resize/scroll, relays wheel events to zoom controls, and resets transforms to fill the viewport.
- `SignalFilterWidget` provides search (plain text or `/regex`), type toggles, "changed only" filtering, and presets; emits visible-signal updates consumed by both waveform and table.
- `DataTableWidget` uses `LogDataModel` (`QAbstractTableModel`) to expose device/signal/timestamp/value/type columns with simple filtering hooks.
- `StatsWidget` summarizes counts and time-range windows; toggles an error text panel when `ParseResult` carries failures.

## Parser Extension Tips
- Subclass `GenericTemplateLogParser` and set either `LINE_RE` (regex fast path) or `TEMPLATE` (uses `parse` library). Override `TYPE_MAP`, `DEVICE_ID_REGEX`, or `INFER_TYPES` as needed.
- Implement `can_parse` if quick sniffing can short-circuit detection before full parsing.
- Register new parsers via `parser_registry.register(MyParser(), is_default=True/False)` within the module that defines them.
- Reuse `_fast_ts`, `_parse_int_like`, and `_parse_value_fast` helpers to stay consistent with existing inference logic.

## Testing & Diagnostics
- `plc_visualizer/tests/test_viewport_state.py` validates zoom/pan math and signal emission contracts.
- `plc_visualizer/tests/test_parser.py` still references a legacy `DefaultParser`; either restore that parser or update the suite to target the current `parser_registry` ecosystem.
- CI-style smoke test: `uv run pytest -q`.
- Inspect parsing behavior quickly via `ParserThread.parse_streaming` or by running parser modules directly within an interactive REPL (`uv run python -m plc_visualizer.parsers.plc_parser <file>` once wiring exists).

## Utilities & Fixtures
- `generate_random_log.py` can create tailored samples:
  - `uv run python python_plc_visualizer/generate_random_log.py --signals 20 --lines 5000`.
  - Bulk mode (`--bulk`) generates ~30 MB logs per registered parser into `sample_logs/generated`.
- `python_plc_visualizer/scripts/` may hold automation helpers (review docstrings per file).
- Root-level `todo.md` can outline outstanding tasks; sync with this INIT when major components change.

## Known Gaps / TODO Radar
- Update `plc_visualizer/tests/test_parser.py` to exercise the active parsers (`plc_debug`, `plc_tab`) now that `DefaultParser` has been retired.
- Wayland sizing logic exists in `main.py` and `MainWindow`; ensure any new top-level windows respect the same conventions.
- Multiprocessing fallback in `ParserThread._compute_signal_data` defaults to single worker; tune `max_workers` if waveform prep becomes CPU-bound.

## Quick Reference Commands
```
# Sync dependencies (respects uv policy from AGENTS.MD)
uv sync

# Launch GUI
uv run python python_plc_visualizer/main.py

# Run tests
uv run pytest

# Generate debug-style samples
uv run python python_plc_visualizer/generate_random_log.py --bulk
```
