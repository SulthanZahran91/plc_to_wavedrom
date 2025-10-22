# map_viewer/config.py
from PySide6.QtGui import QColor
from PySide6.QtCore import Qt

# Attributes/child elements to extract from XML
ATTRIBUTES_TO_EXTRACT = ["type"]
CHILD_ELEMENTS_TO_EXTRACT = [
    "Text", "Size", "Location", "UnitId", "LineThick", "FlowDirection",
    "DashStyle", "StartCap", "EndCap", "ForeColor"
]

# Types rendered specially
RENDER_AS_TEXT_TYPES = [
    "System.Windows.Forms.Label, System.Windows.Forms, Version=4.0.0.0, Culture=neutral, PublicKeyToken=b77a5c561934e089"
]
RENDER_AS_ARROW_TYPES = [
    "SmartFactory.SmartCIM.GUI.Widgets.WidgetArrow, SmartFactory.SmartCIM.GUI, Version=1.0.0.0, Culture=neutral, PublicKeyToken=null"
]

# Coloring & z-order
# Modified per integration_plan: use neutral base color; runtime state will recolor
TYPE_COLOR_MAPPING = {
    "default": QColor(211, 211, 211),  # neutral base; runtime state will recolor
}

TYPE_ZINDEX_MAPPING = {
    "SmartFactory.SmartCIM.GUI.Widgets.WidgetConveyorPort, SmartFactory.SmartCIM.GUI, Version=1.0.0.0, Culture=neutral, PublicKeyToken=null": 4,
    "SmartFactory.SmartCIM.GUI.Widgets.WidgetBelt, SmartFactory.SmartCIM.GUI, Version=1.0.0.0, Culture=neutral, PublicKeyToken=null": 3,
    "SmartFactory.SmartCIM.GUI.Widgets.WidgetDiverter, SmartFactory.SmartCIM.GUI, Version=1.0.0.0, Culture=neutral, PublicKeyToken=null": 2,
    "default": 0,
}

FORECOLOR_MAPPING = {
    "HotTrack": QColor(0, 102, 204),
    "Black": QColor(Qt.GlobalColor.black),
    "Red": QColor(Qt.GlobalColor.red),
    "Green": QColor(Qt.GlobalColor.green),
    "Blue": QColor(Qt.GlobalColor.blue),
    "Yellow": QColor(Qt.GlobalColor.yellow),
    "White": QColor(Qt.GlobalColor.white),
    "default": QColor(Qt.GlobalColor.black),
}
