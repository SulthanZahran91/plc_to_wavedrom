# example_main.py
"""
Basic demo of the map viewer package.

PREREQUISITE: You need a test.xml file containing your conveyor map data.
Place your XML file as 'test.xml' in the project root, or pass a path:

    python example_main.py path/to/your.xml

The XML should contain Object elements with attributes like:
- name, type, Size, Location, UnitId, etc.
"""
import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QDockWidget, QWidget
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

from map_viewer import MapParser, MapRenderer, MediaControls

class DemoWindow(QMainWindow):
    """
    Demo composition:
      - Central: MapRenderer
      - Bottom Dock: MediaControls (UI only)
      - Parser: MapParser
      - Demo signal: emits stateChanged(UnitId, QColor) periodically
    """
    def __init__(self, xml_path: str = "test.xml"):
        super().__init__()
        self.setWindowTitle("Conveyor Map Viewer (Demo)")
        self.resize(1200, 800)

        # Core widgets
        self.renderer = MapRenderer()
        self.setCentralWidget(self.renderer)

        self._build_media_dock()

        # Parser and connections
        self.parser = MapParser()
        self.parser.objectsParsed.connect(self.renderer.set_objects)
        self.parser.stateChanged.connect(self.renderer.update_rect_color_by_unit)

        # Load once
        objects = self.parser.parse_file(xml_path)

        # Collect UnitIds for demo (rectangles will have UnitId indexed)
        unit_ids = [v.get("UnitId") for v in (objects or {}).values() if v.get("UnitId")]
        unit_ids = list(dict.fromkeys(unit_ids))  # de-dup while keeping order

        # Start demo state changes if any UnitIds exist
        if unit_ids:
            self.parser.start_demo_state_changes(
                unit_ids=unit_ids[:8],  # limit demo to first few
                colors=[QColor("#00C853"), QColor("#FFD600"), QColor("#D50000")]
            )

    def _build_media_dock(self):
        dock = QDockWidget(self)
        dock.setObjectName("MediaPlayerDock")
        dock.setAllowedAreas(Qt.DockWidgetArea.BottomDockWidgetArea)
        dock.setTitleBarWidget(QWidget(dock))  # hide title bar

        self.media_controls = MediaControls(dock)
        dock.setWidget(self.media_controls)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, dock)

if __name__ == '__main__':
    import os

    # Check if XML file is provided as argument or exists as test.xml
    xml_file = sys.argv[1] if len(sys.argv) > 1 else "test.xml"

    if not os.path.exists(xml_file):
        print(f"Error: XML file '{xml_file}' not found!")
        print("\nPlease provide a valid XML file path:")
        print(f"  python {sys.argv[0]} path/to/your.xml")
        print("\nOr place your XML file as 'test.xml' in the current directory.")
        sys.exit(1)

    app = QApplication(sys.argv)
    window = DemoWindow(xml_path=xml_file)
    window.show()
    sys.exit(app.exec())
