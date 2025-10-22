# example_main_integration.py
"""
Full integration demo showing signal-driven color updates.

PREREQUISITES:
1. test.xml - Your conveyor map data (same as example_main.py)
2. mappings_and_rules.yaml - Configuration for device mapping and color rules

This demo shows how to:
- Map device IDs to UnitIds in the XML
- Apply color rules based on signal values
- Integrate with the state model for real-time updates
"""
import sys
import time
import os
from PySide6.QtWidgets import QApplication, QMainWindow, QDockWidget, QWidget
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor

from map_viewer import MapParser, MapRenderer, MediaControls
from map_viewer.state_model import UnitStateModel, SignalEvent
from map_viewer.config_loader import load_mapping_and_policy

class DemoWindow(QMainWindow):
    def __init__(self, xml_path: str = "test.xml", yaml_cfg: str = "mappings_and_rules.yaml"):
        super().__init__()
        self.setWindowTitle("Conveyor Map Viewer — Signal Integration Demo")
        self.resize(1200, 800)

        # UI
        self.renderer = MapRenderer()
        self.setCentralWidget(self.renderer)
        self._build_media_dock()

        # Parser → renders static layout
        self.parser = MapParser()
        self.parser.objectsParsed.connect(self.renderer.set_objects)
        objects = self.parser.parse_file(xml_path)

        # Device→Unit + Color rules → State model → Renderer color updates
        device_map, color_policy = load_mapping_and_policy(yaml_cfg)
        self.state_model = UnitStateModel(device_map, color_policy)
        self.state_model.stateChanged.connect(self.renderer.update_rect_color_by_unit)

        # --- Demo signal generator (replace with your real stream) ---
        # Try to pick a UnitId from XML to drive a visible change:
        self._demo_unit = None
        for v in objects.values():
            if v.get("UnitId"):
                self._demo_unit = v["UnitId"]; break
        # If we have a UnitId, synthesize device_id that matches YAML pattern:
        self._demo_device = f"{self._demo_unit}@D19" if self._demo_unit else "B1ACNV13301-104@D19"

        self._tick = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._emit_fake_signal)
        self._timer.start(800)

    def _emit_fake_signal(self):
        # Flip Signal A between 1 and 2 to toggle Yellow/Green
        self._tick ^= 1
        ev = SignalEvent(
            device_id=self._demo_device,
            signal_name="A",
            value=1 if self._tick else 2,
            timestamp=time.time(),
        )
        self.state_model.on_signal(ev)

    def _build_media_dock(self):
        dock = QDockWidget(self)
        dock.setObjectName("MediaPlayerDock")
        dock.setAllowedAreas(Qt.DockWidgetArea.BottomDockWidgetArea)
        dock.setTitleBarWidget(QWidget(dock))
        self.media_controls = MediaControls(dock)
        dock.setWidget(self.media_controls)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, dock)

if __name__ == "__main__":
    # Check prerequisites
    xml_file = sys.argv[1] if len(sys.argv) > 1 else "test.xml"
    yaml_file = sys.argv[2] if len(sys.argv) > 2 else os.path.join(
        os.path.dirname(__file__), "mappings_and_rules.yaml"
    )

    if not os.path.exists(xml_file):
        print(f"Error: XML file '{xml_file}' not found!")
        print("\nUsage:")
        print(f"  python {sys.argv[0]} [xml_file] [yaml_config]")
        print("\nDefaults:")
        print("  xml_file: test.xml")
        print(f"  yaml_config: {yaml_file}")
        sys.exit(1)

    if not os.path.exists(yaml_file):
        print(f"Error: Config file '{yaml_file}' not found!")
        print("\nPlease create a mappings_and_rules.yaml file (see README.md for format)")
        sys.exit(1)

    app = QApplication(sys.argv)
    w = DemoWindow(xml_path=xml_file, yaml_cfg=yaml_file)
    w.show()
    sys.exit(app.exec())
