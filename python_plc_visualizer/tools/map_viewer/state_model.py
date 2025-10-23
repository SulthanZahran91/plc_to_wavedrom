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
    Central state: turns device signal events into renderer-friendly color and text overlay updates.
    Emits: stateChanged(unit_id, QColor, text_overlay_info)
    where text_overlay_info is (character, text_color) or None
    """
    stateChanged = Signal(str, QColor, object)  # (unit_id, bg_color, text_info)

    def __init__(self, device_map: DeviceUnitMap, color_policy: ColorPolicy, parent=None):
        super().__init__(parent)
        self._device_map = device_map
        self._policy = color_policy
        self._colors: dict[str, QColor] = {}
        self._text_overlays: dict[str, Optional[tuple[str, QColor]]] = {}

    @Slot(object)
    def on_signal(self, event: SignalEvent):
        unit_id = self._device_map.map(event.device_id) or event.device_id  # fallback: use device_id
        prev_color = self._colors.get(unit_id)
        prev_text = self._text_overlays.get(unit_id)

        color, text_info = self._policy.color_for(unit_id, event.signal_name, event.value, prev_color)

        # Emit if either color or text overlay changed
        if prev_color != color or prev_text != text_info:
            self._colors[unit_id] = color
            self._text_overlays[unit_id] = text_info
            self.stateChanged.emit(unit_id, color, text_info)

    def color_of(self, unit_id: str) -> Optional[QColor]:
        return self._colors.get(unit_id)

    def text_overlay_of(self, unit_id: str) -> Optional[tuple[str, QColor]]:
        return self._text_overlays.get(unit_id)
