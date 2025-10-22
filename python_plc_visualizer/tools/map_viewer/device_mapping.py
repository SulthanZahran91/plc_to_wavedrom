# map_viewer/device_mapping.py
from typing import Optional, List, Dict
import fnmatch

class DeviceUnitMap:
    """
    Maps device_id strings (from your runtime signals) to UnitId strings used in the map XML.
    Rules are simple fnmatch wildcards, e.g., "B1ACNV*-104@*" -> "B1ACNV13301-104"

    Special case: If unit_id is "*", extracts the UnitId from the device_id itself
    (the part before the @ symbol).
    """
    def __init__(self, rules: List[Dict]):
        # rules: [{pattern: "B1ACNV*-104@*", unit_id: "B1ACNV13301-104"}]
        # or [{pattern: "B1ACNV*@*", unit_id: "*"}] to extract from device_id
        self.rules = rules or []

    def map(self, device_id: str) -> Optional[str]:
        for r in self.rules:
            pat = r.get("pattern")
            uid = r.get("unit_id")
            if pat and uid and fnmatch.fnmatch(device_id, pat):
                # If unit_id is "*", extract from device_id (part before @)
                if uid == "*":
                    if "@" in device_id:
                        return device_id.split("@")[0]
                    return device_id
                return uid
        return None
