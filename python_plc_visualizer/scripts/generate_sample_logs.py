"""Generate sample log files for each registered parser.

Run as:
    python -m python_plc_visualizer.scripts.generate_sample_logs --output-dir sample_logs
or directly:
    python python_plc_visualizer/scripts/generate_sample_logs.py --output-dir sample_logs
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable, Dict

# Ensure the package root is importable when executing the script directly
PACKAGE_ROOT = Path(__file__).resolve().parents[1]
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

from plc_visualizer.parsers import parser_registry


def _timestamp_series(start: datetime, count: int, step_seconds: int) -> list[str]:
    """Create a sequence of HH:MM:SS timestamps starting from `start`."""
    stamps = []
    for i in range(count):
        ts = start + timedelta(seconds=i * step_seconds)
        stamps.append(ts.strftime("%H:%M:%S"))
    return stamps


def _format_millis(dt: datetime) -> str:
    """Format a datetime with millisecond precision."""
    return dt.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]


def _timestamp_series_full(
    start: datetime, count: int, step_milliseconds: int
) -> list[str]:
    """Create a sequence of ISO timestamps with millisecond precision."""
    stamps = []
    delta = timedelta(milliseconds=step_milliseconds)
    current = start
    for _ in range(count):
        stamps.append(_format_millis(current))
        current += delta
    return stamps


def _generate_default_log(output_dir: Path) -> Path:
    """Generate a sample log compatible with the default parser."""
    file_path = output_dir / "default_parser.log"

    start_time = datetime(2024, 1, 1, 10, 30, 45)
    timestamps = _timestamp_series(start_time, count=6, step_seconds=5)

    lines = [
        f"DEVICE_A MOTOR_START {timestamps[0]} true boolean",
        f"DEVICE_A SENSOR_A {timestamps[1]} ready string",
        f"DEVICE_B COUNTER_1 {timestamps[2]} 100 integer",
        f"DEVICE_A MOTOR_START {timestamps[3]} false boolean",
        f"DEVICE_A SENSOR_A {timestamps[4]} error string",
        f"DEVICE_B COUNTER_1 {timestamps[5]} 150 integer",
    ]

    file_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return file_path


def _generate_plc_debug_log(output_dir: Path) -> Path:
    """Generate a sample log compatible with the PLC debug parser."""
    file_path = output_dir / "plc_debug_parser.log"

    start_time = datetime(2025, 9, 22, 13, 0, 0, 199000)
    timestamps = _timestamp_series_full(start_time, count=5, step_milliseconds=250)

    device_path = "/AreaA/Line01/Robot-01@Main"

    lines = [
        f"{timestamps[0]} [Debug] [{device_path}] [INPUT2:I_MOVE_IN] (Boolean) : ON",
        f"{timestamps[1]} [Info] [{device_path}] [INPUT2:I_MOVE_IN] (Boolean) : OFF",
        f"{timestamps[2]} [Debug] [{device_path}] [ANALOG:PRESSURE] (Integer) : 345",
        f"{timestamps[3]} [Warn] [{device_path}] [ANALOG:TEMP] (Integer) : 102",
        f"{timestamps[4]} [Debug] [{device_path}] [STATE:MODE] (String) : MANUAL",
    ]

    file_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return file_path


def _generate_plc_tab_log(output_dir: Path) -> Path:
    """Generate a sample log compatible with the PLC tab-separated parser."""
    file_path = output_dir / "plc_tab_parser.log"

    start_time = datetime(2025, 9, 22, 14, 5, 0, 500000)
    timestamps = _timestamp_series_full(start_time, count=4, step_milliseconds=500)

    path_base = "CellB/Assembly/Robot-02@Backup"

    lines = [
        f"{timestamps[0]} [] {path_base}\tOUTPUT1:CLAMP_ENGAGED\tOUT\tON\t\tStation-12\tOK\t{timestamps[0]}",
        f"{timestamps[1]} [] {path_base}\tOUTPUT1:CLAMP_ENGAGED\tOUT\tOFF\t\tStation-12\tOK\t{timestamps[1]}",
        f"{timestamps[2]} [] {path_base}\tANALOG:FORCE\tOUT\t482\t\tStation-12\tOK\t{timestamps[2]}",
        f"{timestamps[3]} [] {path_base}\tSTATE:MODE\tOUT\tAUTO\t\tStation-12\tWarn\t{timestamps[3]}",
    ]
    file_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return file_path


def main():
    parser = argparse.ArgumentParser(
        description="Generate sample PLC logs for each registered parser."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("generated_logs"),
        help="Directory to write the generated log files (defaults to ./generated_logs)",
    )
    args = parser.parse_args()

    output_dir: Path = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    generators: Dict[str, Callable[[Path], Path]] = {
        "default": _generate_default_log,
        "plc_debug": _generate_plc_debug_log,
        "plc_tab": _generate_plc_tab_log,
    }

    generated_files: Dict[str, Path] = {}
    skipped_parsers: list[str] = []

    for parser_name in parser_registry.get_parser_names():
        generator = generators.get(parser_name)
        if generator is None:
            skipped_parsers.append(parser_name)
            continue

        generated_files[parser_name] = generator(output_dir)

    if generated_files:
        print("Generated sample logs:")
        for parser_name, file_path in generated_files.items():
            print(f"  - {parser_name}: {file_path}")
    else:
        print("No sample logs were generated. No known generators for registered parsers.")

    if skipped_parsers:
        print("\nParsers without sample generators:")
        for parser_name in skipped_parsers:
            print(f"  - {parser_name}")
        print("Add a generator in this script to support these parsers.")


if __name__ == "__main__":
    main()
