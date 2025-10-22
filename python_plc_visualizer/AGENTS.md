# Repository Guidelines

## Project Structure & Module Organization
The core package lives in `plc_visualizer/`, with domain logic under `models/`, file readers in `parsers/`, Qt windows and widgets in `ui/`, and shared helpers in `utils/`. Pytest suites reside in `plc_visualizer/tests/`. Sample PLC logs used in demos sit in `sample_logs/` and `test_data/`, while `generated_logs/` holds synthetic runs produced by `generate_random_log.py`. Utility scripts for maintenance and converters live in `scripts/` and `tools/`.

## Build, Test, and Development Commands
- `python -m venv .venv && source .venv/bin/activate`: create and activate a local environment (recommended).
- `pip install -r requirements.txt`: install runtime and test dependencies; use `uv pip sync` if you prefer the locked set in `uv.lock`.
- `python main.py`: launch the Qt visualizer with the default sample dataset.
- `pytest`: run the full unit and UI test suite; add `-k` to target a single module when iterating.

## Coding Style & Naming Conventions
Follow PEP 8 with 4-space indentation and explicit imports. Use `snake_case` for modules, functions, and variables; reserve `PascalCase` for Qt widgets and data models. Prefer descriptive signal names that mirror the PLC fields. Keep Qt `.ui` loaders and resource references inside `ui/` modules to avoid cross-layer coupling.

## Testing Guidelines
Write Pytest tests alongside the code in `plc_visualizer/tests/`, naming files `test_<feature>.py`. When adding UI behavior, include a `qtbot` fixture example that demonstrates the user-driven flow. Target meaningful coverage of log parsing edge cases by extending fixtures under `test_data/`. Run `pytest --maxfail=1 --disable-warnings` before submitting to catch regressions quickly.

## Commit & Pull Request Guidelines
Commits should read like “Verb object with context”, mirroring the existing history (e.g., `Enhance timestamp handling...`). Group related changes and keep commits focused. Every pull request needs a short summary, test evidence (`pytest` output or screenshots of the viewer), and links to the driving issue. Call out any follow-up work or data dependencies in the PR body.
