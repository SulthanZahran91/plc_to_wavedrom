# Map Viewer Quick Start Guide

Get up and running with the PLC Map Viewer in 3 steps!

## Step 1: Install Dependencies

```bash
cd python_plc_visualizer
uv pip install -e .
```

This installs PySide6, PyYAML, and all other dependencies.

## Step 2: Generate Test Data

```bash
cd tools/map_viewer
python generate_test_data.py
```

This creates:
- `test_map.xml` - A sample conveyor system map
- `test_signals.csv` - Simulated signal data
- `TEST_DATA_README.md` - Detailed usage instructions

## Step 3: Run the Playback Demo

```bash
python playback_demo.py
```

This opens an interactive viewer where you can:
- ▶/⏸ Play/pause signal playback
- Adjust playback speed (0.25× to 2.0×)
- Seek through the timeline
- Watch conveyor units change color based on signal values

## What You'll See

The map viewer displays:
- **Conveyor belts** (yellow/gray rectangles)
- **Diverters** (green squares)
- **Ports** (blue squares)
- **Arrows** showing flow direction
- **Labels** identifying each unit

Colors change in real-time based on signals:
- **Green** = Running
- **Red** = Error
- **Yellow** = Stopped
- **Blue-gray** = Idle
- Plus various colors for signal A, B, and Speed values

## Next Steps

### Customize Test Data

```bash
# Generate larger map
python generate_test_data.py --num-units 20 --duration 60

# Use a specific random seed for reproducibility
python generate_test_data.py --seed 42
```

### Modify Color Rules

Edit `mappings_and_rules.yaml` to change how signals map to colors:

```yaml
rules:
  - signal: "Status"
    op: "=="
    value: "Running"
    color: "#00FF00"  # Bright green
    priority: 100
```

### Integration with Your Data

See the full README in `map_viewer/README.md` for:
- Integration instructions
- API documentation
- Configuration details
- Architecture overview

## Troubleshooting

**Issue**: `ModuleNotFoundError: No module named 'PySide6'`
- **Solution**: Run `uv pip install -e .` from the `python_plc_visualizer` directory

**Issue**: `FileNotFoundError: test_map.xml not found`
- **Solution**: Run `python generate_test_data.py` first

**Issue**: Map is empty or units don't appear
- **Solution**: Check that the XML file has `<Object>` elements with proper `Size` and `Location` attributes

**Issue**: Colors don't update
- **Solution**: Verify `mappings_and_rules.yaml` patterns match your device IDs

## Files Overview

```
tools/map_viewer/
├── README.md                      # Full documentation
├── generate_test_data.py          # Generate test XML + signals
├── playback_demo.py               # Interactive playback demo
├── example_main.py                # Basic demo
├── example_main_integration.py    # Integration demo
├── mappings_and_rules.yaml        # Color rule configuration
├── __init__.py                    # Package exports
├── config.py                      # UI configuration
├── parser_xml.py                  # XML parser
├── renderer.py                    # Graphics renderer
├── media_controls.py              # Media control widgets
├── device_mapping.py              # Device→Unit mapping
├── color_policy.py                # Signal→Color rules
├── state_model.py                 # State management
└── config_loader.py               # YAML config loader
```

## Questions?

See the full README for detailed information:
```bash
cat map_viewer/README.md
```
