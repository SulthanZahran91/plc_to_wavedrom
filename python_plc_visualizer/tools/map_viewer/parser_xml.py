# map_viewer/parser_xml.py
import xml.etree.ElementTree as ET
from typing import Dict, Any, Iterable, Optional
from itertools import cycle

from PySide6.QtCore import QObject, Signal, QTimer
from PySide6.QtGui import QColor

from .config import ATTRIBUTES_TO_EXTRACT, CHILD_ELEMENTS_TO_EXTRACT

class MapParser(QObject):
    """
    XML parser that emits a Python dict consumable by the renderer.
    Also exposes a stub stateChanged(UnitId, QColor) signal for demo/testing.
    """
    objectsParsed = Signal(object)            # Dict[str, Dict[str, Any]]
    stateChanged  = Signal(str, QColor)       # unit_id, color

    def __init__(self, parent=None):
        super().__init__(parent)
        self._demo_timer: Optional[QTimer] = None
        self._demo_units: list[str] = []

    def parse_file(self, xml_path: str) -> Dict[str, Dict[str, Any]]:
        root = ET.parse(xml_path).getroot()
        res: Dict[str, Dict[str, Any]] = {}
        for obj in root.findall('.//Object[@name]'):
            name = obj.get("name")
            if not name:
                continue
            entry: Dict[str, Any] = {}
            for attr in ATTRIBUTES_TO_EXTRACT:
                entry[attr] = obj.get(attr)
            for child in CHILD_ELEMENTS_TO_EXTRACT:
                entry[child] = obj.findtext(child)
            res[name] = entry

        self.objectsParsed.emit(res)
        return res

    # ---------------- Demo / stub live updates ----------------
    def start_demo_state_changes(
        self,
        unit_ids: Iterable[str],
        colors: Iterable[QColor] | None = None,
        period_ms: int = 800
    ) -> None:
        """
        Periodically emits stateChanged(UnitId, QColor) cycling through given colors.
        Use ONLY for demo/testing. Call stop_demo_state_changes() to stop.
        """
        self.stop_demo_state_changes()
        self._demo_units = list(unit_ids)
        if not self._demo_units:
            return

        palette = list(colors) if colors else [
            QColor("#00C853"),  # green
            QColor("#FFD600"),  # amber
            QColor("#D50000"),  # red
            QColor("#1E88E5"),  # blue
        ]
        color_cycle = cycle(palette)
        unit_cycle  = cycle(self._demo_units)

        self._demo_timer = QTimer(self)
        self._demo_timer.timeout.connect(lambda: self._emit_next_demo(color_cycle, unit_cycle))
        self._demo_timer.start(period_ms)

    def _emit_next_demo(self, color_cycle, unit_cycle):
        unit = next(unit_cycle)
        color = next(color_cycle)
        self.stateChanged.emit(unit, color)

    def stop_demo_state_changes(self) -> None:
        if self._demo_timer:
            self._demo_timer.stop()
            self._demo_timer.deleteLater()
            self._demo_timer = None
