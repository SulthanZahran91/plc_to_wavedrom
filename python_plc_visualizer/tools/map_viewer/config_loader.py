# map_viewer/config_loader.py
from __future__ import annotations
from typing import Tuple, List, Dict
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
            text=r.get("text"),
            text_color=r.get("text_color"),
            bg_color=r.get("bg_color"),
            target=r.get("target", "block"),
        )
        for r in rules_cfg
        if r.get("signal")
    ]
    dmap = DeviceUnitMap(cfg.get("device_to_unit", []))
    policy = ColorPolicy(rules, default=cfg.get("default_color", "#D3D3D3"))
    return dmap, policy

def load_xml_parsing_config(yaml_path: str) -> dict:
    """Load XML parsing configuration from YAML file.
    
    Returns a dictionary with the following keys:
    - attributes_to_extract: List[str]
    - child_elements_to_extract: List[str]
    - render_as_text_types: List[str]
    - render_as_arrow_types: List[str]
    - render_as_arrowed_rectangle_types: List[str]
    - type_color_mapping: Dict[str, str]
    - type_zindex_mapping: Dict[str, int]
    - forecolor_mapping: Dict[str, str]
    """
    try:
        with open(yaml_path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
        xml_cfg = cfg.get("xml_parsing", {})
        
        return {
            "attributes_to_extract": xml_cfg.get("attributes_to_extract", ["type"]),
            "child_elements_to_extract": xml_cfg.get("child_elements_to_extract", []),
            "render_as_text_types": xml_cfg.get("render_as_text_types", []),
            "render_as_arrow_types": xml_cfg.get("render_as_arrow_types", []),
            "render_as_arrowed_rectangle_types": xml_cfg.get("render_as_arrowed_rectangle_types", []),
            "type_color_mapping": xml_cfg.get("type_color_mapping", {"default": "#D3D3D3"}),
            "type_zindex_mapping": xml_cfg.get("type_zindex_mapping", {"default": 0}),
            "forecolor_mapping": xml_cfg.get("forecolor_mapping", {"default": "#000000"}),
        }
    except Exception as e:
        print(f"Warning: Failed to load XML parsing config from {yaml_path}: {e}")
        # Return empty config, will use fallback defaults
        return {
            "attributes_to_extract": [],
            "child_elements_to_extract": [],
            "render_as_text_types": [],
            "render_as_arrow_types": [],
            "render_as_arrowed_rectangle_types": [],
            "type_color_mapping": {},
            "type_zindex_mapping": {},
            "forecolor_mapping": {},
        }
