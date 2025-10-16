# Feature Suggestions

Ideas to grow the PLC Log Visualizer beyond its current capabilities. Grouped so you can prioritize quickly.

## UI and Workflow
- Add a startup wizard that lets users queue log files and pick parsers with preview stats before fully loading the UI.
- Persist per-signal visibility, zoom, and filter presets across sessions via lightweight config storage.
- Provide inline annotations on the waveform (double-click to place a note tied to timestamps) and export them with the log bundle.
- Introduce a quick-compare mode to overlay signals from different files or devices on the same timeline for delta analysis.

## Parser Ecosystem
- Implement auto-detection heuristics that inspect the first N lines and rank parser confidence instead of first-match wins.
- Support streaming/rotating logs by watching a directory and appending new entries live, throttled to avoid UI churn.
- Add optional CSV/JSON exporters so parsed results can feed other analytics pipelines.
- Build a parser plugin template (cookiecutter or script) that scaffolds new subclasses of `GenericTemplateLogParser` with tests.

## Performance and Scaling
- Cache waveform-ready `SignalData` on disk for large datasets so subsequent sessions reload instantly.
- Provide a headless CLI mode (`uv run python -m plc_visualizer.cli ...`) that parses and emits stats without launching Qt.
- Allow multi-worker waveform preparation with configurable concurrency and progress callbacks for better responsiveness.
- Instrument parser and UI phases with tracing hooks (e.g., `tracing.py` or OpenTelemetry) to spot bottlenecks.

## Testing and CI
- Expand parser tests to cover current log fixtures (`sample_logs`) and edge cases (multi-device interleaving, malformed timestamps).
- Add Qt-driven integration tests using `pytest-qt` that simulate file uploads and assert waveform/table updates.
- Set up a GitHub Actions workflow running `uv sync`, lint checks (ruff/flake8), and `pytest` against Linux/Windows.
- Create golden-image snapshots for waveform rendering so regressions in painter logic are caught early.

## Developer Experience
- Document `uv` workflows in contributing guidelines and add helper scripts under `python_plc_visualizer/scripts` (format, lint, test).
- Offer a debug console inside the app that exposes parser stats, current viewport range, and active filters.
- Provide a `make docs` workflow that builds API docs (pdoc or sphinx) for models, parsers, and utils.
- Package the app via PyInstaller or fbs for distribution, including platform-specific launch scripts.
