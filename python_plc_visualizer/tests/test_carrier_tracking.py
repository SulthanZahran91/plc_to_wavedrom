#!/usr/bin/env python3
"""
Test script for carrier tracking functionality.

This script tests the UnitStateModel's carrier tracking logic.
"""

from PySide6.QtGui import QColor
from python_plc_visualizer.tools.map_viewer.state_model import UnitStateModel, SignalEvent
from python_plc_visualizer.tools.map_viewer.device_mapping import DeviceUnitMap
from python_plc_visualizer.tools.map_viewer.color_policy import ColorPolicy


def test_carrier_tracking():
    """Test carrier tracking functionality."""
    print("Testing Carrier Tracking...")
    
    # Create minimal device map and color policy
    device_map = DeviceUnitMap({})
    color_policy = ColorPolicy({})
    
    # Create state model
    model = UnitStateModel(device_map, color_policy)
    
    # Test 1: Carrier tracking disabled by default
    assert not model.enable_carrier_tracking, "Carrier tracking should be disabled by default"
    print("✓ Test 1 passed: Carrier tracking disabled by default")
    
    # Test 2: Enable carrier tracking
    model.enable_carrier_tracking = True
    assert model.enable_carrier_tracking, "Carrier tracking should be enabled"
    print("✓ Test 2 passed: Can enable carrier tracking")
    
    # Test 3: Add carrier location
    event1 = SignalEvent(
        device_id="CARRIER001",
        signal_name="CurrentLocation",
        value="UNIT_A",
        timestamp=1000.0
    )
    model.on_signal(event1)
    
    location = model.get_carrier_location("CARRIER001")
    assert location == "UNIT_A", f"Expected UNIT_A, got {location}"
    print("✓ Test 3 passed: Carrier location tracked correctly")
    
    # Test 4: Move carrier to new location
    event2 = SignalEvent(
        device_id="CARRIER001",
        signal_name="CurrentLocation",
        value="UNIT_B",
        timestamp=2000.0
    )
    model.on_signal(event2)
    
    location = model.get_carrier_location("CARRIER001")
    assert location == "UNIT_B", f"Expected UNIT_B, got {location}"
    print("✓ Test 4 passed: Carrier moved to new location")
    
    # Test 5: Multiple carriers at different locations
    event3 = SignalEvent(
        device_id="CARRIER002",
        signal_name="CurrentLocation",
        value="UNIT_A",
        timestamp=3000.0
    )
    model.on_signal(event3)
    
    carriers_at_a = model.get_carriers_at_unit("UNIT_A")
    assert "CARRIER002" in carriers_at_a, "CARRIER002 should be at UNIT_A"
    # CRITICAL: Verify CARRIER001 is NOT at UNIT_A after moving to UNIT_B
    assert "CARRIER001" not in carriers_at_a, "CARRIER001 should NOT be at UNIT_A (it moved to UNIT_B)"
    print("✓ Test 5 passed: Multiple carriers tracked independently")
    
    # Test 6: Disable carrier tracking clears state
    model.enable_carrier_tracking = False
    
    location = model.get_carrier_location("CARRIER001")
    assert location is None, "Location should be cleared when tracking disabled"
    print("✓ Test 6 passed: Disabling tracking clears state")
    
    print("\n✅ All tests passed!")


if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    import sys
    
    # Need QApplication for QColor
    app = QApplication(sys.argv)
    
    try:
        test_carrier_tracking()
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
