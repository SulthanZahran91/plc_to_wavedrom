# Repository Guidelines

PLC Visualizer renders PLC log streams into Qt dashboards, so this guide highlights the few conventions that keep the tool consistent and reliable.

## Project Structure & Module Organization

Core source lives inside `plc_visualizer/`: models in `models/`, stream readers and parsers in `parsers/`, Qt windows/widgets in `ui/`, and cross-cutting helpers in `utils/`. Tests mirror that tree under `plc_visualizer/tests/`. Demo and fixture data live in `sample_logs/` and `test_data/`, while synthetic runs from `generate_random_log.py` are written to `generated_logs/`. Operational scripts (`scripts/`) and utilities (`tools/`) hold maintenance and visualization helpers such as the map viewer playback harness.

## Build, Test, and Development Commands

- `uv sync` — install or update the locked dependency set.
- `uv run python main.py` — launch the main GUI; Wayland-friendly sizing logic resides in `main.py`.
- `uv run python tools/map_viewer/playback_demo.py` — run the detached map viewer against bundled fixtures.
- `uv run pytest` — execute the full test suite; append `-k parser` or similar when narrowing scope.
- `uv run python scripts/test_chunked_loading.py` — manual smoke test for streaming ingestion regressions.

## Coding Style & Naming Conventions

Adhere to PEP 8 with 4-space indentation, explicit imports, and `snake_case` for modules, functions, and locals. Reserve `PascalCase` for Qt widgets/data models (e.g., `SignalPanel`). Keep Qt resource loading isolated to `plc_visualizer/ui/` and pass structured models rather than raw dicts across module boundaries. Prefer descriptive signal names that reflect the originating PLC field.

## Testing Guidelines

Write Pytest modules as `test_<feature>.py` under `plc_visualizer/tests/`, grouping fixtures by domain. Reuse `test_data/` log artifacts when covering parser edge cases, and lean on `pytest-qt` (`qtbot`) for widget coverage. Run `uv run pytest --maxfail=1 --disable-warnings` before publishing changes, and capture targeted commands (e.g., `uv run pytest -k map_viewer`) in the PR when verifying fixes.

## Commit & Pull Request Guidelines

Follow the “Verb object with context” pattern used in history (`Enhance timestamp handling in parser`). Each PR should summarize scope, link the driving issue, and attach evidence: console `pytest` excerpts, screenshots, or clip recordings for UI tweaks. Highlight blocked follow-ups or data refresh needs so reviewers can queue subsequent work.

## Security & Configuration Tips

Dependencies stay pinned in `pyproject.toml`/`uv.lock`; only regenerate locks when necessary and note the change in the PR. Never commit artifacts from `generated_logs/` or other large captures—share them out-of-band. When enabling networked PLC features, confirm sandbox and hardware limits to avoid exposing sensitive runtime data.
