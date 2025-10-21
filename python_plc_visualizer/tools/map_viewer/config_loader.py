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
