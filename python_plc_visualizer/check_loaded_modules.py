#!/usr/bin/env python3
"""Check which version of the modules are actually loaded."""

import sys
from pathlib import Path

print("="*70)
print("MODULE LOADING DIAGNOSTIC")
print("="*70)
print()
print(f"Python executable: {sys.executable}")
print(f"Python version: {sys.version}")
print()

# Check where modules are loaded from
try:
    import plc_visualizer
    print(f"plc_visualizer loaded from: {plc_visualizer.__file__}")

    from plc_visualizer.ui import signal_item
    print(f"signal_item loaded from: {signal_item.__file__}")

    from plc_visualizer.ui import signal_label_item
    print(f"signal_label_item loaded from: {signal_label_item.__file__}")

    print()
    print("Checking if modules are from local directory...")
    expected_path = Path(__file__).parent / "plc_visualizer"
    actual_path = Path(plc_visualizer.__file__).parent

    if expected_path.resolve() == actual_path.resolve():
        print("✓ Modules are loaded from LOCAL directory")
    else:
        print("✗ PROBLEM: Modules are loaded from a DIFFERENT location!")
        print(f"  Expected: {expected_path}")
        print(f"  Actual: {actual_path}")

    print()
    print("Checking SignalItem attributes...")
    from plc_visualizer.ui.signal_item import SignalItem

    # Check if it has the old attributes (LABEL_WIDTH, WAVEFORM_LEFT_MARGIN)
    if hasattr(SignalItem, 'LABEL_WIDTH'):
        print("✗ SignalItem still has LABEL_WIDTH (OLD VERSION)")
    else:
        print("✓ SignalItem doesn't have LABEL_WIDTH (NEW VERSION)")

    if hasattr(SignalItem, 'WAVEFORM_LEFT_MARGIN'):
        print("✗ SignalItem still has WAVEFORM_LEFT_MARGIN (OLD VERSION)")
    else:
        print("✓ SignalItem doesn't have WAVEFORM_LEFT_MARGIN (NEW VERSION)")

    print()
    print("Checking SignalLabelItem exists...")
    try:
        from plc_visualizer.ui.signal_label_item import SignalLabelItem
        print("✓ SignalLabelItem exists (NEW VERSION)")
        print(f"  LABEL_WIDTH: {SignalLabelItem.LABEL_WIDTH}")
        print(f"  SIGNAL_HEIGHT: {SignalLabelItem.SIGNAL_HEIGHT}")
    except ImportError as e:
        print(f"✗ SignalLabelItem NOT FOUND (OLD VERSION): {e}")

except Exception as e:
    print(f"Error loading modules: {e}")
    import traceback
    traceback.print_exc()

print()
print("="*70)
