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
    Emits: stateChanged(unit_id, block_color, arrow_color, text_overlay_info)
    where:
    - block_color: QColor for rectangle background (or None)
    - arrow_color: QColor for arrow overlay (or None)
    - text_overlay_info: (character, text_color) or None
    
    Carrier Tracking Mode:
    When enable_carrier_tracking is True, intercepts CurrentLocation signals to display
    CarrierID on the map at their current location.
    """
    stateChanged = Signal(str, object, object, object)  # (unit_id, block_color, arrow_color, text_info)

    def __init__(self, device_map: DeviceUnitMap, color_policy: ColorPolicy, parent=None):
        super().__init__(parent)
        self._device_map = device_map
        self._policy = color_policy
        self._block_colors: dict[str, QColor] = {}
        self._arrow_colors: dict[str, Optional[QColor]] = {}
        self._text_overlays: dict[str, Optional[tuple[str, QColor]]] = {}
        
        # Carrier tracking
        self._enable_carrier_tracking = False
        self._carrier_locations: dict[str, str] = {}  # CarrierID -> UnitId

    @property
    def enable_carrier_tracking(self) -> bool:
        """Get carrier tracking mode state."""
        return self._enable_carrier_tracking
    
    @enable_carrier_tracking.setter
    def enable_carrier_tracking(self, enabled: bool):
        """Enable/disable carrier tracking mode."""
        if self._enable_carrier_tracking == enabled:
            return
        
        self._enable_carrier_tracking = enabled
        
        if not enabled:
            # Clear all carrier text overlays when disabling
            for unit_id in list(self._carrier_locations.values()):
                # Clear text overlay for this unit
                prev_text = self._text_overlays.get(unit_id)
                if prev_text is not None:
                    self._text_overlays[unit_id] = None
                    # Re-emit with current colors but no text
                    self.stateChanged.emit(
                        unit_id,
                        self._block_colors.get(unit_id),
                        self._arrow_colors.get(unit_id),
                        None
                    )
            self._carrier_locations.clear()
    
    def get_carrier_location(self, carrier_id: str) -> Optional[str]:
        """Get the current location (UnitId) of a carrier."""
        return self._carrier_locations.get(carrier_id)
    
    def get_carriers_at_unit(self, unit_id: str) -> list[str]:
        """Get all carriers currently at a given unit."""
        return [cid for cid, uid in self._carrier_locations.items() if uid == unit_id]

    @Slot(object)
    def on_signal(self, event: SignalEvent):
        # Handle carrier tracking if enabled
        if self._enable_carrier_tracking and event.signal_name == "CurrentLocation":
            self._handle_carrier_location_update(event)
            return
        
        unit_id = self._device_map.map(event.device_id) or event.device_id  # fallback: use device_id
        prev_block_color = self._block_colors.get(unit_id)
        prev_arrow_color = self._arrow_colors.get(unit_id)
        prev_text = self._text_overlays.get(unit_id)

        block_color, arrow_color, text_info = self._policy.color_for(
            unit_id, event.signal_name, event.value, prev_block_color, prev_arrow_color
        )

        # Emit if any of the colors or text overlay changed
        if prev_block_color != block_color or prev_arrow_color != arrow_color or prev_text != text_info:
            self._block_colors[unit_id] = block_color
            self._arrow_colors[unit_id] = arrow_color
            self._text_overlays[unit_id] = text_info
            self.stateChanged.emit(unit_id, block_color, arrow_color, text_info)
    
    def _handle_carrier_location_update(self, event: SignalEvent):
        """Handle CurrentLocation signal update for carrier tracking.
        
        Args:
            event: SignalEvent where device_id is CarrierID and value is UnitId
        """
        carrier_id = event.device_id
        new_unit_id = str(event.value) if event.value else None
        old_unit_id = self._carrier_locations.get(carrier_id)
        
        # Skip if location hasn't changed
        if old_unit_id == new_unit_id:
            return
        
        # Update carrier location in dictionary FIRST (before updating displays)
        # This ensures get_carriers_at_unit() returns correct counts
        if new_unit_id:
            self._carrier_locations[carrier_id] = new_unit_id
        elif carrier_id in self._carrier_locations:
            del self._carrier_locations[carrier_id]
        
        # Now update displays with correct carrier counts
        if old_unit_id:
            # Update the old unit's display (will show remaining carriers or clear)
            self._update_unit_display(old_unit_id)
        
        if new_unit_id:
            # Update the new unit's display
            self._update_unit_display(new_unit_id)
    
    def _get_carrier_count_color(self, count: int) -> Optional[QColor]:
        """Get the background color based on the number of carriers at a unit.
        
        Color gradient:
        - 0 carriers: None (use default/transparent)
        - 1 carrier:  Light green (#90EE90 - indicates normal occupancy)
        - 2 carriers: Yellow (#FFD700 - indicates moderate load)
        - 3 carriers: Orange (#FFA500 - indicates high load)
        - 4+ carriers: Red (#FF4444 - indicates congestion/concern)
        
        Args:
            count: Number of carriers at the unit
            
        Returns:
            QColor for the block background, or None for default
        """
        if count == 0:
            return None  # No color/use default
        elif count == 1:
            return QColor(144, 238, 144)  # Light green
        elif count == 2:
            return QColor(255, 215, 0)  # Yellow/Gold
        elif count == 3:
            return QColor(255, 165, 0)  # Orange
        else:
            # 4+ carriers - red (more intense for higher counts)
            intensity = min(count - 3, 5)  # Cap intensity boost
            red = min(255, 255)
            green = max(0, 68 - intensity * 10)  # Gets darker red
            blue = max(0, 68 - intensity * 10)
            return QColor(red, green, blue)
    
    def _update_unit_display(self, unit_id: str):
        """Update the text overlay and color for a unit based on carrier count.
        
        Args:
            unit_id: The unit to update display for
        """
        carriers_at_unit = self.get_carriers_at_unit(unit_id)
        carrier_count = len(carriers_at_unit)
        
        # Determine text overlay
        if carrier_count == 0:
            # No carriers, clear the overlay
            text_info = None
        elif carrier_count == 1:
            # Single carrier, show the carrier ID
            text_info = (carriers_at_unit[0], QColor(0, 0, 0))  # Black text
        elif carrier_count <= 3:
            # 2-3 carriers: show all IDs with line breaks
            carrier_text = "\n".join(carriers_at_unit)
            text_info = (carrier_text, QColor(0, 0, 0))  # Black text
        else:
            # 4+ carriers: show count to avoid overcrowding
            count_text = f"{carrier_count}x"
            text_info = (count_text, QColor(0, 0, 0))  # Black text
        
        # Determine block color based on carrier count
        block_color = self._get_carrier_count_color(carrier_count)
        
        # Update internal state and emit signal
        self._text_overlays[unit_id] = text_info
        # Always update block_color (including when None to clear color)
        self._block_colors[unit_id] = block_color
        
        self.stateChanged.emit(
            unit_id,
            block_color,  # Emit the carrier-count-based color
            self._arrow_colors.get(unit_id),
            text_info
        )
    def block_color_of(self, unit_id: str) -> Optional[QColor]:
        return self._block_colors.get(unit_id)
    
    def arrow_color_of(self, unit_id: str) -> Optional[QColor]:
        return self._arrow_colors.get(unit_id)

    def text_overlay_of(self, unit_id: str) -> Optional[tuple[str, QColor]]:
        return self._text_overlays.get(unit_id)
