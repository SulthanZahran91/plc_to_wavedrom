# Project Overview: PLC Log Visualizer

**PLC Log Visualizer** is a desktop application built with `PySide6` designed to parse, merge, and visualize PLC logs. It provides synchronized timelines, data tables, and map overlays to assist in debugging and analyzing industrial automation logs.

## Architecture Philosophy

  * **Performance-First:** Utilizes `GenericTemplateLogParser` with regex fast-paths and multiprocessing to handle large log files efficiently.
  * **Modularity:** Enforces clear separation between components:
      * `models/` (Data models)
      * `parsers/` (Log parsing logic)
      * `ui/` (User interface components)
      * `utils/` (Helper utilities)
  * **Extensibility:** Follows a registry pattern (`parser_registry.py`), allowing easy addition of new log formats by subclassing `GenericTemplateLogParser`.
  * **Cross-Platform:** Designed for Linux (supporting both Wayland and X11) with specific window sizing logic.

## Code Guidelines

### Dependency Management

Use `uv` for all dependency operations.

  * **Sync Dependencies:**
    ```bash
    uv sync
    ```
  * **Run Application:**
    ```bash
    uv run python python_plc_visualizer/main.py
    ```
  * **Testing:**
    Verify changes using `uv run pytest`. Ensure new features or parsers have accompanying tests.

### Development Standards

  * **File Structure:** All source code resides in the `python_plc_visualizer/` directory.
  * **Temporary Files:** Use `/tmp` for any helper scripts, temporary data, or backup files.
  * **Status Updates:** Do not create README files to update progress; print status to standard output (`stdout`) or put it in /tmp/agent_status.txt.
  * **Formatting:** Maintain clean, **PEP 8** compliant Python code.

## AGENTS GUIDELINES

  * Read CONTEXT.md for project overview and architecture philosophy.

  