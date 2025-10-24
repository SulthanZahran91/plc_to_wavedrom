# Signal Validation Rules

This directory contains YAML configuration files for signal validation.

## Quick Start

1. Load a log file in the PLC Visualizer
2. Load validation rules: `log_window.load_validation_rules("config/signal_validation_rules.yaml")`
3. Run validation: `log_window.run_validation()`
4. View violations in console output

## Features

### Sequential Pattern Validation

Validates that signals follow a specific ordered sequence with timing constraints.

**Key Features:**
- **Ordered Steps**: Signals must occur in the defined sequence
- **Timing Constraints**: Each step can have a timeout (max duration from previous step)
- **Same-Step Unordered**: Multiple steps with the same step number can occur in any order
- **Flexible Intermediate Changes**: Optional `allow_intermediate_changes` setting
- **Multiple Operators**: Supports `==`, `!=`, `>`, `<`, `>=`, `<=`, `in`, `not in`

### Example Rule

```yaml
validation_rules:
  - device_pattern: "B1ACNV*"  # Applies to all conveyors
    name: "Carrier Movement Sequence"

    patterns:
      - id: "CARRIER_HANDSHAKE"
        pattern_type: "sequence"
        severity: "error"

        sequence:
          - step: 1
            signal: "CARRIER_DETECTED"
            operator: "=="
            value: true
            timeout: null  # No timeout (starts sequence)

          - step: 2
            signal: "CARRIER_ID_READ"
            operator: "=="
            value: "SET"
            timeout: 2.0  # Must happen within 2 seconds

          # ... more steps

        options:
          allow_intermediate_changes: false
          reset_on_timeout: true
```

### Same-Step Feature (Unordered Signals)

When multiple steps have the same step number, they can occur in **any order**:

```yaml
sequence:
  - step: 1
    signal: "INIT_START"
    value: true

  # These three can happen in ANY order
  - step: 2
    signal: "SENSOR_A_READY"
    value: true
    timeout: 5.0

  - step: 2
    signal: "SENSOR_B_READY"
    value: true
    timeout: 5.0

  - step: 2
    signal: "MOTOR_CALIBRATED"
    value: true
    timeout: 5.0

  # Step 3 only proceeds after ALL step 2 signals complete
  - step: 3
    signal: "INIT_COMPLETE"
    value: true
    timeout: 1.0
```

## Configuration Options

### Global Settings

```yaml
validation_settings:
  enabled: true
  auto_validate_on_load: false  # Manual validation trigger
  max_violations_per_device: 100
  max_violations_per_rule: 500
```

### Pattern Options

```yaml
options:
  allow_intermediate_changes: false  # Strict mode - only expected signals can change
  reset_on_timeout: true  # Reset tracking if timeout occurs
  partial_match_severity: "warning"  # Severity for incomplete sequences
```

### Operators

| Operator | Description | Example |
|----------|-------------|---------|
| `==` | Equal to | `value: true` |
| `!=` | Not equal to | `value: 0` |
| `>` | Greater than | `value: 0.0` |
| `<` | Less than | `value: 100` |
| `>=` | Greater than or equal | `value: 10` |
| `<=` | Less than or equal | `value: 50` |
| `in` | Value in list | `value: ["Idle", "Running"]` |
| `not in` | Value not in list | `value: ["Error", "Fault"]` |

### Severity Levels

- **error**: Critical violations (system malfunction)
- **warning**: Issues to review (may be acceptable)
- **info**: Informational (for awareness)

## Violation Output

Violations are reported with:
- **Timestamp**: When the violation occurred
- **Device ID**: Which device violated the rule
- **Signal**: Which signal was involved
- **Message**: Human-readable description
- **Expected vs Actual**: What was expected and what actually happened

Example output:
```
[ERROR] 2025-10-24 10:00:03.000 B1ACNV13302-104 CARRIER_ID_READ: Sequence timeout: Expected step 2 to complete within 2.0s, but 3.0s elapsed (expected: CARRIER_ID_READ=SET, actual: No change for 3.0s)
```

## Testing

Run the test suite to verify validation rules:

```bash
python test_validator.py
```

The test suite includes:
1. Perfect sequence (no violations)
2. Timeout violations
3. Out-of-order violations
4. Same-step feature (unordered signals)

## Customization

To create your own validation rules:

1. Copy `signal_validation_rules.yaml` to a new file
2. Modify `device_pattern` to match your devices
3. Define your `sequence` steps with appropriate timeouts
4. Set `options` based on your requirements
5. Test with your log data

## Integration

The validator is integrated into `LogTableWindow`:

```python
# Load rules
log_window.load_validation_rules("path/to/rules.yaml")

# Run validation
violations = log_window.run_validation()

# Access violations programmatically
for device_id, device_violations in violations.items():
    for violation in device_violations:
        print(violation)
```
