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
    
    Supports target field:
    - target: "block" (default) or "arrow" - which part to color for arrowed rectangles
    """
    def __init__(self, signal: str, op: str, value: Any, color: str,
                 unit_id: Optional[str] = None, priority: int = 0,
                 text: Optional[str] = None, text_color: Optional[str] = None,
                 bg_color: Optional[str] = None, target: str = "block"):
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
        # Target support: "block" or "arrow"
        self.target = target if target in ["block", "arrow"] else "block"

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
                  previous_block_color: Optional[QColor],
                  previous_arrow_color: Optional[QColor] = None) -> tuple[Optional[QColor], Optional[QColor], Optional[tuple[str, QColor]]]:
        """
        Returns (block_color, arrow_color, text_overlay_info).
        - block_color: color for rectangle background (None means no change)
        - arrow_color: color for arrow overlay (None means no change)
        - text_overlay_info: (character, text_color) or None if no text overlay
        
        Rules with target="block" set block_color, target="arrow" set arrow_color.
        Multiple rules can match with different targets.
        """
        block_color = None
        arrow_color = None
        text_info = None
        
        for r in self.rules:
            if r.matches(unit_id, signal_name, value):
                if r.target == "block" and block_color is None:
                    block_color = r.bg_color
                    # Text overlay only applies with block color
                    if r.text and r.text_color and text_info is None:
                        text_info = (r.text, r.text_color)
                elif r.target == "arrow" and arrow_color is None:
                    arrow_color = r.bg_color
                
                # If both colors found and text overlay decided, we can stop
                if block_color is not None and arrow_color is not None and (text_info is not None or not any(rule.text for rule in self.rules)):
                    break
        
        # Apply defaults: keep previous colors if no rule matched
        final_block_color = block_color if block_color is not None else (previous_block_color or self.default)
        final_arrow_color = arrow_color if arrow_color is not None else previous_arrow_color
        
        return (final_block_color, final_arrow_color, text_info)
