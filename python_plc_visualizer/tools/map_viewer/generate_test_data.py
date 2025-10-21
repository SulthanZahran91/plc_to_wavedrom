#!/usr/bin/env python3
"""
Generate test XML map and corresponding signal data for the map viewer.

This script creates:
1. test_map.xml - A conveyor system map with various widgets
2. test_signals.csv - Simulated signal data for the conveyor units

Usage:
    python generate_test_data.py
    python generate_test_data.py --num-units 20 --duration 60
"""

import argparse
import csv
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Tuple
import xml.etree.ElementTree as ET
from xml.dom import minidom


def generate_xml_map(num_units: int = 10) -> str:
    """Generate a test XML map with conveyor widgets.

    Args:
        num_units: Number of conveyor units to generate

    Returns:
        Formatted XML string
    """
    root = ET.Element("ConveyorMap")
    root.set("version", "1.0")

    # Layout parameters
    col_width = 120
    row_height = 80
    margin = 50

    # Generate conveyor belts in a grid
    for i in range(num_units):
        row = i // 4
        col = i % 4
        x = margin + col * col_width
        y = margin + row * row_height

        obj = ET.SubElement(root, "Object")
        unit_id = f"B1ACNV{13301 + i:03d}-104"
        obj.set("name", f"Belt_{i:02d}")
        obj.set("type", "SmartFactory.SmartCIM.GUI.Widgets.WidgetBelt, SmartFactory.SmartCIM.GUI, Version=1.0.0.0, Culture=neutral, PublicKeyToken=null")

        ET.SubElement(obj, "Size").text = f"{col_width - 20}, 40"
        ET.SubElement(obj, "Location").text = f"{x}, {y}"
        ET.SubElement(obj, "UnitId").text = unit_id
        ET.SubElement(obj, "Text").text = unit_id

        # Add labels for each belt
        label = ET.SubElement(root, "Object")
        label.set("name", f"Label_{i:02d}")
        label.set("type", "System.Windows.Forms.Label, System.Windows.Forms, Version=4.0.0.0, Culture=neutral, PublicKeyToken=b77a5c561934e089")

        ET.SubElement(label, "Size").text = f"{col_width - 20}, 20"
        ET.SubElement(label, "Location").text = f"{x}, {y - 22}"
        ET.SubElement(label, "Text").text = f"Belt {i:02d}"
        ET.SubElement(label, "UnitId").text = unit_id

    # Add some diverters
    for i in range(min(3, num_units // 3)):
        row = i + num_units // 4 + 1
        col = 1
        x = margin + col * col_width
        y = margin + row * row_height

        obj = ET.SubElement(root, "Object")
        unit_id = f"B1ACDV{14001 + i:03d}-104"
        obj.set("name", f"Diverter_{i:02d}")
        obj.set("type", "SmartFactory.SmartCIM.GUI.Widgets.WidgetDiverter, SmartFactory.SmartCIM.GUI, Version=1.0.0.0, Culture=neutral, PublicKeyToken=null")

        ET.SubElement(obj, "Size").text = "60, 60"
        ET.SubElement(obj, "Location").text = f"{x}, {y}"
        ET.SubElement(obj, "UnitId").text = unit_id

        # Label
        label = ET.SubElement(root, "Object")
        label.set("name", f"DiverterLabel_{i:02d}")
        label.set("type", "System.Windows.Forms.Label, System.Windows.Forms, Version=4.0.0.0, Culture=neutral, PublicKeyToken=b77a5c561934e089")
        ET.SubElement(label, "Size").text = "60, 20"
        ET.SubElement(label, "Location").text = f"{x}, {y - 22}"
        ET.SubElement(label, "Text").text = f"Div {i:02d}"
        ET.SubElement(label, "UnitId").text = unit_id

    # Add some conveyor ports
    for i in range(min(2, num_units // 5)):
        row = num_units // 4 + 2
        col = i * 2
        x = margin + col * col_width
        y = margin + row * row_height

        obj = ET.SubElement(root, "Object")
        unit_id = f"B1ACPT{15001 + i:03d}-104"
        obj.set("name", f"Port_{i:02d}")
        obj.set("type", "SmartFactory.SmartCIM.GUI.Widgets.WidgetConveyorPort, SmartFactory.SmartCIM.GUI, Version=1.0.0.0, Culture=neutral, PublicKeyToken=null")

        ET.SubElement(obj, "Size").text = "50, 50"
        ET.SubElement(obj, "Location").text = f"{x}, {y}"
        ET.SubElement(obj, "UnitId").text = unit_id

        # Label
        label = ET.SubElement(root, "Object")
        label.set("name", f"PortLabel_{i:02d}")
        label.set("type", "System.Windows.Forms.Label, System.Windows.Forms, Version=4.0.0.0, Culture=neutral, PublicKeyToken=b77a5c561934e089")
        ET.SubElement(label, "Size").text = "50, 20"
        ET.SubElement(label, "Location").text = f"{x}, {y - 22}"
        ET.SubElement(label, "Text").text = f"Port {i:02d}"
        ET.SubElement(label, "UnitId").text = unit_id

    # Add some arrows to show flow direction
    for i in range(min(num_units - 1, 8)):
        row = i // 4
        col = i % 4
        x = margin + col * col_width + col_width - 30
        y = margin + row * row_height + 10

        arrow = ET.SubElement(root, "Object")
        arrow.set("name", f"Arrow_{i:02d}")
        arrow.set("type", "SmartFactory.SmartCIM.GUI.Widgets.WidgetArrow, SmartFactory.SmartCIM.GUI, Version=1.0.0.0, Culture=neutral, PublicKeyToken=null")

        ET.SubElement(arrow, "Size").text = "30, 20"
        ET.SubElement(arrow, "Location").text = f"{x}, {y}"
        ET.SubElement(arrow, "FlowDirection").text = "Angle_90"  # Right arrow
        ET.SubElement(arrow, "LineThick").text = "3"
        ET.SubElement(arrow, "EndCap").text = "ArrowAnchor"
        ET.SubElement(arrow, "ForeColor").text = "HotTrack"

    # Format XML with pretty printing
    xml_str = ET.tostring(root, encoding='unicode')
    dom = minidom.parseString(xml_str)
    return dom.toprettyxml(indent="  ")


def generate_signal_data(num_units: int = 10, duration_seconds: int = 30) -> List[Tuple]:
    """Generate test signal data for conveyor units.

    Args:
        num_units: Number of units to generate signals for
        duration_seconds: Duration of signal data in seconds

    Returns:
        List of (timestamp, device_id, signal_name, value) tuples
    """
    signals = []
    start_time = datetime.now()

    # Generate UnitIds matching the XML
    unit_ids = [f"B1ACNV{13301 + i:03d}-104" for i in range(num_units)]

    # Add some diverters
    unit_ids.extend([f"B1ACDV{14001 + i:03d}-104" for i in range(min(3, num_units // 3))])

    # Add some ports
    unit_ids.extend([f"B1ACPT{15001 + i:03d}-104" for i in range(min(2, num_units // 5))])

    # Generate signals at different intervals
    time_step = 0.5  # 500ms intervals

    for t in range(0, int(duration_seconds / time_step)):
        timestamp = start_time + timedelta(seconds=t * time_step)

        # Each unit has a chance to change state
        for unit_id in unit_ids:
            if random.random() < 0.1:  # 10% chance per time step
                # Device ID format: UnitId@DeviceName
                device_id = f"{unit_id}@D19"

                # Generate different signal types
                signal_type = random.choice(['Status', 'A', 'B', 'Speed'])

                if signal_type == 'Status':
                    value = random.choice(['Idle', 'Running', 'Stopped', 'Error'])
                elif signal_type == 'A':
                    value = random.randint(0, 3)
                elif signal_type == 'B':
                    value = random.randint(0, 100)
                else:  # Speed
                    value = round(random.uniform(0, 1.5), 2)

                signals.append((
                    timestamp.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3],
                    device_id,
                    signal_type,
                    value
                ))

    # Sort by timestamp
    signals.sort(key=lambda x: x[0])

    return signals


def main():
    parser = argparse.ArgumentParser(
        description='Generate test data for map viewer',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate with defaults (10 units, 30 seconds)
  python generate_test_data.py

  # Generate larger test set
  python generate_test_data.py --num-units 20 --duration 60

  # Specify output directory
  python generate_test_data.py --output-dir /path/to/output
        """
    )

    parser.add_argument(
        '--num-units',
        type=int,
        default=10,
        help='Number of conveyor units to generate (default: 10)'
    )

    parser.add_argument(
        '--duration',
        type=int,
        default=30,
        help='Duration of signal data in seconds (default: 30)'
    )

    parser.add_argument(
        '--output-dir',
        type=Path,
        default=Path.cwd(),
        help='Output directory for generated files (default: current directory)'
    )

    parser.add_argument(
        '--seed',
        type=int,
        default=None,
        help='Random seed for reproducible output'
    )

    args = parser.parse_args()

    # Set random seed if provided
    if args.seed is not None:
        random.seed(args.seed)

    # Create output directory if it doesn't exist
    args.output_dir.mkdir(parents=True, exist_ok=True)

    # Generate XML map
    print(f"Generating XML map with {args.num_units} units...")
    xml_content = generate_xml_map(args.num_units)
    xml_path = args.output_dir / "test_map.xml"

    with open(xml_path, 'w', encoding='utf-8') as f:
        f.write(xml_content)

    print(f"✓ Created: {xml_path}")

    # Generate signal data
    print(f"Generating signal data ({args.duration} seconds)...")
    signals = generate_signal_data(args.num_units, args.duration)
    csv_path = args.output_dir / "test_signals.csv"

    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Timestamp', 'DeviceID', 'Signal', 'Value'])
        writer.writerows(signals)

    print(f"✓ Created: {csv_path} ({len(signals)} signal events)")

    # Create a README for the generated data
    readme_content = f"""# Generated Test Data

Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Files

- **test_map.xml**: Conveyor map with {args.num_units} units
- **test_signals.csv**: Signal data with {len(signals)} events over {args.duration} seconds

## Map Units

- Conveyor Belts: B1ACNV13301-104 through B1ACNV{13301 + args.num_units - 1:05d}-104
- Diverters: B1ACDV14001-104 through B1ACDV{14001 + min(3, args.num_units // 3) - 1:05d}-104
- Ports: B1ACPT15001-104 through B1ACPT{15001 + min(2, args.num_units // 5) - 1:05d}-104

## Signal Types

- **Status**: Idle, Running, Stopped, Error
- **A**: Integer values 0-3
- **B**: Integer values 0-100
- **Speed**: Float values 0.0-1.5

## Usage

### Run the basic demo:
```bash
python example_main.py {xml_path}
```

### Run the integration demo:
```bash
python example_main_integration.py {xml_path}
```

### Load signals programmatically:
```python
import csv
from datetime import datetime
from map_viewer.state_model import SignalEvent

with open('{csv_path}', 'r') as f:
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
"""

    readme_path = args.output_dir / "TEST_DATA_README.md"
    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write(readme_content)

    print(f"✓ Created: {readme_path}")

    print("\n" + "="*60)
    print("Test data generation complete!")
    print("="*60)
    print(f"\nGenerated files in: {args.output_dir.absolute()}")
    print(f"  - {xml_path.name} ({args.num_units} conveyor units)")
    print(f"  - {csv_path.name} ({len(signals)} signal events)")
    print(f"  - {readme_path.name} (usage instructions)")
    print(f"\nTo test the map viewer:")
    print(f"  python example_main.py {xml_path}")
    print(f"  python example_main_integration.py {xml_path}")


if __name__ == '__main__':
    main()
