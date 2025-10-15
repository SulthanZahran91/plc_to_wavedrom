"""Utility script to generate random PLC log files.

The script now supports two modes:
    1. Single-file generation (legacy behaviour) controlled via --signals/--lines/etc.
    2. Bulk generation (--bulk) that creates ~30 MB log files for each registered parser.
"""

from __future__ import annotations

import argparse
import random
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable, Iterable, List, Optional


DEFAULT_START_TIME = "10:00:00"
DEFAULT_DATE = "2024-01-01"
DEFAULT_DEVICE_PREFIX = "DEVICE_"
DEFAULT_STRING_POOL = [
    "ready",
    "idle",
    "error",
    "running",
    "paused",
    "complete",
    "starting",
    "stopped",
]

DEFAULT_SAMPLE_LOG_DIR = Path(__file__).resolve().parent / "sample_logs"
DEFAULT_BULK_OUTPUT_DIR = DEFAULT_SAMPLE_LOG_DIR / "generated"
DEFAULT_BULK_TARGET_MB = 30.0
DEFAULT_BULK_FILES_PER_PARSER = 5


@dataclass
class SignalSpec:
    """Definition of a randomly generated signal."""

    device_id: str
    name: str
    signal_type: str
    last_value: str | None = None

    def next_value(self) -> str:
        """Generate the next value for this signal."""
        if self.signal_type == "boolean":
            current = random.choice([True, False])
            value = "true" if current else "false"
        elif self.signal_type == "integer":
            # Bias toward changing values while keeping within a readable range
            base = int(self.last_value) if self.last_value and self.last_value.isdigit() else None
            if base is not None:
                # Add a small delta so graphs remain interesting
                delta = random.randint(-50, 50)
                candidate = max(0, base + delta)
            else:
                candidate = random.randint(0, 500)
            value = str(candidate)
        else:  # string
            pool = DEFAULT_STRING_POOL
            if self.last_value in pool and len(pool) > 1:
                pool = [word for word in pool if word != self.last_value]
            value = random.choice(pool)

        self.last_value = value
        return value


STATUS_STRING_POOL = [
    "AUTO",
    "MANUAL",
    "MAINT",
    "RUNNING",
    "STOPPED",
    "FAULT",
    "RESET",
    "PAUSED",
]


def _random_bool_value(
    last_value: Optional[str],
    options: tuple[str, str] = ("ON", "OFF"),
) -> str:
    candidates = list(options)
    if last_value in candidates and len(candidates) > 1:
        candidates = [opt for opt in candidates if opt != last_value]
    return random.choice(candidates)


def _random_integer_value(
    last_value: Optional[str],
    *,
    minimum: int = 0,
    maximum: int = 1000,
    delta: int = 50,
) -> str:
    base: Optional[int] = None
    if last_value is not None:
        try:
            base = int(last_value.replace(",", ""))
        except ValueError:
            base = None
    if base is None:
        candidate = random.randint(minimum, maximum)
    else:
        candidate = max(minimum, min(maximum, base + random.randint(-delta, delta)))
    return str(candidate)


def _random_string_value(
    last_value: Optional[str],
    pool: Iterable[str],
) -> str:
    options = list(pool)
    if last_value in options and len(options) > 1:
        options = [opt for opt in options if opt != last_value]
    return random.choice(options) if options else ""


@dataclass
class StructuredSignal:
    """Signal definition for rich parser log generation."""

    name: str
    value_type: str
    direction: Optional[str] = None
    category: Optional[str] = None
    dtype_label: Optional[str] = None
    boolean_values: tuple[str, str] = ("ON", "OFF")
    string_pool: Optional[List[str]] = None
    last_value: Optional[str] = None

    def next_value(self) -> str:
        """Generate a value consistent with parser expectations."""
        if self.value_type == "boolean":
            value = _random_bool_value(self.last_value, self.boolean_values)
        elif self.value_type == "integer":
            value = _random_integer_value(self.last_value)
        else:
            pool = self.string_pool if self.string_pool is not None else STATUS_STRING_POOL
            value = _random_string_value(self.last_value, pool)
        self.last_value = value
        return value


def _format_timestamp(dt: datetime) -> str:
    """Format timestamps with millisecond precision."""
    return dt.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]


class DebugLogGenerator:
    """Generate log lines compatible with PLCDebugParser."""

    def __init__(self, start_time: datetime) -> None:
        self.current_time = start_time
        self.levels = ["Debug", "Info", "Warn", "Error", "Trace"]
        self.areas = ["AreaA", "AreaB", "AreaC", "AreaD"]
        self.lines = ["Line01", "Line02", "Line03", "Line04", "Line05"]
        self.devices = ["Robot", "Conveyor", "Press", "Cell", "Handler"]
        self.modes = ["Main", "Backup", "Maintenance", "Test"]
        self.signals = [
            StructuredSignal(name="I_MOVE_IN", category="INPUT1", dtype_label="Boolean", value_type="boolean"),
            StructuredSignal(name="I_MOVE_OUT", category="INPUT2", dtype_label="Boolean", value_type="boolean"),
            StructuredSignal(name="PRESSURE", category="ANALOG", dtype_label="Integer", value_type="integer"),
            StructuredSignal(name="TEMP", category="ANALOG", dtype_label="Integer", value_type="integer"),
            StructuredSignal(
                name="MODE",
                category="STATE",
                dtype_label="String",
                value_type="string",
                string_pool=["AUTO", "MANUAL", "MAINT", "STOPPED", "RECOVERY"],
            ),
            StructuredSignal(
                name="ALARM_CODE",
                category="ALARM",
                dtype_label="String",
                value_type="string",
                string_pool=["NONE", "A001", "A204", "A350", "B010"],
            ),
        ]

    def _random_path(self) -> str:
        device = random.choice(self.devices)
        area = random.choice(self.areas)
        line = random.choice(self.lines)
        mode = random.choice(self.modes)
        unit_index = random.randint(1, 8)
        return f"/{area}/{line}/{device}-{unit_index:02d}@{mode}"

    def next_line(self) -> str:
        self.current_time += timedelta(milliseconds=random.randint(25, 300))
        ts_text = _format_timestamp(self.current_time)

        signal = random.choice(self.signals)
        value = signal.next_value()
        level = random.choice(self.levels)
        category = signal.category or "GENERAL"
        dtype_label = signal.dtype_label or signal.value_type.title()

        return (
            f"{ts_text} [{level}] [{self._random_path()}] "
            f"[{category}:{signal.name}] ({dtype_label}) : {value}"
        )


class TabLogGenerator:
    """Generate log lines compatible with PLCTabParser."""

    def __init__(self, start_time: datetime) -> None:
        self.current_time = start_time
        self.cells = ["CellA", "CellB", "CellC", "CellD"]
        self.sections = ["Assembly", "Packaging", "Testing", "Welding"]
        self.devices = ["Robot", "Conveyor", "Press", "Loader", "Station"]
        self.modes = ["Main", "Backup", "Aux", "Maintenance"]
        self.locations = [f"Station-{idx:02d}" for idx in range(1, 25)]
        self.statuses = ["OK", "Warn", "Fault", "Info", "Audit"]
        self.flag2_options = ["", "AckPending", "Cleared", "Operator", "Maintenance"]
        self.signals = [
            StructuredSignal(
                name="OUTPUT1:CLAMP_ENGAGED",
                direction="OUT",
                value_type="boolean",
            ),
            StructuredSignal(
                name="OUTPUT2:START",
                direction="OUT",
                value_type="boolean",
            ),
            StructuredSignal(
                name="ANALOG:FORCE",
                direction="OUT",
                value_type="integer",
            ),
            StructuredSignal(
                name="ANALOG:TEMP",
                direction="OUT",
                value_type="integer",
            ),
            StructuredSignal(
                name="STATE:MODE",
                direction="OUT",
                value_type="string",
                string_pool=["AUTO", "MANUAL", "PAUSE", "MAINT"],
            ),
            StructuredSignal(
                name="STATE:PHASE",
                direction="IN",
                value_type="string",
                string_pool=["INIT", "PICK", "PLACE", "CHECK", "COMPLETE"],
            ),
        ]

    def _random_path(self) -> str:
        cell = random.choice(self.cells)
        section = random.choice(self.sections)
        device = random.choice(self.devices)
        mode = random.choice(self.modes)
        unit_index = random.randint(1, 10)
        return f"{cell}/{section}/{device}-{unit_index:02d}@{mode}"

    def next_line(self) -> str:
        self.current_time += timedelta(milliseconds=random.randint(40, 350))
        ts_text = _format_timestamp(self.current_time)
        signal = random.choice(self.signals)
        value = signal.next_value()
        location = random.choice(self.locations)
        status = random.choice(self.statuses)
        extra_flag = random.choice(self.flag2_options)

        parts: List[str] = [
            f"{ts_text} [] {self._random_path()}",
            signal.name,
            signal.direction or "",
            value,
            "",
            location,
            status,
        ]
        if extra_flag:
            parts.append(extra_flag)
        parts.append(ts_text)
        return "\t".join(parts)


def _write_target_sized_log(
    file_path: Path,
    line_factory: Callable[[], str],
    target_size_bytes: int,
) -> int:
    """Write log lines until the target size (in bytes) is reached."""
    if target_size_bytes <= 0:
        raise ValueError("target_size_bytes must be greater than 0")

    bytes_written = 0
    with file_path.open("w", encoding="utf-8") as handle:
        while bytes_written < target_size_bytes:
            line = line_factory()
            handle.write(line + "\n")
            bytes_written += len(line) + 1  # account for newline
    return bytes_written


def generate_bulk_logs(
    output_dir: Path,
    *,
    target_size_mb: float = DEFAULT_BULK_TARGET_MB,
    files_per_parser: int = DEFAULT_BULK_FILES_PER_PARSER,
    start_date: str = DEFAULT_DATE,
    start_time_text: str = DEFAULT_START_TIME,
) -> None:
    """Generate ~target_size_mb log files for each parser."""
    if files_per_parser <= 0:
        raise ValueError("files_per_parser must be greater than 0")
    if target_size_mb <= 0:
        raise ValueError("target_size_mb must be greater than 0")

    target_size_bytes = int(target_size_mb * 1024 * 1024)
    base_start = parse_start_timestamp(start_date, start_time_text)

    parser_generators = {
        "plc_debug": DebugLogGenerator,
        "plc_tab": TabLogGenerator,
    }

    output_dir.mkdir(parents=True, exist_ok=True)

    for parser_name, factory in parser_generators.items():
        for index in range(1, files_per_parser + 1):
            start_offset = base_start + timedelta(days=index - 1)
            generator = factory(start_offset)
            file_path = output_dir / f"{parser_name}_parser_{index:02d}.log"
            size_written = _write_target_sized_log(file_path, generator.next_line, target_size_bytes)
            print(
                f"Generated {file_path} ({size_written / (1024 * 1024):.2f} MB)"
            )


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a random PLC log file.")
    parser.add_argument(
        "--signals",
        type=int,
        default=None,
        help="Number of unique signals to generate (required unless --bulk).",
    )
    parser.add_argument(
        "--lines",
        type=int,
        default=None,
        help="Total number of log lines to output (required unless --bulk).",
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=None,
        help="Total duration in seconds covered by the log (required unless --bulk).",
    )
    parser.add_argument(
        "--start-time",
        default=DEFAULT_START_TIME,
        help=f"Start time of the log (HH:MM:SS). Default: {DEFAULT_START_TIME}",
    )
    parser.add_argument(
        "--date",
        default=DEFAULT_DATE,
        help=f"Date anchor for timestamps (YYYY-MM-DD). Default: {DEFAULT_DATE}",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional output path. If omitted, the log is printed to stdout.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Optional random seed for reproducible output.",
    )
    parser.add_argument(
        "--devices",
        type=int,
        default=None,
        help="Number of devices to simulate. Default distributes signals across up to 5 devices.",
    )
    parser.add_argument(
        "--bulk",
        action="store_true",
        help="Generate ~target-size-mb logs for every parser instead of a single file.",
    )
    parser.add_argument(
        "--target-size-mb",
        type=float,
        default=DEFAULT_BULK_TARGET_MB,
        help=f"Target size (in MB) for each file when using --bulk. Default: {DEFAULT_BULK_TARGET_MB}",
    )
    parser.add_argument(
        "--files-per-parser",
        type=int,
        default=DEFAULT_BULK_FILES_PER_PARSER,
        help=f"Number of files to produce per parser when using --bulk. Default: {DEFAULT_BULK_FILES_PER_PARSER}",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_BULK_OUTPUT_DIR,
        help=f"Output directory for bulk generation. Default: {DEFAULT_BULK_OUTPUT_DIR}",
    )
    args = parser.parse_args(argv)
    if not args.bulk:
        missing = [name for name in ("signals", "lines", "duration") if getattr(args, name) is None]
        if missing:
            missing_flags = ", ".join(f"--{name}" for name in missing)
            parser.error(f"{missing_flags} required unless --bulk is specified")
    return args


def build_signals(count: int, device_ids: List[str]) -> List[SignalSpec]:
    """Create random signal definitions."""
    if count <= 0:
        raise ValueError("signals must be greater than 0")
    if not device_ids:
        raise ValueError("devices must be greater than 0")

    type_choices = ["boolean", "string", "integer"]
    signals: List[SignalSpec] = []

    device_cycle = device_ids[:]
    random.shuffle(device_cycle)

    cycle_length = len(device_cycle)

    for index in range(count):
        if index > 0 and index % cycle_length == 0:
            random.shuffle(device_cycle)

        device_id = device_cycle[index % cycle_length]
        signal_type = random.choice(type_choices)
        signals.append(SignalSpec(
            device_id=device_id,
            name=f"SIGNAL_{index + 1}",
            signal_type=signal_type
        ))

    return signals


def parse_start_timestamp(date_text: str, time_text: str) -> datetime:
    """Combine the provided date and time strings into a datetime object."""
    try:
        combined = f"{date_text} {time_text}"
        return datetime.strptime(combined, "%Y-%m-%d %H:%M:%S")
    except ValueError as exc:
        raise ValueError(
            f"Invalid date/time combination: date='{date_text}', time='{time_text}'"
        ) from exc


def generate_entries(
    signals: List[SignalSpec],
    total_lines: int,
    start_time: datetime,
    duration_seconds: int,
) -> List[str]:
    """Generate random log lines."""
    if total_lines <= 0:
        raise ValueError("lines must be greater than 0")
    if duration_seconds <= 0:
        raise ValueError("duration must be greater than 0 seconds")

    entries = []

    # Ensure each signal appears at least once when possible.
    signals_cycle = []
    if total_lines >= len(signals):
        signals_cycle.extend(signals)
        total_remaining = total_lines - len(signals)
    else:
        total_remaining = total_lines

    for _ in range(total_remaining):
        signals_cycle.append(random.choice(signals))

    timestamps = [
        start_time + timedelta(seconds=random.randint(0, duration_seconds))
        for _ in range(len(signals_cycle))
    ]

    # Sort by timestamp so entries progress in chronological order.
    ordered_pairs = sorted(
        zip(timestamps, signals_cycle),
        key=lambda item: item[0]
    )

    for timestamp, signal in ordered_pairs:
        entries.append(
            f"{signal.device_id} {signal.name} {timestamp.strftime('%H:%M:%S')} "
            f"{signal.next_value()} {signal.signal_type}"
        )

    return entries


def main(argv: Iterable[str] | None = None) -> None:
    args = parse_args(argv)

    if args.seed is not None:
        random.seed(args.seed)

    if args.bulk:
        generate_bulk_logs(
            args.output_dir,
            target_size_mb=args.target_size_mb,
            files_per_parser=args.files_per_parser,
            start_date=args.date,
            start_time_text=args.start_time,
        )
        return

    start_time = parse_start_timestamp(args.date, args.start_time)
    device_count = args.devices if args.devices is not None else min(max(1, args.signals), 5)
    if device_count <= 0:
        raise ValueError("devices must be greater than 0")

    device_ids = [f"{DEFAULT_DEVICE_PREFIX}{index + 1}" for index in range(device_count)]
    signals = build_signals(args.signals, device_ids)
    lines = generate_entries(signals, args.lines, start_time, args.duration)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    else:
        print("\n".join(lines))


if __name__ == "__main__":
    main()
