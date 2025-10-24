# Signal Validator UI Usage Guide

## Overview

The Signal Validator is integrated into the LogTableWindow with a dedicated toolbar that provides easy access to validation features.

## UI Layout

```
┌─────────────────────────────────────────────────────────────────────┐
│ Log Table Window                                                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ Signal Validation:  [Load Rules...]  No rules loaded        │   │
│  │                                                [Run Validation] │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ Signal Filters                                                │   │
│  │ [Search] [Type filters] [Device filters]                     │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ Device ID │ Signal Name │ Timestamp │ Value │ Type          │   │
│  ├───────────┼─────────────┼───────────┼───────┼───────────────┤   │
│  │ ...       │ ...         │ ...       │ ...   │ ...           │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

## Step-by-Step Usage

### Step 1: Load Log Data

First, load your PLC log file through the main application. The LogTableWindow will display the parsed log entries.

### Step 2: Load Validation Rules

1. Click the **"Load Rules..."** button in the validation toolbar
2. A file dialog will appear
3. Navigate to your validation rules YAML file
   - Example: `config/signal_validation_rules.yaml`
   - Filter shows: "YAML Files (*.yaml *.yml)"
4. Click "Open"

**Success:**
- Status label changes from "No rules loaded" to "Loaded: [filename]"
- Status label turns green
- "Run Validation" button becomes enabled
- A success dialog appears with instructions

**Failure:**
- Error dialog shows the reason (file not found, invalid YAML, etc.)
- Status remains "No rules loaded"

### Step 3: Run Validation

1. Click the **"Run Validation"** button
2. The validator processes all devices and signals
3. Results appear in two places:

**A. Summary Dialog:**
```
┌────────────────────────────────────┐
│  Validation Complete               │
├────────────────────────────────────┤
│                                    │
│  Found 3 violations in 2 devices:  │
│                                    │
│    Errors: 2                       │
│    Warnings: 1                     │
│    Info: 0                         │
│                                    │
│  Check console output for details. │
│                                    │
│  [ OK ]                            │
└────────────────────────────────────┘
```

**B. Console Output:**
```
================================================================================
VALIDATION VIOLATIONS
================================================================================

Device: B1ACNV13302-104
--------------------------------------------------------------------------------
  [ERROR] 2025-10-24 10:00:03.000 B1ACNV13302-104 CARRIER_ID_READ:
  Sequence timeout: Expected step 2 to complete within 2.0s, but 3.0s elapsed
  (expected: CARRIER_ID_READ=SET, actual: No change for 3.0s)

Device: B1ACNV13303-104
--------------------------------------------------------------------------------
  [WARNING] 2025-10-24 10:00:05.000 B1ACNV13303-104 CONVEYOR_MOVE:
  Carrier handshake sequence violated (expected: CARRIER_GIVEN_MOVE == True,
  actual: CONVEYOR_MOVE = True)

================================================================================
```

**No Violations:**
```
┌────────────────────────────────────┐
│  Validation Complete               │
├────────────────────────────────────┤
│                                    │
│  No violations found!              │
│  All signals follow expected       │
│  patterns.                         │
│                                    │
│  [ OK ]                            │
└────────────────────────────────────┘
```

## Button States

### "Load Rules..." Button
- **Always enabled**
- Clicking opens a file dialog
- Can reload rules at any time

### "Run Validation" Button
- **Disabled** when no rules are loaded (gray)
- **Enabled** after rules are loaded (clickable)
- Can be clicked multiple times to re-run validation

## Status Indicator

The status label shows the current state:

| State | Display | Color | Description |
|-------|---------|-------|-------------|
| No rules | "No rules loaded" | Gray (italic) | Initial state, no rules file loaded |
| Rules loaded | "Loaded: filename.yaml" | Green | Rules successfully loaded and ready to use |

## Error Scenarios

### No Rules Loaded
If you click "Run Validation" without loading rules:
```
┌────────────────────────────────────┐
│  No Rules Loaded                   │
├────────────────────────────────────┤
│                                    │
│  Please load validation rules      │
│  first.                            │
│                                    │
│  [ OK ]                            │
└────────────────────────────────────┘
```

### No Data Loaded
If you try to validate without log data:
```
┌────────────────────────────────────┐
│  No Data                           │
├────────────────────────────────────┤
│                                    │
│  Please load log data first.       │
│                                    │
│  [ OK ]                            │
└────────────────────────────────────┘
```

### Invalid YAML
If the rules file has syntax errors:
```
┌────────────────────────────────────┐
│  Load Error                        │
├────────────────────────────────────┤
│                                    │
│  Failed to load validation rules:  │
│  YAML syntax error on line 42...   │
│                                    │
│  [ OK ]                            │
└────────────────────────────────────┘
```

## Tips

1. **Keep rules file handy**: Save your custom validation rules in a known location for easy reloading

2. **Iterative development**: You can:
   - Run validation
   - See violations
   - Edit your YAML rules
   - Click "Load Rules..." again (reload)
   - Run validation again

3. **Multiple validations**: You can run validation multiple times on the same data without reloading

4. **Console output**: Always check the console for detailed violation information including:
   - Exact timestamp of violation
   - Device and signal involved
   - What was expected vs. what happened
   - Rule context (sequence ID, step number, etc.)

## Workflow Example

```
1. Application starts
   ↓
2. User loads PLC log file
   ↓
3. LogTableWindow displays log entries
   ↓
4. User clicks "Load Rules..."
   ↓
5. User selects "my_validation_rules.yaml"
   ↓
6. Status shows "Loaded: my_validation_rules.yaml" (green)
   ↓
7. User clicks "Run Validation"
   ↓
8. Dialog shows "Found 5 violations..."
   ↓
9. User checks console for details
   ↓
10. User analyzes violations and takes action
```

## Programmatic Usage

If you're integrating this into code:

```python
from plc_visualizer.ui.log_table_window import LogTableWindow

# Create window
window = LogTableWindow()

# Load data
window.set_data(parsed_log, signal_data)

# Option A: Automatic (no file dialog)
window.load_validation_rules("path/to/rules.yaml")

# Option B: Interactive (shows file dialog)
window.load_validation_rules()  # User selects file

# Run validation
violations = window.run_validation()

# Access results
for device_id, device_violations in violations.items():
    for violation in device_violations:
        print(f"{violation.timestamp}: {violation.message}")
```

## Related Files

- **config/signal_validation_rules.yaml**: Example rules with documentation
- **config/README.md**: Detailed validation features and YAML schema
- **test_validation_ui.py**: Interactive test showing the UI in action
- **test_validator.py**: Automated tests for validation logic
