"""Utility script to generate random PLC log files.

The generated log matches the format used by the visualizer:
    DEVICE_ID SIGNAL_NAME HH:MM:SS value type

Example usage:
    python generate_random_log.py --signals 5 --devices 2 --lines 200 \\
        --duration 1800 --output random.log
"""

from __future__ import annotations

import argparse
import random
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable, List


DEFAULT_START_TIME = "10:00:00"
DEFAULT_DATE = "2024-01-01"
DEFAULT_DEVICE_PREFIX = "DEVICE_"
STRING_POOL = [
    "ready",
    "idle",
    "error",
    "running",
    "paused",
    "complete",
    "starting",
    "stopped",
]


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
            pool = STRING_POOL
            if self.last_value in pool and len(pool) > 1:
                pool = [word for word in pool if word != self.last_value]
            value = random.choice(pool)

        self.last_value = value
        return value


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a random PLC log file.")
    parser.add_argument(
        "--signals",
        type=int,
        required=True,
        help="Number of unique signals to generate.",
    )
    parser.add_argument(
        "--lines",
        type=int,
        required=True,
        help="Total number of log lines to output.",
    )
    parser.add_argument(
        "--duration",
        type=int,
        required=True,
        help="Total duration in seconds covered by the log.",
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
    return parser.parse_args(argv)


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
