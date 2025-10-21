# PLC Map Viewer

Modular viewer for PLC/conveyor system maps with real-time signal-driven color updates.

## Components

### Core Modules

- **parser_xml.MapParser** — XML → dict parser. Emits `objectsParsed(dict)` and a stub `stateChanged(unit_id, QColor)` (demo only).
- **renderer.MapRenderer** — QGraphicsView-based renderer with methods:
  - `set_objects(objects: dict)` — Render parsed objects
  - `update_rect_color_by_unit(unit_id: str, color: QColor) -> int` — Update colors by UnitId
- **media_controls.MediaControls** — Bottom media bar UI (no functionality yet, ready for integration)

### Integration Layer

- **device_mapping.DeviceUnitMap** — Maps device IDs (from signals) to UnitIds (from XML) using fnmatch patterns
- **color_policy.ColorPolicy** — Defines rules to map signal values to colors with priority support
- **state_model.UnitStateModel** — Central state model that processes signal events and emits color updates
- **config_loader** — YAML-based configuration loader for mappings and rules

### Demo Scripts

- **generate_test_data.py** — Generates test XML map and CSV signal data
- **playback_demo.py** — Interactive playback of CSV signal data with timeline controls
- **example_main.py** — Basic demo with random state changes
- **example_main_integration.py** — Integration demo with timer-based signals

## Quick Start

### Prerequisites

1. **Python 3.10+** with PySide6 and PyYAML installed
2. **XML map file** (or generate test data - see below)

### Generate Test Data

The easiest way to get started is to generate test data:

```bash
# Generate test XML map + signal data
python generate_test_data.py

# This creates:
#   - test_map.xml (10 conveyor units with belts, diverters, ports)
#   - test_signals.csv (30 seconds of simulated signal data)
#   - TEST_DATA_README.md (usage instructions)

# Customize generation:
python generate_test_data.py --num-units 20 --duration 60
```

### Run the Playback Demo (Recommended)

The playback demo loads the generated data and replays signals in real-time:

```bash
# Generate test data first
python generate_test_data.py

# Run playback demo
python playback_demo.py

# Or specify custom files
python playback_demo.py --map test_map.xml --signals test_signals.csv --speed 2.0
```

Features:
- ▶/⏸ Play/Pause controls
- Speed control (0.25× to 2.0×)
- Progress slider for seeking
- Real-time signal-driven color updates

### Run the Basic Demo

```bash
python example_main.py test_map.xml
```

This runs a basic demo with random simulated state changes cycling through colors.

### Run the Full Integration Demo

```bash
python example_main_integration.py test_map.xml
```

This demonstrates signal-driven color updates with a simple timer-based signal generator.

## Integration with plc_to_wavedrom

### Approach

1. **Keep renderer "dumb"** — It just draws shapes and exposes `update_rect_color_by_unit(unit_id, QColor)`
2. **Mapping layer** — DeviceUnitMap translates your device IDs → XML UnitIds
3. **Color policy** — ColorPolicy turns `(unit_id, signal_name, value)` into colors
4. **State model** — UnitStateModel listens to device signals, applies mapping + policy, emits color updates

### Setup

```python
from map_viewer import MapParser, MapRenderer
from map_viewer.state_model import UnitStateModel, SignalEvent
from map_viewer.config_loader import load_mapping_and_policy

# 1. Set up the renderer
renderer = MapRenderer()
parser = MapParser()
parser.objectsParsed.connect(renderer.set_objects)
objects = parser.parse_file("your_map.xml")

# 2. Load mapping and color rules
device_map, color_policy = load_mapping_and_policy("mappings_and_rules.yaml")

# 3. Create state model and connect to renderer
state_model = UnitStateModel(device_map, color_policy)
state_model.stateChanged.connect(renderer.update_rect_color_by_unit)

# 4. Send signals to the state model
state_model.on_signal(SignalEvent(
    device_id="B1ACNV13301-104@D19",
    signal_name="A",
    value=1,
    timestamp=time.time()
))
```

### Configuration (YAML)

See `mappings_and_rules.yaml` for examples. The configuration includes:

- **device_to_unit**: Wildcard patterns mapping device IDs to UnitIds
- **rules**: Signal-based color rules with operators (`==`, `>`, `<`, etc.)
- **priority**: Higher priority rules override lower ones

Example rule:
```yaml
- signal: "Status"
  op: "=="
  value: "Running"
  color: "#00FF00"
  unit_id: "B1ACNV13301-104"  # Optional: specific to one unit
  priority: 10
```

## Features

- **Interactive map** with pan (middle mouse), zoom (scroll wheel), and selection
- **Info box** displays object details on click
- **Z-ordering** for proper layering of different object types
- **Arrow rendering** with flow directions and arrow caps
- **Real-time updates** through signal/slot connections
- **Config-driven** color rules (no code changes needed)

## Keyboard Shortcuts

- `R` — Reset view (fit to screen)
- `+/=` — Zoom in
- `-` — Zoom out
- `ESC` — Clear selection and hide info box

## Notes

- The media bar is intentionally UI-only and ready for playback integration
- `start_demo_state_changes()` in MapParser is for demo/testing only
- The renderer indexes shapes by `UnitId` for O(1) color updates
- Signal events can come from any thread (Qt signals handle thread safety)

## Architecture Benefits

- **Decoupled** — Renderer doesn't know about signals or business logic
- **Testable** — All components can be unit tested independently
- **Config-driven** — Operators can modify rules without touching code
- **Extensible** — Easy to add new rule types, timeouts, multi-signal conditions, etc.

## Future Enhancements

Potential additions:
- Staleness timeout (revert to gray if no updates for N seconds)
- Multi-signal aggregation (e.g., "if A high AND B low → amber")
- Regex patterns for signal names
- Per-unit rule priority overrides
