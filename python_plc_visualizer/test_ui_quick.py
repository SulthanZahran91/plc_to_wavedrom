"""Quick test to verify UI components work correctly."""

import sys
from pathlib import Path

# Test imports
try:
    from PyQt6.QtWidgets import QApplication
    from plc_visualizer.ui import MainWindow
    from plc_visualizer.parsers import parser_registry
    print("✓ All imports successful")
except ImportError as e:
    print(f"✗ Import error: {e}")
    sys.exit(1)

# Test parser with sample file
sample_file = Path(__file__).parent / "test_data" / "sample.log"
if sample_file.exists():
    print(f"✓ Sample file found: {sample_file}")

    result = parser_registry.parse(str(sample_file))
    if result.success:
        print(f"✓ Parser works: {result.data.entry_count} entries, "
              f"{result.data.signal_count} signals")
        if result.has_errors:
            print(f"  ⚠ {result.error_count} parsing error(s)")
    else:
        print(f"✗ Parser failed: {result.errors}")
        sys.exit(1)
else:
    print(f"✗ Sample file not found: {sample_file}")
    sys.exit(1)

# Test UI creation (without showing)
print("Testing UI creation...")
app = QApplication(sys.argv)
window = MainWindow()
print(f"✓ MainWindow created successfully")

# Verify UI components exist
assert window.upload_widget is not None, "upload_widget missing"
assert window.stats_widget is not None, "stats_widget missing"
assert window.data_table is not None, "data_table missing"
assert window.progress_bar is not None, "progress_bar missing"
print("✓ All UI components present")

print("\n" + "="*50)
print("✓ ALL TESTS PASSED")
print("="*50)
print("\nTo run the full application, execute:")
print("  python main.py")
