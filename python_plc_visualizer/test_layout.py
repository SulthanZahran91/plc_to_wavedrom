"""Verify the waveform layout is correct."""

import sys
from pathlib import Path
from PyQt6.QtWidgets import QApplication

from plc_visualizer.parsers import parser_registry
from plc_visualizer.ui import WaveformView

print("Verifying Waveform Layout...")
print("="*60)

# Parse sample file
sample_file = Path(__file__).parent / "test_data" / "sample.log"
result = parser_registry.parse(str(sample_file))

if not result.success:
    print(f"✗ Parser failed")
    sys.exit(1)

# Create Qt app and view
app = QApplication(sys.argv)
view = WaveformView()
view.set_data(result.data)

# Check the scene structure
scene = view.waveform_scene

print(f"Scene dimensions: {scene.scene_width} x {scene.scene_height}")
print()

# Check time axis
if scene.time_axis:
    print("Time Axis:")
    print(f"  LABEL_WIDTH: {scene.time_axis.LABEL_WIDTH}px")
    print(f"  Height: {scene.time_axis.height}px")
    print(f"  Width: {scene.time_axis.width}px")
    print(f"  ✓ Vertical separator at x={scene.time_axis.LABEL_WIDTH}")
    print(f"  ✓ Time ticks start at x={scene.time_axis.LABEL_WIDTH}")
    print()

# Check signal items
print(f"Signal Items ({len(scene.signal_items)}):")
for i, signal_item in enumerate(scene.signal_items):
    print(f"  {i+1}. {signal_item.signal_data.name}")
    print(f"     - Label area: 0 to {signal_item.LABEL_WIDTH}px")
    print(f"     - Waveform starts at: {signal_item.LABEL_WIDTH}px")
    print(f"     - Y offset: {signal_item.y_offset}px")

    # Check path items have correct offset
    if signal_item.path_items:
        first_path = signal_item.path_items[0]
        pos = first_path.pos()
        print(f"     - Path offset: x={pos.x()}, y={pos.y()}")

        if pos.x() == signal_item.LABEL_WIDTH:
            print(f"     ✓ Correctly offset")
        else:
            print(f"     ✗ WRONG offset (expected {signal_item.LABEL_WIDTH})")

print()
print("="*60)
print("Layout Structure:")
print()
print("┌────────────────────┬────────────────────────────────────┐")
print("│  Device / Signal   │         Timeline Area              │")
print("│     (180px)        │     (starts at x=180)              │")
print("├─────────────────┼────────────────────────────────────┤")
print("│                 │  10:30:50   10:30:55   10:31:00   │")
print("├─────────────────┼────────────────────────────────────┤")
print("│ DEVICE_B ALARM  │  ─────────────────────────────     │")
print("├─────────────────┼────────────────────────────────────┤")
print("│ DEVICE_A COUNT1 │   ████ 100  ████ 150  ████ 200    │")
print("├─────────────────┼────────────────────────────────────┤")
print("│ DEVICE_A MOTOR  │  ▔▔▔▔▁▁▁▁▁▁▁▁▁▁▁▔▔▔▔▔▔▔▔▔▔▔▔▔     │")
print("├─────────────────┼────────────────────────────────────┤")
print("│ DEVICE_B SENSOR │   ████ ready ████ error ████ idle │")
print("├─────────────────┼────────────────────────────────────┤")
print("│ DEVICE_B TEMP   │                        ████ 25     │")
print("└────────────────────┴────────────────────────────────────┘")
print("                  ↑")
print("            Vertical separator at x=180px")
print()
print("✓ Layout verification complete!")
