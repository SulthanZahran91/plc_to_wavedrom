#!/usr/bin/env python3
"""Check current signal size configuration."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from plc_visualizer.ui.signal_item import SignalItem
from plc_visualizer.ui.waveform_scene import WaveformScene
from plc_visualizer.ui.renderers.boolean_renderer import BooleanRenderer
from plc_visualizer.ui.renderers.state_renderer import StateRenderer

print("="*70)
print("Current Signal Size Configuration")
print("="*70)
print()
print(f"SignalItem.SIGNAL_HEIGHT:     {SignalItem.SIGNAL_HEIGHT} pixels")
print(f"WaveformScene.SIGNAL_HEIGHT:  {WaveformScene.SIGNAL_HEIGHT} pixels")
print()
print("Renderer Instances:")
bool_r = BooleanRenderer(60.0)
state_r = StateRenderer(60.0)
print(f"  BooleanRenderer.signal_height: {bool_r.signal_height} pixels")
print(f"  StateRenderer.signal_height:   {state_r.signal_height} pixels")
print()
print("Padding: 12.0 pixels (hardcoded in render methods)")
print()
print("Expected waveform area per signal: 60px height, 12px padding top/bottom")
print("Actual drawing area: 36px (60 - 12 - 12)")
print()
print("="*70)
print("If your app still shows 40px signals, you need to RESTART the app!")
print("="*70)
