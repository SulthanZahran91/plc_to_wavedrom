"""Main validation orchestrator."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from plc_visualizer.models import ParsedLog
from plc_visualizer.utils import SignalData
from .rule_loader import RuleLoader
from .violation import ValidationViolation
from .pattern_validators import SequenceValidator


class SignalValidator:
    """Main validator that orchestrates all validation rules."""

    def __init__(self, rules_path: str | Path):
        """Initialize validator with rules from a YAML file.

        Args:
            rules_path: Path to YAML rules file.

        Raises:
            FileNotFoundError: If rules file doesn't exist.
            ValueError: If rules file is invalid.
        """
        self.rules = RuleLoader.load(rules_path)
        self.settings = RuleLoader.get_settings(self.rules)
        self.rules_path = Path(rules_path)

        # Initialize pattern validators
        self.pattern_validators = {
            "sequence": SequenceValidator(),
        }

    def validate_device(
        self,
        device_id: str,
        signal_data_list: list[SignalData]
    ) -> list[ValidationViolation]:
        """Validate all signals for a specific device.

        Args:
            device_id: Device to validate.
            signal_data_list: List of signal data for this device.

        Returns:
            List of violations found (may be empty).
        """
        violations = []

        if not self.settings.get("enabled", True):
            return violations

        # Get rules that apply to this device
        device_rules = RuleLoader.get_rules_for_device(self.rules, device_id)
        if not device_rules:
            return violations

        # Build signal map
        signal_data_map = {sd.name: sd for sd in signal_data_list}

        # Apply each rule
        for rule in device_rules:
            rule_violations = self._validate_rule(
                device_id,
                signal_data_map,
                rule
            )

            # Enforce per-rule violation limit
            max_per_rule = self.settings.get("max_violations_per_rule", 500)
            violations.extend(rule_violations[:max_per_rule])

        # Enforce per-device violation limit
        max_per_device = self.settings.get("max_violations_per_device", 100)
        return violations[:max_per_device]

    def validate_all(
        self,
        parsed_log: ParsedLog,
        signal_data_list: list[SignalData]
    ) -> dict[str, list[ValidationViolation]]:
        """Validate all devices in a log.

        Args:
            parsed_log: The parsed log data.
            signal_data_list: List of all signal data.

        Returns:
            Dictionary mapping device_id to list of violations.
        """
        violations_by_device = {}

        # Group signal data by device
        signals_by_device: dict[str, list[SignalData]] = {}
        for signal_data in signal_data_list:
            device_id = signal_data.device_id
            if device_id not in signals_by_device:
                signals_by_device[device_id] = []
            signals_by_device[device_id].append(signal_data)

        # Validate each device
        for device_id, device_signals in signals_by_device.items():
            device_violations = self.validate_device(device_id, device_signals)
            if device_violations:
                violations_by_device[device_id] = device_violations

        return violations_by_device

    def _validate_rule(
        self,
        device_id: str,
        signal_data_map: dict[str, SignalData],
        rule: dict[str, Any]
    ) -> list[ValidationViolation]:
        """Validate a single rule against device signals."""
        violations = []

        # Check required signals exist
        required_signals = rule.get("required_signals", [])
        for signal_name in required_signals:
            if signal_name not in signal_data_map:
                # Missing required signal - report as violation
                violations.append(ValidationViolation(
                    device_id=device_id,
                    signal_name=signal_name,
                    timestamp=None,
                    severity="error",
                    rule_name=rule.get("name", "unknown"),
                    message=f"Required signal '{signal_name}' not found in log data",
                    context={"rule": rule.get("name")}
                ))

        # Run pattern validators
        for pattern in rule.get("patterns", []):
            pattern_type = pattern.get("pattern_type")
            validator = self.pattern_validators.get(pattern_type)

            if validator is None:
                # Unknown pattern type - skip with warning
                violations.append(ValidationViolation(
                    device_id=device_id,
                    signal_name="VALIDATOR",
                    timestamp=None,
                    severity="warning",
                    rule_name=rule.get("name", "unknown"),
                    message=f"Unknown pattern type: {pattern_type}",
                    context={"pattern_type": pattern_type}
                ))
                continue

            # Run the validator
            pattern_violations = validator.validate(
                device_id=device_id,
                signal_data_map=signal_data_map,
                rule_config=pattern
            )
            violations.extend(pattern_violations)

        return violations
