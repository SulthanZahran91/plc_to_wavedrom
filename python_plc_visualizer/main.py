"""PLC Log Visualizer - Main application entry point."""

import sys
from PyQt6.QtWidgets import QApplication
from plc_visualizer.ui import MainWindow


def main():
    """Launch the PLC Log Visualizer application."""
    app = QApplication(sys.argv)
    app.setApplicationName("PLC Log Visualizer")
    app.setOrganizationName("PLC Visualizer")

    # Create and show main window
    window = MainWindow()
    window.showMaximized()

    # Start event loop
    sys.exit(app.exec())


if __name__ == "__main__":
    main()