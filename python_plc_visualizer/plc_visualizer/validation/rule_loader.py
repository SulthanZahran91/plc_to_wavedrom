"""YAML rule loader for validation rules."""

from __future__ import annotations

import fnmatch
from pathlib import Path
from typing import Any

import yaml


class RuleLoader:
    """Loads and parses validation rules from YAML files."""

    @staticmethod
    def load(rules_path: str | Path) -> dict[str, Any]:
        """Load validation rules from a YAML file.

        Args:
            rules_path: Path to the YAML rules file.

        Returns:
            Parsed rules dictionary.

        Raises:
            FileNotFoundError: If rules file doesn't exist.
            yaml.YAMLError: If YAML is malformed.
        """
        path = Path(rules_path)
        if not path.exists():
            raise FileNotFoundError(f"Rules file not found: {rules_path}")

        with open(path, "r", encoding="utf-8") as f:
            rules = yaml.safe_load(f)

        if rules is None:
            raise ValueError(f"Empty or invalid YAML file: {rules_path}")

        # Validate basic structure
        if "validation_rules" not in rules:
            raise ValueError("YAML must contain 'validation_rules' key")

        return rules

    @staticmethod
    def get_rules_for_device(
        rules: dict[str, Any],
        device_id: str
    ) -> list[dict[str, Any]]:
        """Get all rules that apply to a specific device.

        Args:
            rules: Parsed rules dictionary.
            device_id: Device ID to match.

        Returns:
            List of rule configurations that match the device.
        """
        matching_rules = []

        for rule in rules.get("validation_rules", []):
            if not rule.get("enabled", True):
                continue

            device_pattern = rule.get("device_pattern", "*")

            # Match device ID against pattern (supports wildcards)
            if fnmatch.fnmatch(device_id, device_pattern):
                matching_rules.append(rule)

        return matching_rules

    @staticmethod
    def get_settings(rules: dict[str, Any]) -> dict[str, Any]:
        """Get global validation settings.

        Args:
            rules: Parsed rules dictionary.

        Returns:
            Settings dictionary with defaults.
        """
        default_settings = {
            "enabled": True,
            "auto_validate_on_load": False,
            "max_violations_per_device": 100,
            "max_violations_per_rule": 500,
        }

        settings = rules.get("validation_settings", {})
        return {**default_settings, **settings}
