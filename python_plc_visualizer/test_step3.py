#!/usr/bin/env python3
"""Test script for Step 3: Time Navigation & Zoom functionality."""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from PyQt6.QtWidgets import QApplication
from plc_visualizer.ui.main_window import MainWindow


def main():
    """Run the application to test Step 3 features."""
    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()

    print("\n" + "="*70)
    print("PLC Log Visualizer - Step 3: Time Navigation & Zoom")
    print("="*70)
    print("\nFeatures to test:")
    print("  1. Load a log file using the file upload widget")
    print("  2. Use zoom controls:")
    print("     - Click + and - buttons to zoom in/out")
    print("     - Use the slider to adjust zoom level")
    print("     - Ctrl+Scroll to zoom with mouse wheel")
    print("     - Click 'Reset' to return to full view")
    print("  3. Use pan controls:")
    print("     - Click arrow buttons to pan left/right")
    print("     - Drag the scrollbar to navigate")
    print("     - Enter time in HH:MM:SS format and click 'Go'")
    print("  4. Use time range selector:")
    print("     - Drag the blue handles to adjust visible range")
    print("     - Drag the blue region to pan")
    print("  5. Verify viewport culling:")
    print("     - Waveforms should update when zooming/panning")
    print("     - Time axis should show only visible time range")
    print("\nExpected behavior:")
    print("  ✓ Zoom level displays correctly (e.g., 'Zoom: 2.5x')")
    print("  ✓ Zooming maintains center point of viewport")
    print("  ✓ Panning is constrained to log time range")
    print("  ✓ Time range selector shows current viewport")
    print("  ✓ All controls are synchronized")
    print("="*70 + "\n")

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
