"""Test with specific file to catch runtime errors."""

import sys
from pathlib import Path
from PyQt6.QtWidgets import QApplication

from plc_visualizer.parsers import parser_registry
from plc_visualizer.ui import WaveformView

# Parse the file
sample_file = Path(__file__).parent / "test_data" / "sample copy.log"
print(f"Testing with: {sample_file}")

result = parser_registry.parse(str(sample_file))
if not result.success:
    print(f"✗ Parser failed: {result.errors}")
    sys.exit(1)

print(f"✓ Parsed: {result.data.entry_count} entries, {result.data.signal_count} signals")

# Create Qt app and view
app = QApplication(sys.argv)
view = WaveformView()
view.set_data(result.data)
print("✓ Waveform view created and data loaded")

# Show the view
view.resize(1000, 600)
view.show()
print("✓ View shown - check for visual errors")

sys.exit(app.exec())
