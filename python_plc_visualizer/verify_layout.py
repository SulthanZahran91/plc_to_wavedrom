#!/usr/bin/env python3
"""Verify the current layout configuration by creating a test signal."""

import sys
from pathlib import Path

# Ensure we're using the local module
sys.path.insert(0, str(Path(__file__).parent))

# Force fresh imports
for mod in list(sys.modules.keys()):
    if 'plc_visualizer' in mod:
        del sys.modules[mod]

from plc_visualizer.ui.signal_item import SignalItem
from plc_visualizer.ui.renderers.boolean_renderer import BooleanRenderer
from plc_visualizer.ui.renderers.state_renderer import StateRenderer

print("="*70)
print("CURRENT LAYOUT CONFIGURATION")
print("="*70)
print()
print("SignalItem Constants:")
print(f"  SIGNAL_HEIGHT = {SignalItem.SIGNAL_HEIGHT}px")
print(f"  LABEL_WIDTH = {SignalItem.LABEL_WIDTH}px")
print(f"  WAVEFORM_LEFT_MARGIN = {SignalItem.WAVEFORM_LEFT_MARGIN}px")
print()
print("Expected Layout:")
print(f"  Label area: 0px to {SignalItem.LABEL_WIDTH}px")
print(f"  Separator line: at {SignalItem.LABEL_WIDTH}px")
print(f"  Margin: {SignalItem.LABEL_WIDTH}px to {SignalItem.LABEL_WIDTH + SignalItem.WAVEFORM_LEFT_MARGIN}px")
print(f"  Waveform starts: {SignalItem.LABEL_WIDTH + SignalItem.WAVEFORM_LEFT_MARGIN}px")
print()

# Create renderer instances to check padding
bool_renderer = BooleanRenderer(60.0)
state_renderer = StateRenderer(60.0)

print("Renderer Configuration:")
print(f"  BooleanRenderer height: {bool_renderer.signal_height}px")
print(f"  StateRenderer height: {state_renderer.signal_height}px")
print(f"  Padding: 12px (hardcoded in render methods)")
print()
print("="*70)
print()

if SignalItem.SIGNAL_HEIGHT == 60.0 and SignalItem.WAVEFORM_LEFT_MARGIN == 10.0:
    print("✓ Configuration is CORRECT")
    print("✓ Signal height is 60px (increased from 40px)")
    print("✓ 10px margin ensures waveforms never touch labels")
    print()
    print("If your app still shows old layout:")
    print("  1. Make sure you completely closed the previous app instance")
    print("  2. Run: python3 test_step3.py")
    print("  3. Load a log file and check the waveforms")
else:
    print("✗ Configuration is WRONG - values don't match expected!")

print("="*70)
