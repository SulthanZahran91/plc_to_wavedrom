"""Sequential pattern validator."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from plc_visualizer.utils import SignalData
from plc_visualizer.validation.violation import ValidationViolation
from .base import PatternValidator


class SequenceStatus(Enum):
    """Status of a sequence being tracked."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    VIOLATED = "violated"
    TIMEOUT = "timeout"


@dataclass
class SequenceStep:
    """Single step in a sequence."""
    step_number: int
    signal: str
    operator: str  # ==, !=, >, <, >=, <=, in, not in
    value: Any
    description: str = ""
    timeout: Optional[float] = None  # Seconds from previous step


@dataclass
class SequenceInstance:
    """Tracks a specific instance of a sequence in progress."""
    sequence_id: str
    device_id: str
    status: SequenceStatus
    current_step_number: int
    completed_steps: set[tuple[int, str]] = field(default_factory=set)  # (step_num, signal)
    step_start_time: datetime = None
    sequence_start_time: datetime = None
    violations: list[ValidationViolation] = field(default_factory=list)


class SequenceValidator(PatternValidator):
    """Validates that signals follow a specific ordered sequence.

    Features:
    - Steps with the same step number can occur in any order
    - Timing constraints (max duration between steps)
    - Optional intermediate signal changes
    - Single-device validation (one sequence at a time per device)
    """

    def __init__(self):
        self.active_sequences: dict[str, SequenceInstance] = {}

    def validate(
        self,
        device_id: str,
        signal_data_map: dict[str, SignalData],
        rule_config: dict[str, Any]
    ) -> list[ValidationViolation]:
        """Validate a sequence pattern against device signals.

        Args:
            device_id: Device being validated.
            signal_data_map: All signals for this device {signal_name: SignalData}.
            rule_config: Pattern configuration from YAML.

        Returns:
            List of violations found.
        """
        violations = []

        # Parse sequence definition
        sequence_steps = self._parse_sequence(rule_config.get("sequence", []))
        if not sequence_steps:
            return violations

        sequence_id = rule_config.get("id", "unknown")

        # Get all signal changes chronologically
        all_changes = self._get_chronological_changes(signal_data_map)

        # Track sequence through time
        for timestamp, signal_name, signal_value in all_changes:
            result = self._process_signal_change(
                device_id=device_id,
                sequence_id=sequence_id,
                sequence_steps=sequence_steps,
                signal_name=signal_name,
                signal_value=signal_value,
                timestamp=timestamp,
                rule_config=rule_config
            )
            violations.extend(result)

        # Check for incomplete sequences
        violations.extend(self._check_incomplete_sequences(rule_config))

        return violations

    def _parse_sequence(self, sequence_config: list[dict]) -> list[SequenceStep]:
        """Parse sequence configuration into SequenceStep objects."""
        steps = []
        for step_config in sequence_config:
            steps.append(SequenceStep(
                step_number=step_config.get("step", 0),
                signal=step_config.get("signal", ""),
                operator=step_config.get("operator", "=="),
                value=step_config.get("value"),
                description=step_config.get("description", ""),
                timeout=step_config.get("timeout")
            ))
        return sorted(steps, key=lambda s: (s.step_number, s.signal))

    def _get_chronological_changes(
        self,
        signal_data_map: dict[str, SignalData]
    ) -> list[tuple[datetime, str, Any]]:
        """Get all signal changes in chronological order.

        Returns:
            List of (timestamp, signal_name, value) tuples sorted by time.
        """
        all_changes = []

        for signal_name, signal_data in signal_data_map.items():
            for state in signal_data.states:
                all_changes.append((
                    state.start_time,
                    signal_name,
                    state.value
                ))

        return sorted(all_changes, key=lambda x: x[0])

    def _process_signal_change(
        self,
        device_id: str,
        sequence_id: str,
        sequence_steps: list[SequenceStep],
        signal_name: str,
        signal_value: Any,
        timestamp: datetime,
        rule_config: dict[str, Any]
    ) -> list[ValidationViolation]:
        """Process a single signal change and update sequence tracking."""
        violations = []
        instance_key = f"{device_id}:{sequence_id}"

        # Get steps grouped by step number
        steps_by_number = self._group_steps_by_number(sequence_steps)
        step_numbers = sorted(steps_by_number.keys())

        # Check if sequence exists
        if instance_key not in self.active_sequences:
            # Check if this change starts the sequence (matches any step 1)
            first_steps = steps_by_number.get(step_numbers[0], [])
            if self._matches_any_step(signal_name, signal_value, first_steps):
                # Start new sequence
                self.active_sequences[instance_key] = SequenceInstance(
                    sequence_id=sequence_id,
                    device_id=device_id,
                    status=SequenceStatus.IN_PROGRESS,
                    current_step_number=step_numbers[0],
                    completed_steps={(step_numbers[0], signal_name)},
                    step_start_time=timestamp,
                    sequence_start_time=timestamp
                )

                # Check if we should advance immediately (if all steps in step 1 are done)
                instance = self.active_sequences[instance_key]
                if self._all_steps_complete(first_steps, instance.completed_steps, step_numbers[0]):
                    if len(step_numbers) > 1:
                        instance.current_step_number = step_numbers[1]
                        instance.step_start_time = timestamp
                    else:
                        # Only one step in sequence, already complete
                        instance.status = SequenceStatus.COMPLETED

                return []
            else:
                # Not starting the sequence, ignore
                return []

        instance = self.active_sequences[instance_key]

        # Skip if sequence already completed or violated
        if instance.status in (SequenceStatus.COMPLETED, SequenceStatus.VIOLATED):
            # Check if starting a new sequence
            first_steps = steps_by_number.get(step_numbers[0], [])
            if self._matches_any_step(signal_name, signal_value, first_steps):
                # Reset and start fresh
                self.active_sequences[instance_key] = SequenceInstance(
                    sequence_id=sequence_id,
                    device_id=device_id,
                    status=SequenceStatus.IN_PROGRESS,
                    current_step_number=step_numbers[0],
                    completed_steps={(step_numbers[0], signal_name)},
                    step_start_time=timestamp,
                    sequence_start_time=timestamp
                )

                # Check if we should advance immediately
                instance = self.active_sequences[instance_key]
                if self._all_steps_complete(first_steps, instance.completed_steps, step_numbers[0]):
                    if len(step_numbers) > 1:
                        instance.current_step_number = step_numbers[1]
                        instance.step_start_time = timestamp
                    else:
                        instance.status = SequenceStatus.COMPLETED

            return []

        # Get current step group
        current_steps = steps_by_number[instance.current_step_number]

        # Check for timeout
        max_timeout = max((s.timeout for s in current_steps if s.timeout is not None), default=None)
        if max_timeout is not None:
            elapsed = (timestamp - instance.step_start_time).total_seconds()
            if elapsed > max_timeout:
                # Timeout violation
                pending_steps = [s for s in current_steps
                                if (instance.current_step_number, s.signal) not in instance.completed_steps]

                violation = ValidationViolation(
                    device_id=device_id,
                    signal_name=pending_steps[0].signal if pending_steps else "unknown",
                    timestamp=timestamp,
                    severity=rule_config.get("severity", "error"),
                    rule_name=f"{sequence_id}: Step {instance.current_step_number}",
                    message=f"Sequence timeout: Expected step {instance.current_step_number} to complete within {max_timeout}s, but {elapsed:.1f}s elapsed",
                    expected=", ".join(f"{s.signal}={s.value}" for s in pending_steps),
                    actual=f"No change for {elapsed:.1f}s",
                    context={
                        "sequence_id": sequence_id,
                        "step": instance.current_step_number,
                        "elapsed": elapsed
                    }
                )
                violations.append(violation)
                instance.status = SequenceStatus.TIMEOUT

                # Reset if configured
                if rule_config.get("options", {}).get("reset_on_timeout", True):
                    del self.active_sequences[instance_key]

                return violations

        # Check if this change matches any step in current step group
        matching_step = self._find_matching_step(signal_name, signal_value, current_steps)

        if matching_step:
            # Check if already completed this exact step
            step_key = (instance.current_step_number, signal_name)
            if step_key in instance.completed_steps:
                # Duplicate - ignore (signal changed again to same value)
                return []

            # Mark as completed
            instance.completed_steps.add(step_key)

            # Check if all steps in current step number are now complete
            if self._all_steps_complete(current_steps, instance.completed_steps, instance.current_step_number):
                # Advance to next step number
                current_idx = step_numbers.index(instance.current_step_number)
                if current_idx + 1 < len(step_numbers):
                    instance.current_step_number = step_numbers[current_idx + 1]
                    instance.step_start_time = timestamp
                else:
                    # Sequence complete!
                    instance.status = SequenceStatus.COMPLETED

                    # Optionally log success
                    if rule_config.get("on_complete", {}).get("log_success", False):
                        duration = (timestamp - instance.sequence_start_time).total_seconds()
                        violations.append(ValidationViolation(
                            device_id=device_id,
                            signal_name="SEQUENCE_COMPLETE",
                            timestamp=timestamp,
                            severity="info",
                            rule_name=sequence_id,
                            message=rule_config.get("on_complete", {}).get("message",
                                                                          f"Sequence completed in {duration:.1f}s"),
                            context={"sequence_id": sequence_id, "duration": duration}
                        ))

        else:
            # Signal change doesn't match current step
            allow_intermediate = rule_config.get("options", {}).get("allow_intermediate_changes", False)

            if not allow_intermediate:
                # Check if it matches ANY future step (out of order)
                future_match = False
                for future_step_num in step_numbers:
                    if future_step_num > instance.current_step_number:
                        if self._matches_any_step(signal_name, signal_value, steps_by_number[future_step_num]):
                            future_match = True
                            break

                if future_match:
                    # Out of order violation
                    violation = ValidationViolation(
                        device_id=device_id,
                        signal_name=signal_name,
                        timestamp=timestamp,
                        severity=rule_config.get("severity", "error"),
                        rule_name=f"{sequence_id}: Step {instance.current_step_number}",
                        message=rule_config.get("on_violation", {}).get("message",
                                                                       "Sequence violated: step out of order"),
                        expected=self._format_expected_steps(current_steps, instance.completed_steps, instance.current_step_number),
                        actual=f"{signal_name} = {signal_value}",
                        context={
                            "sequence_id": sequence_id,
                            "expected_step": instance.current_step_number,
                        }
                    )
                    violations.append(violation)
                    instance.status = SequenceStatus.VIOLATED

                    # Reset if configured
                    if rule_config.get("on_violation", {}).get("reset_on_error", True):
                        del self.active_sequences[instance_key]
                # else: unrelated signal change, ignore

        return violations

    def _group_steps_by_number(self, steps: list[SequenceStep]) -> dict[int, list[SequenceStep]]:
        """Group steps by their step number."""
        grouped = {}
        for step in steps:
            if step.step_number not in grouped:
                grouped[step.step_number] = []
            grouped[step.step_number].append(step)
        return grouped

    def _matches_any_step(self, signal_name: str, signal_value: Any, steps: list[SequenceStep]) -> bool:
        """Check if signal change matches any of the given steps."""
        return any(self._matches_step(signal_name, signal_value, step) for step in steps)

    def _find_matching_step(
        self,
        signal_name: str,
        signal_value: Any,
        steps: list[SequenceStep]
    ) -> Optional[SequenceStep]:
        """Find the step that matches this signal change."""
        for step in steps:
            if self._matches_step(signal_name, signal_value, step):
                return step
        return None

    def _matches_step(self, signal_name: str, signal_value: Any, step: SequenceStep) -> bool:
        """Check if a signal change matches a sequence step."""
        if signal_name != step.signal:
            return False

        return self._compare(signal_value, step.operator, step.value)

    def _compare(self, actual: Any, operator: str, expected: Any) -> bool:
        """Compare values based on operator."""
        try:
            if operator == "==":
                return actual == expected
            elif operator == "!=":
                return actual != expected
            elif operator == ">":
                return actual > expected
            elif operator == "<":
                return actual < expected
            elif operator == ">=":
                return actual >= expected
            elif operator == "<=":
                return actual <= expected
            elif operator == "in":
                return actual in expected
            elif operator == "not in":
                return actual not in expected
            else:
                return False
        except (TypeError, ValueError):
            return False

    def _all_steps_complete(
        self,
        steps: list[SequenceStep],
        completed: set[tuple[int, str]],
        step_number: int
    ) -> bool:
        """Check if all steps in a step group are completed."""
        for step in steps:
            if (step_number, step.signal) not in completed:
                return False
        return True

    def _format_expected_steps(
        self,
        steps: list[SequenceStep],
        completed: set[tuple[int, str]],
        step_number: int
    ) -> str:
        """Format expected steps for violation message."""
        pending = [s for s in steps if (step_number, s.signal) not in completed]
        if not pending:
            return "All steps complete"
        return ", ".join(f"{s.signal} {s.operator} {s.value}" for s in pending)

    def _check_incomplete_sequences(self, rule_config: dict[str, Any]) -> list[ValidationViolation]:
        """Check for sequences that started but never completed."""
        violations = []

        for instance_key, instance in list(self.active_sequences.items()):
            if instance.status == SequenceStatus.IN_PROGRESS:
                partial_severity = rule_config.get("options", {}).get("partial_match_severity", "warning")

                violations.append(ValidationViolation(
                    device_id=instance.device_id,
                    signal_name="SEQUENCE_INCOMPLETE",
                    timestamp=instance.step_start_time,
                    severity=partial_severity,
                    rule_name=instance.sequence_id,
                    message=f"Sequence started but never completed (reached step {instance.current_step_number})",
                    context={
                        "sequence_id": instance.sequence_id,
                        "current_step": instance.current_step_number,
                        "started_at": instance.sequence_start_time.isoformat()
                    }
                ))

        return violations
