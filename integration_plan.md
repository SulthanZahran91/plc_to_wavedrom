Here’s a concrete, low-friction way to integrate—clean separation, runtime color from signals (not from `TYPE_COLOR_MAPPING`), and easy to slot into `plc_to_wavedrom` when you’re ready.

# Approach (summary)

1. **Keep renderer “dumb.”** It just draws shapes and exposes `update_rect_color_by_unit(unit_id, QColor)`.
2. **Add a mapping layer** from your device IDs (from `plc_to_wavedrom`) → `UnitId` in the map: `DeviceUnitMap`.
3. **Add a color policy** that turns `(unit_id, signal_name, value)` into a **color** (e.g., Signal A high → yellow/green).
4. **Add a state model** that listens to *device signals*, applies mapping + policy, and emits `stateChanged(unit_id, QColor)` — which you connect to the renderer.

This keeps signal logic out of the renderer and makes it trivial to change rules without touching UI code.

---

## Drop these files into `plc_map_viewer/map_viewer/`

### `device_mapping.py`

```python
# map_viewer/device_mapping.py
from typing import Optional, List, Dict
import fnmatch

class DeviceUnitMap:
    """
    Maps device_id strings (from your runtime signals) to UnitId strings used in the map XML.
    Rules are simple fnmatch wildcards, e.g., "B1ACNV*-104@*" -> "B1ACNV13301-104"
    """
    def __init__(self, rules: List[Dict]):
        # rules: [{pattern: "B1ACNV*-104@*", unit_id: "B1ACNV13301-104"}]
        self.rules = rules or []

    def map(self, device_id: str) -> Optional[str]:
        for r in self.rules:
            pat = r.get("pattern")
            uid = r.get("unit_id")
            if pat and uid and fnmatch.fnmatch(device_id, pat):
                return uid
        return None
```

### `color_policy.py`

```python
# map_viewer/color_policy.py
from __future__ import annotations
from typing import Any, List, Optional
from PySide6.QtGui import QColor
import operator

_OPS = {
    "==": operator.eq, "!=": operator.ne,
    ">": operator.gt, "<": operator.lt,
    ">=": operator.ge, "<=": operator.le,
}

class ColorRule:
    """
    A rule that sets a color if (unit_id optional AND signal_name matches AND op(value, rule.value) is True).
    Higher priority wins (first match wins after sorting).
    """
    def __init__(self, signal: str, op: str, value: Any, color: str,
                 unit_id: Optional[str] = None, priority: int = 0):
        self.signal = signal
        self.op = op or "=="
        self.value = value
        self.color = QColor(color)
        self.unit_id = unit_id
        self.priority = priority

    def matches(self, unit_id: str, signal_name: str, value: Any) -> bool:
        if self.unit_id and self.unit_id != unit_id:
            return False
        if self.signal != signal_name:
            return False
        fn = _OPS.get(self.op, _OPS["=="])
        # best-effort numeric compare, else str compare
        def _num(x):
            try: return float(x)
            except: return None
        v_num, r_num = _num(value), _num(self.value)
        if v_num is not None and r_num is not None:
            return fn(v_num, r_num)
        return fn(str(value), str(self.value))

class ColorPolicy:
    def __init__(self, rules: List[ColorRule], default: str = "#D3D3D3"):
        self.rules = sorted(rules or [], key=lambda r: r.priority, reverse=True)
        self.default = QColor(default)

    def color_for(self, unit_id: str, signal_name: str, value: Any,
                  previous_color: Optional[QColor]) -> QColor:
        for r in self.rules:
            if r.matches(unit_id, signal_name, value):
                return r.color
        # no rule hit: keep prior color if any, else default
        return previous_color or self.default
```

### `state_model.py`

```python
# map_viewer/state_model.py
from __future__ import annotations
from typing import Any, NamedTuple, Optional, Iterable
from PySide6.QtCore import QObject, Signal, Slot
from PySide6.QtGui import QColor

from .device_mapping import DeviceUnitMap
from .color_policy import ColorPolicy

class SignalEvent(NamedTuple):
    device_id: str
    signal_name: str
    value: Any
    timestamp: float  # seconds since epoch or ms, your choice

class UnitStateModel(QObject):
    """
    Central state: turns device signal events into renderer-friendly color updates.
    Emits: stateChanged(unit_id, QColor)
    """
    stateChanged = Signal(str, QColor)

    def __init__(self, device_map: DeviceUnitMap, color_policy: ColorPolicy, parent=None):
        super().__init__(parent)
        self._device_map = device_map
        self._policy = color_policy
        self._colors: dict[str, QColor] = {}

    @Slot(object)
    def on_signal(self, event: SignalEvent):
        unit_id = self._device_map.map(event.device_id) or event.device_id  # fallback: use device_id
        prev = self._colors.get(unit_id)
        color = self._policy.color_for(unit_id, event.signal_name, event.value, prev)
        if prev != color:
            self._colors[unit_id] = color
            self.stateChanged.emit(unit_id, color)

    def color_of(self, unit_id: str) -> Optional[QColor]:
        return self._colors.get(unit_id)
```

### `config_loader.py` (optional helper, YAML-based)

```python
# map_viewer/config_loader.py
from __future__ import annotations
from typing import Tuple, List
from PySide6.QtGui import QColor
import yaml

from .device_mapping import DeviceUnitMap
from .color_policy import ColorPolicy, ColorRule

def load_mapping_and_policy(yaml_path: str) -> tuple[DeviceUnitMap, ColorPolicy]:
    with open(yaml_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}
    rules_cfg: List[dict] = cfg.get("rules", [])
    rules = [
        ColorRule(
            signal=r.get("signal"),
            op=r.get("op", "=="),
            value=r.get("value"),
            color=r.get("color", "#D3D3D3"),
            unit_id=r.get("unit_id"),
            priority=int(r.get("priority", 0)),
        )
        for r in rules_cfg
        if r.get("signal")
    ]
    dmap = DeviceUnitMap(cfg.get("device_to_unit", []))
    policy = ColorPolicy(rules, default=cfg.get("default_color", "#D3D3D3"))
    return dmap, policy
```

### Example YAML (`mappings_and_rules.yaml`)

```yaml
# map_viewer/mappings_and_rules.yaml
default_color: "#D3D3D3"

device_to_unit:
  - pattern: "B1ACNV13301-104@*"   # Device ID wildcard
    unit_id: "B1ACNV13301-104"     # UnitId in the map XML

rules:
  # Signal A == 1 -> Yellow
  - signal: "A"
    op: "=="
    value: 1
    color: "#FFFF00"
    priority: 10

  # Signal A == 2 -> Green
  - signal: "A"
    op: "=="
    value: 2
    color: "#00FF00"
    priority: 10

  # Example: any unit with Signal B > 80 -> Red (override)
  - signal: "B"
    op: ">"
    value: 80
    color: "#D50000"
    priority: 100
```

> You can start with a dict in code instead of YAML if you prefer; YAML just lets non-devs tweak rules.

---

## Wire it together (demo integration)

Add a small integration demo so you can test end-to-end before plugging into `plc_to_wavedrom`.

### `example_main_integration.py`

```python
# example_main_integration.py
import sys, time
from PySide6.QtWidgets import QApplication, QMainWindow, QDockWidget, QWidget
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor

from map_viewer import MapParser, MapRenderer, MediaControls
from map_viewer.state_model import UnitStateModel, SignalEvent
from map_viewer.config_loader import load_mapping_and_policy

class DemoWindow(QMainWindow):
    def __init__(self, xml_path: str = "test.xml", yaml_cfg: str = "map_viewer/mappings_and_rules.yaml"):
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
    app = QApplication(sys.argv)
    w = DemoWindow(xml_path="test.xml")
    w.show()
    sys.exit(app.exec())
```

---

## Renderer change you should make now

Since **color is no longer dependent on type**, use a **neutral base**. In your existing `config.py`, set all type entries to the same neutral gray, or just keep `"default"` and delete the specific ones:

```python
# config.py
TYPE_COLOR_MAPPING = {
    "default": QColor(211, 211, 211)  # neutral base; runtime state will recolor
}
```

(Your runtime updates will paint rectangles via `update_rect_color_by_unit`.)

---

## How to hook this into `plc_to_wavedrom` later

**Assumptions** (replace if different):

* You already have a stream of device events like `(device_id, signal_name, value, ts)` from your log parser / runtime.
* Your “device_id” strings can be mapped to UnitIds shown in the XML map (e.g., `B1ACNV13301-104@D19` → `B1ACNV13301-104`).

**Steps:**

1. **Instantiate once** (e.g., in your app boot):

   * `MapRenderer` in a tab/dock (not necessarily visible yet).
   * `DeviceUnitMap` + `ColorPolicy` (from YAML or dict).
   * `UnitStateModel(device_map, color_policy)`.
   * Connect: `state_model.stateChanged.connect(renderer.update_rect_color_by_unit)`.
2. **Send your signals** into the state model:

   * Wherever you currently emit or handle parsed PLC/HSMS/etc. signals, call:

     ```python
     state_model.on_signal(SignalEvent(device_id, signal_name, value, timestamp))
     ```
3. **Show the map view** when you’re ready in the UI. No changes needed to signal flow.
4. **Iterate your color rules** in YAML—no code changes. You can add rules for multiple signals, priorities (e.g., faults → red override), thresholds, etc.
5. **Performance:** if you push thousands of updates/sec:

   * Batch/coalesce per unit in the producer and emit only when the resulting color changes.
   * If signals arrive on worker threads, always cross to the UI thread via Qt signals (the `@Slot(object)` + signal connection already does this cleanly).

---

## Why this is robust

* **Decoupled**: renderer doesn’t know about signals or rules.
* **Testable**: you can unit test `DeviceUnitMap`, `ColorPolicy`, and `UnitStateModel` without Qt widgets.
* **Config-driven**: ops can tweak YAML mappings/rules without touching code.
* **Extensible**: add more rule types (regex by signal, per-unit overrides, timeouts to revert color if stale, etc.) in `ColorPolicy`.

If you want, I can add:

* A **staleness timeout** (e.g., revert to gray if no updates for `N` seconds).
* **Per-unit rule priority** and **multi-signal aggregation** (e.g., “if A high AND B low → amber”).
* A **pyproject.toml** so this becomes `pip install -e .` installable.
