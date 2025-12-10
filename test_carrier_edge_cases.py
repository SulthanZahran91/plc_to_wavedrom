"""Test carrier tracking edge cases."""
import sys
from pathlib import Path

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from PySide6.QtGui import QColor
from tools.map_viewer.state_model import UnitStateModel, SignalEvent
from tools.map_viewer.device_mapping import DeviceUnitMap
from tools.map_viewer.color_policy import ColorPolicy


def test_multiple_carriers_same_unit():
    """Test Edge Case 1: Multiple carriers at same location."""
    print("\\n=== Test 1: Multiple Carriers at Same Unit ===")
    
    # Create minimal state model
    device_map = DeviceUnitMap({})
    color_policy = ColorPolicy({})
    model = UnitStateModel(device_map, color_policy)
    model.enable_carrier_tracking = True
    
    # Track state changes
    changes = []
    model.stateChanged.connect(lambda u, b, a, t: changes.append((u, t)))
    
    # Add carrier A to unit U1
    event1 = SignalEvent(device_id="CarrierA", signal_name="CurrentLocation", 
                         value="U1", timestamp=1.0)
    model.on_signal(event1)
    
    assert len(changes) == 1
    assert changes[0][0] == "U1"
    assert changes[0][1] == ("CarrierA", QColor(0, 0, 0))  # Single carrier shows ID
    print("✓ Single carrier shows CarrierID: CarrierA")
    
    # Add carrier B to same unit U1
    changes.clear()
    event2 = SignalEvent(device_id="CarrierB", signal_name="CurrentLocation",
                         value="U1", timestamp=2.0)
    model.on_signal(event2)
    
    assert len(changes) == 1
    assert changes[0][0] == "U1"
    assert changes[0][1] == ("2x", QColor(0, 0, 0))  # Multiple carriers show count
    print("✓ Two carriers show count: 2x")
    
    # Add carrier C to U1
    changes.clear()
    event3 = SignalEvent(device_id="CarrierC", signal_name="CurrentLocation",
                         value="U1", timestamp=3.0)
    model.on_signal(event3)
    
    assert len(changes) == 1
    assert changes[0][1] == ("3x", QColor(0, 0, 0))  # Three carriers
    print("✓ Three carriers show count: 3x")
    
    # Remove carrier B
    changes.clear()
    event4 = SignalEvent(device_id="CarrierB", signal_name="CurrentLocation",
                         value="U2", timestamp=4.0)  # Moved to different unit
    model.on_signal(event4)
    
    # Should update U1 to show 2x and U2 to show CarrierB
    u1_update = [c for c in changes if c[0] == "U1"]
    assert len(u1_update) == 1
    assert u1_update[0][1] == ("2x", QColor(0, 0, 0))  # Back to 2 carriers
    print("✓ After one leaves, count updates: 2x")
    
    # Remove carrier A
    changes.clear()
    event5 = SignalEvent(device_id="CarrierA", signal_name="CurrentLocation",
                         value="U3", timestamp=5.0)
    model.on_signal(event5)
    
    u1_update = [c for c in changes if c[0] == "U1"]
    assert len(u1_update) == 1
    assert u1_update[0][1] == ("CarrierC", QColor(0, 0, 0))  # Only one left
    print("✓ After another leaves, shows single CarrierID: CarrierC")
    
    # Remove last carrier
    changes.clear()
    event6 = SignalEvent(device_id="CarrierC", signal_name="CurrentLocation",
                         value="U4", timestamp=6.0)
    model.on_signal(event6)
    
    u1_update = [c for c in changes if c[0] == "U1"]
    assert len(u1_update) == 1
    assert u1_update[0][1] is None  # All carriers gone
    print("✓ After all leave, overlay cleared: None")
    
    print("\\n✅ Test 1 PASSED: Multiple carriers handled correctly")


def test_null_location_clears_overlay():
    """Test Edge Case 2: Null/empty location values."""
    print("\\n=== Test 2: Null Location Clears Overlay ===")
    
    device_map = DeviceUnitMap({})
    color_policy = ColorPolicy({})
    model = UnitStateModel(device_map, color_policy)
    model.enable_carrier_tracking = True
    
    changes = []
    model.stateChanged.connect(lambda u, b, a, t: changes.append((u, t)))
    
    # Add carrier to unit
    event1 = SignalEvent(device_id="CarrierX", signal_name="CurrentLocation",
                         value="U1", timestamp=1.0)
    model.on_signal(event1)
    
    assert changes[-1] == ("U1", ("CarrierX", QColor(0, 0, 0)))
    print("✓ Carrier added to U1")
    
    # Send null location
    changes.clear()
    event2 = SignalEvent(device_id="CarrierX", signal_name="CurrentLocation",
                         value=None, timestamp=2.0)
    model.on_signal(event2)
    
    u1_update = [c for c in changes if c[0] == "U1"]
    assert len(u1_update) == 1
    assert u1_update[0][1] is None  # Overlay cleared
    
    # Verify carrier removed from tracking
    assert model.get_carrier_location("CarrierX") is None
    print("✓ Null location clears overlay and removes from tracking")
    
    # Test empty string
    event3 = SignalEvent(device_id="CarrierY", signal_name="CurrentLocation",
                         value="U2", timestamp=3.0)
    model.on_signal(event3)
    
    changes.clear()
    event4 = SignalEvent(device_id="CarrierY", signal_name="CurrentLocation",
                         value="", timestamp=4.0)
    model.on_signal(event4)
    
    u2_update = [c for c in changes if c[0] == "U2"]
    assert len(u2_update) == 1
    assert u2_update[0][1] is None
    print("✓ Empty string location also clears overlay")
    
    print("\\n✅ Test 2 PASSED: Null/empty locations handled correctly")


def test_get_carriers_at_unit():
    """Test helper method for info box display."""
    print("\\n=== Test 3: Get Carriers at Unit (for Info Box) ===")
    
    device_map = DeviceUnitMap({})
    color_policy = ColorPolicy({})
    model = UnitStateModel(device_map, color_policy)
    model.enable_carrier_tracking = True
    
    # Add multiple carriers to same unit
    for carrier_id in ["C1", "C2", "C3"]:
        event = SignalEvent(device_id=carrier_id, signal_name="CurrentLocation",
                           value="U1", timestamp=1.0)
        model.on_signal(event)
    
    carriers = model.get_carriers_at_unit("U1")
    assert len(carriers) == 3
    assert set(carriers) == {"C1", "C2", "C3"}
    print(f"✓ get_carriers_at_unit returns all carriers: {carriers}")
    
    # Test empty unit
    carriers_empty = model.get_carriers_at_unit("U999")
    assert carriers_empty == []
    print("✓ Empty unit returns empty list")
    
    print("\\n✅ Test 3 PASSED: Info box query works correctly")


if __name__ == "__main__":
    try:
        test_multiple_carriers_same_unit()
        test_null_location_clears_overlay()
        test_get_carriers_at_unit()
        
        print("\\n" + "="*50)
        print("🎉 ALL TESTS PASSED!")
        print("="*50)
    except AssertionError as e:
        print(f"\\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
