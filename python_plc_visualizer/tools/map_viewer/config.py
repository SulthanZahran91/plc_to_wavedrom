# map_viewer/config.py
from pathlib import Path
from PySide6.QtGui import QColor
from PySide6.QtCore import Qt

from .config_loader import load_xml_parsing_config

# Load configuration from YAML file
_yaml_path = Path(__file__).parent / "mappings_and_rules.yaml"
_xml_config = load_xml_parsing_config(str(_yaml_path))

# Fallback defaults (used if YAML is missing or incomplete)
_DEFAULT_ATTRIBUTES_TO_EXTRACT = ["type"]
_DEFAULT_CHILD_ELEMENTS_TO_EXTRACT = [
    "Text", "Size", "Location", "UnitId", "LineThick", "FlowDirection",
    "DashStyle", "StartCap", "EndCap", "ForeColor"
]
_DEFAULT_RENDER_AS_TEXT_TYPES = [
    "System.Windows.Forms.Label, System.Windows.Forms, Version=4.0.0.0, Culture=neutral, PublicKeyToken=b77a5c561934e089"
]
_DEFAULT_RENDER_AS_ARROW_TYPES = [
    "SmartFactory.SmartCIM.GUI.Widgets.WidgetArrow, SmartFactory.SmartCIM.GUI, Version=1.0.0.0, Culture=neutral, PublicKeyToken=null"
]
_DEFAULT_TYPE_COLOR_MAPPING = {
    "default": QColor(211, 211, 211),
}
_DEFAULT_TYPE_ZINDEX_MAPPING = {
    "SmartFactory.SmartCIM.GUI.Widgets.WidgetConveyorPort, SmartFactory.SmartCIM.GUI, Version=1.0.0.0, Culture=neutral, PublicKeyToken=null": 4,
    "SmartFactory.SmartCIM.GUI.Widgets.WidgetBelt, SmartFactory.SmartCIM.GUI, Version=1.0.0.0, Culture=neutral, PublicKeyToken=null": 3,
    "SmartFactory.SmartCIM.GUI.Widgets.WidgetDiverter, SmartFactory.SmartCIM.GUI, Version=1.0.0.0, Culture=neutral, PublicKeyToken=null": 2,
    "default": 0,
}
_DEFAULT_FORECOLOR_MAPPING = {
    "HotTrack": QColor(0, 102, 204),
    "Black": QColor(Qt.GlobalColor.black),
    "Red": QColor(Qt.GlobalColor.red),
    "Green": QColor(Qt.GlobalColor.green),
    "Blue": QColor(Qt.GlobalColor.blue),
    "Yellow": QColor(Qt.GlobalColor.yellow),
    "White": QColor(Qt.GlobalColor.white),
    "default": QColor(Qt.GlobalColor.black),
}

# Helper function to convert hex color to QColor
def _hex_to_qcolor(hex_str: str) -> QColor:
    """Convert hex color string to QColor."""
    return QColor(hex_str) if hex_str.startswith("#") else QColor(hex_str)

# Export configuration with fallbacks
ATTRIBUTES_TO_EXTRACT = _xml_config.get("attributes_to_extract") or _DEFAULT_ATTRIBUTES_TO_EXTRACT
CHILD_ELEMENTS_TO_EXTRACT = _xml_config.get("child_elements_to_extract") or _DEFAULT_CHILD_ELEMENTS_TO_EXTRACT
RENDER_AS_TEXT_TYPES = _xml_config.get("render_as_text_types") or _DEFAULT_RENDER_AS_TEXT_TYPES
RENDER_AS_ARROW_TYPES = _xml_config.get("render_as_arrow_types") or _DEFAULT_RENDER_AS_ARROW_TYPES
RENDER_AS_ARROWED_RECTANGLE_TYPES = _xml_config.get("render_as_arrowed_rectangle_types", [])

# Convert color mappings from YAML (hex strings) to QColor
_yaml_type_colors = _xml_config.get("type_color_mapping", {})
TYPE_COLOR_MAPPING = {
    k: _hex_to_qcolor(v) for k, v in _yaml_type_colors.items()
} if _yaml_type_colors else _DEFAULT_TYPE_COLOR_MAPPING

_yaml_zindex = _xml_config.get("type_zindex_mapping", {})
TYPE_ZINDEX_MAPPING = _yaml_zindex if _yaml_zindex else _DEFAULT_TYPE_ZINDEX_MAPPING

_yaml_forecolors = _xml_config.get("forecolor_mapping", {})
FORECOLOR_MAPPING = {
    k: _hex_to_qcolor(v) for k, v in _yaml_forecolors.items()
} if _yaml_forecolors else _DEFAULT_FORECOLOR_MAPPING
