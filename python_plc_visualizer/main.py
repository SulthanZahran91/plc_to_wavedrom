"""PLC Log Visualizer - Main application entry point."""

import sys

from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtWidgets import QApplication

from plc_visualizer.ui import MainWindow


def _show_window(window: MainWindow, app: QApplication):
    """Show the main window with Wayland-friendly maximization."""
    window.show()  # ensure initial buffer matches configure

    platform_name = app.platformName().lower()
    print(f"[Startup] Qt platform: {platform_name}")
    if "wayland" in platform_name:
        def _size_without_maximizing():
            handle = window.windowHandle()
            screen = window.screen()
            print(f"[Startup] (Wayland) handle={handle}, screen={screen}")
            if handle and screen:
                geom = screen.availableGeometry()
                margin_w = min(max(geom.width() // 12, 48), geom.width())
                margin_h = min(max(geom.height() // 10, 96), geom.height())
                target = geom.adjusted(0, 0, -margin_w, -margin_h)
                print(f"[Startup] (Wayland) applying relaxed geometry: {target}")
                window.setMaximumSize(target.width(), target.height())
                window.setMinimumSize(960, 720)
                window.setGeometry(target)
                if handle:
                    handle.setMaximumSize(target.size())
            else:
                print("[Startup] (Wayland) missing handle/screen; leaving default size")

        QTimer.singleShot(0, _size_without_maximizing)
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
