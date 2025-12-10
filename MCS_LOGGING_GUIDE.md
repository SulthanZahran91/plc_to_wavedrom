# Enabling Verbose Logging for MCS Parser

The MCS parser now includes comprehensive logging to help debug parsing issues.

## Logging Levels

The parser uses the following log levels:

- **INFO**: High-level progress and results
  - Format detection results
  - Parse start/complete with summary stats
  - Progress updates every 10,000 lines
  
- **DEBUG**: Detailed line-by-line parsing (very verbose!)
  - Each line's format detection (1-param vs 2-param)
  - Number of entries generated per line
  - Lines that don't match the regex

- **WARNING**: Issues encountered
  - Timestamp parsing failures
  - Other recoverable errors

## How to Enable Logging

### In Your Application

Add this to the top of your main application file:

```python
import logging

# For INFO level logging (recommended)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# For DEBUG level logging (very verbose, shows every line)
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

### From Command Line

When running the visualizer from command line:

```bash
# INFO level
PYTHONPATH=/home/dev/plc_to_wavedrom/python_plc_visualizer \
  python3 -c "import logging; logging.basicConfig(level=logging.INFO); \
  from plc_visualizer.main import main; main()"

# DEBUG level (very verbose)
PYTHONPATH=/home/dev/plc_to_wavedrom/python_plc_visualizer \
  python3 -c "import logging; logging.basicConfig(level=logging.DEBUG); \
  from plc_visualizer.main import main; main()"
```

## What Gets Logged

### Example INFO Log Output

```
14:23:45 - plc_visualizer.parsers.mcs_parser - INFO - MCS parser detection: 10/10 lines matched (result: True) - /path/to/file.log
14:23:45 - plc_visualizer.parsers.mcs_parser - INFO - MCS parser starting single-threaded parse of: /path/to/file.log
14:23:46 - plc_visualizer.parsers.mcs_parser - INFO - MCS parse progress: 10000 lines processed, 19234 entries so far
14:23:47 - plc_visualizer.parsers.mcs_parser - INFO - MCS parse progress: 20000 lines processed, 38891 entries so far
14:23:48 - plc_visualizer.parsers.mcs_parser - INFO - MCS parse complete: 95432 entries, 145 devices, 1203 signals, 0 errors in 3.42s
```

### Example DEBUG Log Output (abbreviated)

```
14:23:45 - plc_visualizer.parsers.mcs_parser - DEBUG - MCS format detected (1-param): carrier=SDADTN490165
14:23:45 - plc_visualizer.parsers.mcs_parser - DEBUG - MCS line parsed into 2 entries for device SDADTN490165
14:23:45 - plc_visualizer.parsers.mcs_parser - DEBUG - MCS format detected (2-param): carrier=BBADFB0397, cmd=336182
14:23:45 - plc_visualizer.parsers.mcs_parser - DEBUG - MCS line parsed into 3 entries for device BBADFB0397
14:23:45 - plc_visualizer.parsers.mcs_parser - WARNING - Failed to parse timestamp: invalid-timestamp
```

## Performance Note

- **INFO logging**: Minimal performance impact (<5%)
- **DEBUG logging**: Significant performance impact (20-30% slower due to per-line logging)
  - Only use DEBUG for troubleshooting specific issues
  - Recommended for small test files only

## Logging in Multiprocessing Mode

Note: When using multiprocessing (num_workers > 1), worker processes may not emit logs unless configured specially. The main process will still log detection and summary information.

To see worker logs, use single-threaded mode:
```python
result = parser.parse(file_path, num_workers=1)  # or num_workers=None
```
