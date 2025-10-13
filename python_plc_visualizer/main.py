"""PLC Log Visualizer - Main application entry point."""

import sys
from PyQt6.QtWidgets import QApplication
from plc_visualizer.ui import MainWindow
from qt_material import apply_stylesheet


def main():
    """Launch the PLC Log Visualizer application."""
    app = QApplication(sys.argv)
    app.setApplicationName("PLC Log Visualizer")
    app.setOrganizationName("PLC Visualizer")

    # setup stylesheet
    apply_stylesheet(app, theme='dark_teal.xml')

    # Create and show main window
    window = MainWindow()
    window.show()

    # Start event loop
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
