# MCS Parser Fix Summary

## Problem
The MCS parser was failing to parse the carrier log file `CARRIER_2025-12-09.log` with error:
```
[CARRIER_2025-12-09.log] Line 0: No suitable parser found
```

## Root Cause
The log file uses a **simplified format** that differs from the original MCS format:

**Original format (two parameters):**
```
2025-12-05 00:00:36.322 [UPDATE=CommandID, CarrierID] [CurrentLocation=B1ACNV13301-120]
```

**Simplified format (single parameter):**
```
2025-12-09 00:00:01.443 [UPDATE=CarrierID] [CarrierLoc=B1ACNV13301-108]
```

Two key differences:
1. **Action header format**: Simplified format has only `[ACTION=CarrierID]` instead of `[ACTION=CommandID, CarrierID]`
2. **Signal name**: Uses `CarrierLoc` instead of `CurrentLocation`

## Solution
Updated the MCS parser to support **both** formats:

### 1. Updated Regex Pattern
Modified `LINE_RE` to make the comma and second ID optional:
```python
# Before
r'\[(?P<action>ADD|UPDATE|REMOVE)=(?P<command_id>[^,\]]+),\s*(?P<carrier_id>[^\]]+)\]'

# After  
r'\[(?P<action>ADD|UPDATE|REMOVE)=(?P<first_id>[^,\]]+)(?:,\s*(?P<second_id>[^\]]+))?\]'
```

### 2. Added Logic to Handle Both Formats
```python
if second_id_match:
    # Original format: [ACTION=CommandID, CarrierID]
    command_id = first_id
    carrier_id = second_id_match.strip()
else:
    # Simplified format: [ACTION=CarrierID]
    command_id = ''
    carrier_id = first_id
```

### 3. Added Signal Name Mapping
Created `SIGNAL_NAME_MAP` to normalize alternative signal names:
```python
SIGNAL_NAME_MAP = {
    'CarrierLoc': 'CurrentLocation',
    'CarrierLocation': 'CurrentLocation',
}
```

This ensures carrier tracking works regardless of which signal name is used in the log file.

### 4. Conditionally Add CommandID
Only add `_CommandID` signal when it's present (not empty):
```python
if command_id:
    entries.append((..., "_CommandID", ..., command_id, ...))
```

### 5. Fixed Multiprocessing Issue
Disabled multiprocessing for MCS parser by overriding `parse()` method:
```python
def parse(self, file_path, num_workers=None, *, use_processes=False):
    # Always use single-threaded parsing for MCS format
    return self._parse_single(file_path)
```

**Why?** The MCS parser's custom `_parse_line_to_entries()` method returns multiple
entries per line, which is incompatible with the generic multiprocessing workers
that expect one entry per line. Single-threaded parsing is still very fast for
typical MCS log files.

## Testing
Added comprehensive test cases in `test_mcs_parser.py`:
- `test_parse_simplified_format()` - Verify simplified format parsing
- `test_signal_name_mapping()` - Verify CarrierLoc → CurrentLocation mapping
- `test_can_parse_simplified_format()` - Verify file detection works
- `test_simplified_no_command_id()` - Verify no _CommandID in simplified format

All tests pass successfully.

## Files Modified
- `/home/dev/plc_to_wavedrom/python_plc_visualizer/plc_visualizer/parsers/mcs_parser.py`
  - Updated module docstring to document both formats
  - Modified LINE_RE regex pattern
  - Added SIGNAL_NAME_MAP dictionary
  - Updated _parse_line_to_entries() logic
  - Applied signal name mapping in parsing loop
  
- `/home/dev/plc_to_wavedrom/python_plc_visualizer/tests/test_mcs_parser.py`
  - Added 4 new test cases for simplified format

## Verification
The parser now correctly:
1. ✓ Recognizes simplified format files (can_parse returns True)
2. ✓ Parses both original and simplified formats
3. ✓ Maps CarrierLoc to CurrentLocation automatically
4. ✓ Works with carrier tracking feature in Map Viewer
5. ✓ Maintains backward compatibility with original format

## Next Steps
You should now be able to:
1. Load `CARRIER_2025-12-09.log` in the PLC Log Visualizer
2. Use the Map Viewer with carrier tracking enabled
3. Search for carriers and see them displayed on the map
