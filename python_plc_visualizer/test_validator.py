#!/usr/bin/env python3
"""Test script for signal validator.

This script demonstrates the signal validator with sample log data
showing various violations.
"""

from datetime import datetime, timedelta
from pathlib import Path

from plc_visualizer.models import LogEntry, ParsedLog, SignalType
from plc_visualizer.utils import SignalData, SignalState
from plc_visualizer.validation import SignalValidator


def create_test_log_perfect_sequence() -> tuple[ParsedLog, list[SignalData]]:
    """Create a test log with perfect carrier handshake sequence."""
    base_time = datetime(2025, 10, 24, 10, 0, 0)
    device_id = "B1ACNV13301-104"

    # Perfect sequence
    entries = [
        # Step 1: Carrier detected
        LogEntry(device_id, "CARRIER_DETECTED", base_time, True, SignalType.BOOLEAN),
        # Step 2: ID read within 2s
        LogEntry(device_id, "CARRIER_ID_READ", base_time + timedelta(seconds=0.5), "SET", SignalType.STRING),
        # Step 3: Given move within 1s
        LogEntry(device_id, "CARRIER_GIVEN_MOVE", base_time + timedelta(seconds=1.0), True, SignalType.BOOLEAN),
        # Step 4: Conveyor moves within 0.5s
        LogEntry(device_id, "CONVEYOR_MOVE", base_time + timedelta(seconds=1.3), True, SignalType.BOOLEAN),
        # Step 5: Carrier leaves within 10s
        LogEntry(device_id, "CARRIER_DETECTED", base_time + timedelta(seconds=8.0), False, SignalType.BOOLEAN),
        # Step 6: Conveyor stops within 2s
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


def create_test_log_timeout_violation() -> tuple[ParsedLog, list[SignalData]]:
    """Create a test log with timeout violation."""
    base_time = datetime(2025, 10, 24, 10, 0, 0)
    device_id = "B1ACNV13302-104"

    # Timeout violation: ID read takes too long (3s instead of max 2s)
    entries = [
        LogEntry(device_id, "CARRIER_DETECTED", base_time, True, SignalType.BOOLEAN),
        LogEntry(device_id, "CARRIER_ID_READ", base_time + timedelta(seconds=3.0), "SET", SignalType.STRING),  # TOO LATE!
        LogEntry(device_id, "CARRIER_GIVEN_MOVE", base_time + timedelta(seconds=4.0), True, SignalType.BOOLEAN),
        LogEntry(device_id, "CONVEYOR_MOVE", base_time + timedelta(seconds=4.3), True, SignalType.BOOLEAN),
    ]

    return _build_log_and_signals(device_id, base_time, entries)


def create_test_log_out_of_order() -> tuple[ParsedLog, list[SignalData]]:
    """Create a test log with out-of-order violation."""
    base_time = datetime(2025, 10, 24, 10, 0, 0)
    device_id = "B1ACNV13303-104"

    # Out of order: CONVEYOR_MOVE before CARRIER_GIVEN_MOVE
    entries = [
        LogEntry(device_id, "CARRIER_DETECTED", base_time, True, SignalType.BOOLEAN),
        LogEntry(device_id, "CARRIER_ID_READ", base_time + timedelta(seconds=0.5), "SET", SignalType.STRING),
        LogEntry(device_id, "CONVEYOR_MOVE", base_time + timedelta(seconds=1.0), True, SignalType.BOOLEAN),  # WRONG! Skipped step 3
        LogEntry(device_id, "CARRIER_GIVEN_MOVE", base_time + timedelta(seconds=1.5), True, SignalType.BOOLEAN),
    ]

    return _build_log_and_signals(device_id, base_time, entries)


def create_test_log_same_step() -> tuple[ParsedLog, list[SignalData]]:
    """Create a test log demonstrating same-step feature (unordered)."""
    base_time = datetime(2025, 10, 24, 10, 0, 0)
    device_id = "B1ACDV14001-104"

    # Diverter init with three signals at step 2 (can be any order)
    entries = [
        LogEntry(device_id, "INIT_START", base_time, True, SignalType.BOOLEAN),
        # These three can happen in any order (all step 2)
        LogEntry(device_id, "MOTOR_CALIBRATED", base_time + timedelta(seconds=1.0), True, SignalType.BOOLEAN),  # 3rd in YAML
        LogEntry(device_id, "SENSOR_A_READY", base_time + timedelta(seconds=2.0), True, SignalType.BOOLEAN),    # 1st in YAML
        LogEntry(device_id, "SENSOR_B_READY", base_time + timedelta(seconds=3.0), True, SignalType.BOOLEAN),    # 2nd in YAML
        # Step 3 only after all step 2's complete
        LogEntry(device_id, "INIT_COMPLETE", base_time + timedelta(seconds=4.0), True, SignalType.BOOLEAN),
    ]

    return _build_log_and_signals(device_id, base_time, entries)


def _build_log_and_signals(device_id: str, base_time: datetime, entries: list[LogEntry]) -> tuple[ParsedLog, list[SignalData]]:
    """Helper to build ParsedLog and SignalData from entries."""
    parsed_log = ParsedLog(
        entries=entries,
        signals={f"{device_id}::{e.signal_name}" for e in entries},
        devices={device_id},
        time_range=(base_time, entries[-1].timestamp) if entries else None
    )

    signal_data_list = []
    signals_by_name = {}
    for entry in entries:
        if entry.signal_name not in signals_by_name:
            signals_by_name[entry.signal_name] = []
        signals_by_name[entry.signal_name].append(entry)

    for signal_name, signal_entries in signals_by_name.items():
        states = []
        for i, entry in enumerate(signal_entries):
            end_time = signal_entries[i + 1].timestamp if i + 1 < len(signal_entries) else base_time + timedelta(seconds=20.0)
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


def run_test(name: str, parsed_log: ParsedLog, signal_data_list: list[SignalData], validator: SignalValidator):
    """Run validation test and print results."""
    print(f"\n{'=' * 80}")
    print(f"TEST: {name}")
    print(f"{'=' * 80}")

    violations = validator.validate_all(parsed_log, signal_data_list)

    if not violations:
        print("✅ NO VIOLATIONS - Sequence is perfect!")
    else:
        for device_id, device_violations in violations.items():
            print(f"\nDevice: {device_id}")
            print("-" * 80)
            for violation in device_violations:
                print(f"  {violation}")


def main():
    """Run all tests."""
    print("\n" + "=" * 80)
    print("SIGNAL VALIDATOR TEST SUITE")
    print("=" * 80)

    # Load rules
    rules_path = Path(__file__).parent / "config" / "signal_validation_rules.yaml"
    print(f"\nLoading rules from: {rules_path}")

    try:
        validator = SignalValidator(rules_path)
        print("✅ Rules loaded successfully")
    except Exception as e:
        print(f"❌ Failed to load rules: {e}")
        import traceback
        traceback.print_exc()
        return

    # Test 1: Perfect sequence
    log, signals = create_test_log_perfect_sequence()
    run_test("Perfect Carrier Handshake", log, signals, validator)

    # Test 2: Timeout violation
    log, signals = create_test_log_timeout_violation()
    run_test("Timeout Violation (ID read too slow)", log, signals, validator)

    # Test 3: Out of order
    log, signals = create_test_log_out_of_order()
    run_test("Out-of-Order Violation (skipped step)", log, signals, validator)

    # Test 4: Same step (unordered)
    log, signals = create_test_log_same_step()
    run_test("Same-Step Feature (signals in any order)", log, signals, validator)

    print(f"\n{'=' * 80}")
    print("ALL TESTS COMPLETE")
    print(f"{'=' * 80}\n")


if __name__ == "__main__":
    main()
