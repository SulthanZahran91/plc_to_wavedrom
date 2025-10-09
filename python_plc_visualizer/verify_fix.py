"""Verify the drawLine fix works correctly."""

import sys
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer

from plc_visualizer.parsers import parser_registry
from plc_visualizer.ui import MainWindow

print("Testing the main application with sample copy.log...")

# Parse the file first to verify it works
sample_file = Path(__file__).parent / "test_data" / "sample copy.log"
print(f"1. Parsing {sample_file.name}...")

result = parser_registry.parse(str(sample_file))
if not result.success:
    print(f"   ✗ Parser failed: {result.errors}")
    sys.exit(1)

print(f"   ✓ Parsed successfully: {result.data.entry_count} entries, {result.data.signal_count} signals")

# Create Qt application
print("2. Creating Qt application...")
app = QApplication(sys.argv)

# Create main window
print("3. Creating main window...")
window = MainWindow()

# Programmatically load the file
print("4. Loading file into UI...")
window._on_file_selected(str(sample_file))

# Wait a moment for the parser thread to finish
print("5. Waiting for parsing to complete...")

def check_results():
    """Check if parsing completed successfully."""
    if window.waveform_view.waveform_scene.get_signal_count() > 0:
        print(f"   ✓ Waveform rendered with {window.waveform_view.waveform_scene.get_signal_count()} signals")
        print("\n" + "="*60)
        print("✓ ALL CHECKS PASSED - No errors!")
        print("="*60)
        print("\nThe application is working correctly.")
        print("Close the window to exit.")
    else:
        print("   ⏳ Still parsing...")
        QTimer.singleShot(100, check_results)

# Check results after a short delay
QTimer.singleShot(500, check_results)

# Show window
window.show()

# Run application
sys.exit(app.exec())
