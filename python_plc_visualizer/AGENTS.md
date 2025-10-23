# Repository Guidelines

This guide captures the current conventions for contributing to the PLC visualizer so agents can ramp quickly and deliver consistent updates.

## Project Structure & Module Organization

Core Python packages live under `plc_visualizer/`. Domain models are in `plc_visualizer/models/`, parsers and log readers in `plc_visualizer/parsers/`, Qt windows and widgets in `plc_visualizer/ui/`, and shared helpers in `plc_visualizer/utils/`. Pytest suites reside in `plc_visualizer/tests/`. Sample PLC logs for demos are stored in `sample_logs/` and `test_data/`, while synthetic runs generated via `generate_random_log.py` land in `generated_logs/`. Maintenance and conversion scripts are organized under `scripts/` and `tools/`.

## Build, Test, and Development Commands

- `uv sync`: install dependencies declared in `pyproject.toml`/`uv.lock`.
- `uv run python python_plc_visualizer/main.py`: launch the main GUI (Wayland-safe sizing is handled in code).
- `uv run pytest`: execute the automated test suite; add `-k` filters when iterating locally.
- `uv run python python_plc_visualizer/tools/map_viewer/playback_demo.py`: exercise the standalone map viewer with generated fixtures.

## Coding Style & Naming Conventions

Follow PEP 8 with 4-space indentation, explicit imports, and `snake_case` for modules, functions, and variables. Reserve `PascalCase` for Qt widgets and data models. Keep Qt `.ui` loaders, resources, and widget logic isolated under `plc_visualizer/ui/` to avoid cross-layer coupling. Prefer descriptive signal names that mirror the underlying PLC field being visualized.

## Testing Guidelines

Author Pytest modules as `test_<feature>.py` within `plc_visualizer/tests/`. Exercise log parsing edge cases using fixtures drawn from `test_data/`. UI additions should include `pytest-qt` (`qtbot`) coverage for the relevant widgets/windows. Run `uv run pytest --maxfail=1 --disable-warnings` before opening a pull request and add targeted `-k` filters when iterating locally. For streaming stress tests, `uv run python python_plc_visualizer/scripts/test_chunked_loading.py` provides a quick manual check.

## Commit & Pull Request Guidelines

Write commits in the “Verb object with context” style seen in history (e.g., `Enhance timestamp handling in parser`). Each pull request should summarize the change, provide test evidence (terminal `pytest` output or viewer screenshots), and link the driving issue. Call out follow-up tasks or required data updates so reviewers can sequence work effectively.

## Security & Configuration Tips

Keep dependencies pinned via `requirements.txt` or `uv.lock` and regenerate them only when necessary. Avoid committing generated logs from `generated_logs/`; share large datasets externally when needed. Review sandbox or hardware requirements before enabling networked PLC features to prevent accidental exposure of sensitive runtime data.
