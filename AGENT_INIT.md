# PLC Log Visualizer - Agent INIT

## TL;DR
- Desktop app built with PySide6 to parse PLC logs, merge multiple files, and render synchronized timelines, tables, and map overlays.
- Parsers (`plc_debug`, `plc_tab`, `csv_signal`) share the high-performance `GenericTemplateLogParser` base with regex fast-paths and multiprocessing helpers.
- Core pipeline: raw logs → `ParseResult` → `merge_parse_results` → `process_signals_for_waveform` → `SignalData` consumed by the waveform, log table, interval dialog, and optional map viewer.
- Prefer `uv` for dependency management and execution (`uv sync`, `uv run python python_plc_visualizer/main.py`).

## Runbook
- `uv sync` — install dependencies declared in `pyproject.toml` / `uv.lock`.
- `uv run python python_plc_visualizer/main.py` — launch the GUI (Wayland sizing handled in `main.py`).
- `uv run pytest` — run the current Pytest suite (viewport coverage plus chunked loading smoke tests).
- Sample logs live in `python_plc_visualizer/sample_logs`; generate larger fixtures with `uv run python python_plc_visualizer/generate_random_log.py`.

## Layout Overview
| Path | Role |
| --- | --- |
| `python_plc_visualizer/main.py` | PySide6 entrypoint that creates `QApplication`, instantiates `MainWindow`, and applies Wayland-friendly sizing. |
| `python_plc_visualizer/plc_visualizer/models/data_types.py` | Domain dataclasses (`LogEntry`, `ParsedLog`, `ParseResult`, `ParseError`, `SignalType`). |
| `python_plc_visualizer/plc_visualizer/parsers/base_parser.py` | Parser infrastructure (timestamp parsing, dtype inference, streaming helpers, multiprocessing offload). Subclass `GenericTemplateLogParser` here. |
| `python_plc_visualizer/plc_visualizer/parsers/plc_parser.py`, `plc_tab_parser.py`, `csv_signal_parser.py` | Concrete parser registrations for bracketed debug logs, tab-delimited exports, and CSV signals. |
| `python_plc_visualizer/plc_visualizer/parsers/parser_registry.py` | Singleton registry handling parser detection, explicit parser selection, and `parse()` orchestration. |
| `python_plc_visualizer/plc_visualizer/ui/main_window.py` | Coordinates uploads, background parsing (`ParserThread`), stats, waveform window, log table, map viewer, and interval plotting. |
| `python_plc_visualizer/plc_visualizer/ui/` | Widgets: drag/drop uploader, stats panel, filter tree, waveform stack (`WaveformView`, `WaveformScene`, renderers), pan/zoom controls, log table, dialogs, and map viewer integration. |
| `python_plc_visualizer/plc_visualizer/utils/` | Merge helpers, waveform processors (`SignalData`, `SignalState`, `process_signals_for_waveform`), chunked-loading utilities, and `ViewportState`. |
| `python_plc_visualizer/scripts/` | Developer tooling (sample log generation, chunked loading tests, shared pytest fixtures). |
| `python_plc_visualizer/tools/map_viewer/` | Standalone map viewer package reused by `IntegratedMapViewer` with YAML-driven device→unit mapping and color policies. |

## Data & Control Flow
1. **File selection** — `FileUploadWidget` emits resolved paths to `MainWindow._on_files_selected`, which normalises and validates them.
2. **Parsing** — `ParserThread` iterates the files, calling `parser_registry.parse`. Each `ParseResult` is captured in `_file_results` while progress updates drive the progress bar.
3. **Aggregation** — `merge_parse_results` combines successes into a single `ParsedLog` and coalesces parser errors for stats display.
4. **Signal prep** — `process_signals_for_waveform` groups entries, produces `SignalData` lists, and offloads work to a shared process pool when entry counts exceed ten thousand.
5. **UI update** — Stats widget gets aggregated metrics, waveform and table windows receive the new `SignalData`, signal filters rebuild their tree, and the map viewer (if open) reloads device state.
6. **Navigation** — Viewport changes flow through a shared `ViewportState`; zoom/pan controls, waveform scene, time-range selector, and map viewer playback stay in sync.

## Key Qt Components
- `MainWindow` coordinates uploads, background parsing, and window launches (timing diagram, log table, map viewer, interval dialog).
- `TimingDiagramWindow` hosts `WaveformView`, zoom/pan controls, filter drawer, and transition markers synced to `ViewportState`.
- `LogTableWindow` reuses `DataTableWidget` and `SignalFilterWidget` for detailed tabular inspection with copy-friendly table view.
- `SignalFilterWidget` provides search, device tree filtering, type toggles, and presets; emits `visible_signals_changed` and `plot_intervals_requested`.
- `IntegratedMapViewer` wraps the map viewer toolkit, wiring `SignalData` into `UnitStateModel` so signal values recolor units over time.
- `SignalIntervalDialog` turns a single signal’s transitions into interval plots and tables for duration analysis.

## Parser Extension Tips
- Subclass `GenericTemplateLogParser`, set `name`, and provide either `LINE_RE` (regex with named groups) or `TEMPLATE` (parse module) plus optional overrides (`TYPE_MAP`, `DEVICE_ID_REGEX`, `TIMESTAMP_FORMAT`).
- Implement `can_parse` for quick detection if files share a unique signature; `parser_registry.parse(file, parser_name="...")` remains available for explicit selection.
- Reuse `_fast_ts`, `_infer_type_fast`, and `_parse_value_fast` to keep behaviour consistent across parsers, especially when adding float support.
- Add optional generators under `scripts/` to keep sample data in sync, and register new formats with `generate_random_log.py` if needed.

## Testing & Diagnostics
- `plc_visualizer/tests/test_viewport_state.py` exercises zoom/pan logic thoroughly.
- `scripts/test_chunked_loading.py` and `test_chunked_loading_quick.py` offer executable smoke tests for streaming large logs.
- Encourage additional pytest modules for parser accuracy, merge helpers, and UI contracts (pytest-qt is already in `pyproject.toml`).
- Quick sanity checks: `uv run pytest -q`, `uv run python python_plc_visualizer/tools/map_viewer/playback_demo.py` for map rendering.

## Utilities & Fixtures
- `generate_random_log.py` synthesises logs per parser (`--parser plc_debug --lines 5000`) or bulk multi-format fixtures (`--bulk`).
- `scripts/generate_sample_logs.py` writes curated examples into `sample_logs/generated` for demos and regression tests.
- `tools/map_viewer` contains the reusable renderer plus YAML-driven mapping/color policy; `IntegratedMapViewer` consumes the same APIs.
- `test_data/` (root and package) holds canonical fixtures; keep them small to ensure Pytest remains fast.

## Known Gaps / TODO Radar
- Expand automated tests: parser contracts, merge utilities, and UI signal wiring currently rely on manual verification.
- Flesh out CSV parser documentation and connect it to sample log generation to avoid bitrot.
- Evaluate multi-process signal preprocessing scaling (`max_workers`) and add metrics/telemetry for long-running merges.
- Document packaging/runtime expectations (Wayland sizing, multimedia dependencies) for deployment audiences.

## Quick Reference Commands
```
# Sync dependencies
uv sync

# Launch GUI
uv run python python_plc_visualizer/main.py

# Run tests
uv run pytest

# Generate demo logs
uv run python python_plc_visualizer/generate_random_log.py --bulk

# Map viewer playback demo
uv run python python_plc_visualizer/tools/map_viewer/playback_demo.py
```
