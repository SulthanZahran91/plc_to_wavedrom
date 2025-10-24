"""Base class for pattern validators."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from plc_visualizer.utils import SignalData
from plc_visualizer.validation.violation import ValidationViolation


class PatternValidator(ABC):
    """Base class for all pattern validators."""

    @abstractmethod
    def validate(
        self,
        device_id: str,
        signal_data_map: dict[str, SignalData],
        rule_config: dict[str, Any]
    ) -> list[ValidationViolation]:
        """Validate signals against a pattern.

        Args:
            device_id: Device being validated.
            signal_data_map: All signals for this device {signal_name: SignalData}.
            rule_config: Pattern configuration from YAML.

        Returns:
            List of violations found.
        """
        pass
