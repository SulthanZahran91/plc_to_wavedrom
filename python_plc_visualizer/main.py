"""PLC Log Visualizer - Main application entry point."""

import sys

from PyQt6.QtCore import QTimer, Qt, QSize
from PyQt6.QtWidgets import QApplication

from plc_visualizer.ui import MainWindow


def _show_window(window: MainWindow, app: QApplication):
    """Show the main window with Wayland-friendly maximization."""
    window.show()  # ensure initial buffer matches configure

    platform_name = app.platformName().lower()
    if "wayland" in platform_name:
        def _maximize_on_wayland():
            handle = window.windowHandle()
            screen = window.screen()
            if handle and screen:
                geometry = screen.availableGeometry()
                handle.setMaximumSize(geometry.size())
                handle.resize(geometry.size())
                window.setGeometry(geometry)
                window.setWindowState(Qt.WindowState.WindowMaximized)
                # Allow user resizing after the compositor settles.
                def _clear_limits(h=handle):
                    if h:
                        h.setMaximumSize(QSize())
                QTimer.singleShot(100, _clear_limits)
            else:
                window.setWindowState(Qt.WindowState.WindowMaximized)

        # Delay until the window handle exists and compositor has configured us.
        QTimer.singleShot(0, _maximize_on_wayland)
    else:
        window.showMaximized()


def main():
    """Launch the PLC Log Visualizer application."""
    app = QApplication(sys.argv)
    app.setApplicationName("PLC Log Visualizer")
    app.setOrganizationName("PLC Visualizer")

    window = MainWindow()
    _show_window(window, app)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
