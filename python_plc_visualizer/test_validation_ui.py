#!/usr/bin/env python3
"""Test UI for LogTableWindow with validation controls.

Run this to see the validation toolbar in action.
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path

from PySide6.QtWidgets import QApplication

from plc_visualizer.models import LogEntry, ParsedLog, SignalType
from plc_visualizer.utils import SignalData, SignalState
from plc_visualizer.ui.log_table_window import LogTableWindow


def create_sample_log() -> tuple[ParsedLog, list[SignalData]]:
    """Create sample log data with carrier handshake."""
    base_time = datetime(2025, 10, 24, 10, 0, 0)
    device_id = "B1ACNV13301-104"

    entries = [
        LogEntry(device_id, "CARRIER_DETECTED", base_time, True, SignalType.BOOLEAN),
        LogEntry(device_id, "CARRIER_ID_READ", base_time + timedelta(seconds=0.5), "SET", SignalType.STRING),
        LogEntry(device_id, "CARRIER_GIVEN_MOVE", base_time + timedelta(seconds=1.0), True, SignalType.BOOLEAN),
        LogEntry(device_id, "CONVEYOR_MOVE", base_time + timedelta(seconds=1.3), True, SignalType.BOOLEAN),
        LogEntry(device_id, "CARRIER_DETECTED", base_time + timedelta(seconds=8.0), False, SignalType.BOOLEAN),
        LogEntry(device_id, "CONVEYOR_MOVE", base_time + timedelta(seconds=9.0), False, SignalType.BOOLEAN),
    ]

    parsed_log = ParsedLog(
        entries=entries,
        signals={f"{device_id}::{e.signal_name}" for e in entries},
        devices={device_id},
        time_range=(base_time, base_time + timedelta(seconds=9.0))
    )

    # Create signal data
    signal_data_list = []
    signals_by_name = {}
    for entry in entries:
        if entry.signal_name not in signals_by_name:
            signals_by_name[entry.signal_name] = []
        signals_by_name[entry.signal_name].append(entry)

    for signal_name, signal_entries in signals_by_name.items():
        states = []
        for i, entry in enumerate(signal_entries):
            end_time = signal_entries[i + 1].timestamp if i + 1 < len(signal_entries) else base_time + timedelta(seconds=10.0)
            states.append(SignalState(
                start_time=entry.timestamp,
                end_time=end_time,
                value=entry.value,
                start_offset=(entry.timestamp - base_time).total_seconds(),
                end_offset=(end_time - base_time).total_seconds()
            ))

        signal_data_list.append(SignalData(
            name=signal_name,
            device_id=device_id,
            key=f"{device_id}::{signal_name}",
            signal_type=signal_entries[0].signal_type,
            states=states,
            _entries_count=len(signal_entries)
        ))

    return parsed_log, signal_data_list


def main():
    """Run the UI test."""
    print("=" * 80)
    print("LOGTABLEWINDOW VALIDATION UI TEST")
    print("=" * 80)
    print("\nInstructions:")
    print("1. Click 'Load Rules...' button")
    print("2. Select: config/signal_validation_rules.yaml")
    print("3. Click 'Run Validation' button")
    print("4. Check console output for violations")
    print("\nSample data includes a perfect carrier handshake sequence.")
    print("=" * 80 + "\n")

    app = QApplication(sys.argv)

    # Create window
    window = LogTableWindow()

    # Load sample data
    parsed_log, signal_data = create_sample_log()
    window.set_data(parsed_log, signal_data)

    # Show window
    window.resize(1000, 600)
    window.show()

    print("Window opened! Use the validation toolbar at the top.\n")

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
