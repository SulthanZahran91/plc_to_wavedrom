"""Test script for Step 2: Waveform Visualization."""

import sys
from pathlib import Path

# Test imports
print("Testing Step 2 Components...")
print("="*60)

try:
    from PyQt6.QtWidgets import QApplication
    from plc_visualizer.ui import WaveformView
    from plc_visualizer.parsers import parser_registry
    from plc_visualizer.utils import process_signals_for_waveform
    from plc_visualizer.ui.renderers import BooleanRenderer, StateRenderer
    print("✓ All imports successful")
except ImportError as e:
    print(f"✗ Import error: {e}")
    sys.exit(1)

# Test parser with sample file
sample_file = Path(__file__).parent / "test_data" / "sample.log"
if not sample_file.exists():
    print(f"✗ Sample file not found: {sample_file}")
    sys.exit(1)

print(f"✓ Sample file found: {sample_file}")

# Parse the file
result = parser_registry.parse(str(sample_file))
if not result.success:
    print(f"✗ Parser failed: {result.errors}")
    sys.exit(1)

print(f"✓ Parser works: {result.data.entry_count} entries, "
      f"{result.data.signal_count} signals")

# Test signal processing
signal_data_list = process_signals_for_waveform(result.data)
print(f"✓ Signal processing works: {len(signal_data_list)} signals processed")

for signal_data in signal_data_list:
    print(f"  - {signal_data.name}: {signal_data.signal_type.value}, "
          f"{len(signal_data.states)} states")

# Test renderers
boolean_renderer = BooleanRenderer()
state_renderer = StateRenderer()
print("✓ Renderers created successfully")

# Test UI creation
app = QApplication(sys.argv)

# Test WaveformView
waveform_view = WaveformView()
print("✓ WaveformView created")

# Set data
waveform_view.set_data(result.data)
print("✓ Data loaded into waveform view")

# Check scene
scene = waveform_view.waveform_scene
print(f"✓ Scene created with {scene.get_signal_count()} signals")

# Verify all components exist
assert scene.time_axis is not None, "Time axis missing"
assert len(scene.signal_items) > 0, "No signal items"
print(f"✓ Time axis and {len(scene.signal_items)} signal items rendered")

print("\n" + "="*60)
print("✓ ALL STEP 2 TESTS PASSED")
print("="*60)
print("\nStep 2 Implementation Complete!")
print("\nFeatures:")
print("  ✓ Waveform data processing utilities")
print("  ✓ Boolean renderer (square waves)")
print("  ✓ State renderer (labeled boxes for strings/integers)")
print("  ✓ Time axis with labels")
print("  ✓ Signal items with name labels")
print("  ✓ Waveform scene and view")
print("  ✓ Integration into main window")
print("\nTo run the full application:")
print("  python main.py")
print("\nThen drag and drop 'test_data/sample.log' to see the waveforms!")
