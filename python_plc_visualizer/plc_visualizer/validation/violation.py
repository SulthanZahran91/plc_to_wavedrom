"""Validation violation data model."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Any


@dataclass
class ValidationViolation:
    """Represents a single validation rule violation.

    This is a log analysis result - it indicates when and where
    a signal pattern deviated from expected behavior.
    """

    device_id: str
    """Device that violated the rule."""

    signal_name: str
    """Signal involved in the violation."""

    timestamp: datetime
    """When the violation occurred."""

    severity: str
    """Severity level: 'error', 'warning', or 'info'."""

    rule_name: str
    """Name/ID of the rule that was violated."""

    message: str
    """Human-readable description of the violation."""

    expected: Optional[str] = None
    """What was expected (optional)."""

    actual: Optional[str] = None
    """What actually happened (optional)."""

    context: dict[str, Any] = field(default_factory=dict)
    """Additional context information."""

    def __str__(self) -> str:
        """Human-readable string representation."""
        parts = [
            f"[{self.severity.upper()}]",
            f"{self.timestamp.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}",
            f"{self.device_id}",
            f"{self.signal_name}:",
            self.message
        ]

        if self.expected and self.actual:
            parts.append(f"(expected: {self.expected}, actual: {self.actual})")

        return " ".join(parts)
