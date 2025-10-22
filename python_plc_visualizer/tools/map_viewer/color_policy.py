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
    """
    def __init__(self, signal: str, op: str, value: Any, color: str,
                 unit_id: Optional[str] = None, priority: int = 0):
        self.signal = signal
        self.op = op or "=="
        self.value = value
        self.color = QColor(color)
        self.unit_id = unit_id
        self.priority = priority

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
                  previous_color: Optional[QColor]) -> QColor:
        for r in self.rules:
            if r.matches(unit_id, signal_name, value):
                return r.color
        # no rule hit: keep prior color if any, else default
        return previous_color or self.default
