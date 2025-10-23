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

    Supports optional text overlay with:
    - text: single character to display (e.g., 'X' to cross out)
    - text_color: color for the text overlay
    - bg_color: background color (defaults to 'color' if not specified)
    """
    def __init__(self, signal: str, op: str, value: Any, color: str,
                 unit_id: Optional[str] = None, priority: int = 0,
                 text: Optional[str] = None, text_color: Optional[str] = None,
                 bg_color: Optional[str] = None):
        self.signal = signal
        self.op = op or "=="
        self.value = value
        # Backward compatibility: if bg_color not specified, use 'color'
        self.bg_color = QColor(bg_color if bg_color else color)
        self.color = self.bg_color  # Keep for backward compatibility
        self.unit_id = unit_id
        self.priority = priority
        # Text overlay support
        self.text = text[:1] if text else None  # Limit to single character
        self.text_color = QColor(text_color) if text_color and text else None

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
                  previous_color: Optional[QColor]) -> tuple[QColor, Optional[tuple[str, QColor]]]:
        """
        Returns (background_color, text_overlay_info).
        text_overlay_info is (character, text_color) or None if no text overlay.
        """
        for r in self.rules:
            if r.matches(unit_id, signal_name, value):
                bg_color = r.bg_color
                text_info = None
                if r.text and r.text_color:
                    text_info = (r.text, r.text_color)
                return (bg_color, text_info)
        # no rule hit: keep prior color if any, else default; no text overlay
        return (previous_color or self.default, None)
