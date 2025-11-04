"""Pytest configuration for tests."""

import sys
import tempfile
import yaml
from pathlib import Path
from datetime import datetime, timedelta

import pytest

# Add the parent directory to the path so we can import plc_visualizer
parent_dir = Path(__file__).parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

from plc_visualizer.models import LogEntry, ParsedLog, ParseResult, SignalType
from plc_visualizer.utils import SignalData, SignalState


@pytest.fixture
def sample_signal_data_with_transitions():
    """Create sample signal data with multiple transitions for interval testing."""
    base_time = datetime(2024, 1, 1, 10, 0, 0)
    device_id = "TEST_DEVICE"
    signal_name = "TEST_BOOLEAN_SIGNAL"
    
    # Create states with various durations for testing
    states = [
        SignalState(
            start_time=base_time,
            end_time=base_time + timedelta(seconds=1.5),
            value=True,
            start_offset=0.0,
            end_offset=1.5
        ),
        SignalState(
            start_time=base_time + timedelta(seconds=1.5),
            end_time=base_time + timedelta(seconds=3.0),
            value=False,
            start_offset=1.5,
            end_offset=3.0
        ),
        SignalState(
            start_time=base_time + timedelta(seconds=3.0),
            end_time=base_time + timedelta(seconds=4.2),
            value=True,
            start_offset=3.0,
            end_offset=4.2
        ),
        SignalState(
            start_time=base_time + timedelta(seconds=4.2),
            end_time=base_time + timedelta(seconds=6.0),
            value=False,
            start_offset=4.2,
            end_offset=6.0
        ),
        SignalState(
            start_time=base_time + timedelta(seconds=6.0),
            end_time=base_time + timedelta(seconds=7.8),
            value=True,
            start_offset=6.0,
            end_offset=7.8
        ),
    ]
    
    return SignalData(
        name=signal_name,
        device_id=device_id,
        key=f"{device_id}::{signal_name}",
        signal_type=SignalType.BOOLEAN,
        states=states,
        _entries_count=len(states)
    )


@pytest.fixture
def parsed_log_with_processing_time():
    """Create a ParsedLog with known processing time for testing stats display."""
    base_time = datetime(2024, 1, 1, 10, 0, 0)
    device_id = "TEST_DEVICE"
    
    entries = [
        LogEntry(device_id, "SIGNAL_A", base_time, True, SignalType.BOOLEAN),
        LogEntry(device_id, "SIGNAL_B", base_time + timedelta(seconds=1), 42, SignalType.INTEGER),
        LogEntry(device_id, "SIGNAL_C", base_time + timedelta(seconds=2), "TEST", SignalType.STRING),
    ]
    
    parsed_log = ParsedLog(
        entries=entries,
        signals={f"{device_id}::{e.signal_name}" for e in entries},
        devices={device_id},
        time_range=(base_time, base_time + timedelta(seconds=2))
    )
    
    # Create result with processing time
    result = ParseResult(
        data=parsed_log,
        errors=[],
        processing_time=0.456  # Known processing time for testing
    )
    
    return result


@pytest.fixture
def sample_yaml_config_file():
    """Create a temporary YAML config file for testing."""
    config = {
        "default_color": "#D3D3D3",
        "xml_parsing": {
            "attributes_to_extract": ["type", "id", "name"],
            "child_elements_to_extract": ["Text", "Size", "Location", "UnitId"],
            "render_as_text_types": [
                "System.Windows.Forms.Label, System.Windows.Forms, Version=4.0.0.0, Culture=neutral, PublicKeyToken=b77a5c561934e089"
            ],
            "render_as_arrow_types": [
                "SmartFactory.SmartCIM.GUI.Widgets.WidgetArrow, SmartFactory.SmartCIM.GUI, Version=1.0.0.0, Culture=neutral, PublicKeyToken=null"
            ],
            "type_color_mapping": {
                "default": "#D3D3D3",
                "special_type": "#FF5733"
            },
            "type_zindex_mapping": {
                "WidgetPort": 10,
                "WidgetBelt": 5,
                "default": 0
            },
            "forecolor_mapping": {
                "HotTrack": "#0066CC",
                "Black": "#000000",
                "Red": "#FF0000",
                "Green": "#00FF00",
                "Blue": "#0000FF",
                "default": "#000000"
            }
        },
        "device_to_unit": [
            {"pattern": "TEST*", "unit_id": "*"}
        ],
        "rules": []
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(config, f)
        temp_path = f.name
    
    yield temp_path
    
    # Cleanup
    Path(temp_path).unlink()


@pytest.fixture
def complete_test_dataset():
    """Create a complete dataset with parsed log and multiple signal types."""
    base_time = datetime(2024, 1, 1, 10, 0, 0)
    device_id = "TEST_DEVICE"
    
    entries = [
        LogEntry(device_id, "BOOLEAN_SIGNAL", base_time, True, SignalType.BOOLEAN),
        LogEntry(device_id, "INTEGER_SIGNAL", base_time, 100, SignalType.INTEGER),
        LogEntry(device_id, "STRING_SIGNAL", base_time, "INIT", SignalType.STRING),
        LogEntry(device_id, "BOOLEAN_SIGNAL", base_time + timedelta(seconds=1), False, SignalType.BOOLEAN),
        LogEntry(device_id, "INTEGER_SIGNAL", base_time + timedelta(seconds=1.5), 200, SignalType.INTEGER),
        LogEntry(device_id, "STRING_SIGNAL", base_time + timedelta(seconds=2), "ACTIVE", SignalType.STRING),
        LogEntry(device_id, "BOOLEAN_SIGNAL", base_time + timedelta(seconds=3), True, SignalType.BOOLEAN),
    ]
    
    parsed_log = ParsedLog(
        entries=entries,
        signals={f"{device_id}::{e.signal_name}" for e in entries},
        devices={device_id},
        time_range=(base_time, base_time + timedelta(seconds=3))
    )
    
    # Create signal data for each signal
    signal_data_list = []
    signals_by_name = {}
    for entry in entries:
        if entry.signal_name not in signals_by_name:
            signals_by_name[entry.signal_name] = []
        signals_by_name[entry.signal_name].append(entry)
    
    for signal_name, signal_entries in signals_by_name.items():
        states = []
        for i, entry in enumerate(signal_entries):
            end_time = signal_entries[i + 1].timestamp if i + 1 < len(signal_entries) else base_time + timedelta(seconds=10)
            states.append(SignalState(
                start_time=entry.timestamp,
                end_time=end_time,
                value=entry.value,
                start_offset=(entry.timestamp - base_time).total_seconds(),
                end_offset=(end_time - base_time).total_seconds()
            ))
        
        signal_data_list.append(SignalData(
            name=signal_name,
            device_id=device_id,
            key=f"{device_id}::{signal_name}",
            signal_type=signal_entries[0].signal_type,
            states=states,
            _entries_count=len(signal_entries)
        ))
    
    return parsed_log, signal_data_list
