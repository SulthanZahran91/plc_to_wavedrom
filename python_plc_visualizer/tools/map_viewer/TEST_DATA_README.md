# Generated Test Data

Generated on: 2025-10-21 23:08:27

## Files

- **test_map.xml**: Conveyor map with 10 units
- **test_signals.csv**: Signal data with 85 events over 30 seconds

## Map Units

- Conveyor Belts: B1ACNV13301-104 through B1ACNV13310-104
- Diverters: B1ACDV14001-104 through B1ACDV14003-104
- Ports: B1ACPT15001-104 through B1ACPT15002-104

## Signal Types

- **Status**: Idle, Running, Stopped, Error
- **A**: Integer values 0-3
- **B**: Integer values 0-100
- **Speed**: Float values 0.0-1.5

## Usage

### Run the basic demo:
```bash
python example_main.py /home/sulthanz/github/plc_to_wavedrom/python_plc_visualizer/tools/map_viewer/test_map.xml
```

### Run the integration demo:
```bash
python example_main_integration.py /home/sulthanz/github/plc_to_wavedrom/python_plc_visualizer/tools/map_viewer/test_map.xml
```

### Load signals programmatically:
```python
import csv
from datetime import datetime
from map_viewer.state_model import SignalEvent

with open('/home/sulthanz/github/plc_to_wavedrom/python_plc_visualizer/tools/map_viewer/test_signals.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        event = SignalEvent(
            device_id=row['DeviceID'],
            signal_name=row['Signal'],
            value=row['Value'],
            timestamp=datetime.strptime(row['Timestamp'], '%Y-%m-%d %H:%M:%S.%f').timestamp()
        )
        # Send to state model
        state_model.on_signal(event)
```

## Customizing

Regenerate with different parameters:
```bash
# More units
python generate_test_data.py --num-units 20

# Longer duration
python generate_test_data.py --duration 60

# Reproducible output
python generate_test_data.py --seed 42
```
