"""Unit tests for MCS Log Parser."""

import sys
import unittest
from datetime import datetime
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from plc_visualizer.parsers.mcs_parser import MCSLogParser
from plc_visualizer.models import SignalType


class TestMCSLogParser(unittest.TestCase):
    """Test cases for MCSLogParser."""
    
    def setUp(self):
        self.parser = MCSLogParser()
    
    def test_parse_update_line(self):
        """Test parsing a simple UPDATE line."""
        line = "2025-12-05 00:00:36.322 [UPDATE=336182, BBADFB0397] [CurrentLocation=B1ACNV13301-120]"
        entries = self.parser._parse_line_to_entries(line)
        
        # Should have 3 entries: _Action, _CommandID, CurrentLocation
        self.assertEqual(len(entries), 3)
        
        # Check device_id
        self.assertEqual(entries[0][0], "BBADFB0397")
        
        # Check _Action entry
        self.assertEqual(entries[0][1], "_Action")
        self.assertEqual(entries[0][3], "UPDATE")
        
        # Check _CommandID entry
        self.assertEqual(entries[1][1], "_CommandID")
        self.assertEqual(entries[1][3], "336182")
        
        # Check CurrentLocation entry
        self.assertEqual(entries[2][1], "CurrentLocation")
        self.assertEqual(entries[2][3], "B1ACNV13301-120")
    
    def test_parse_add_line(self):
        """Test parsing an ADD line with multiple key-value pairs."""
        line = "2025-12-05 00:00:38.574 [ADD=MANUAL_SKID-120500003857_000038574_0580, SDENTP490003] [CommandID=MANUAL_SKID-120500003857_000038574_0580], [IsBoost=False], [Priority=50], [TransferState=Queued]"
        entries = self.parser._parse_line_to_entries(line)
        
        # Should have entries for _Action, _CommandID, and each key-value pair
        self.assertGreater(len(entries), 4)
        
        # Check device_id
        self.assertEqual(entries[0][0], "SDENTP490003")
        
        # Check action
        self.assertEqual(entries[0][3], "ADD")
        
        # Find IsBoost entry (should be boolean False)
        is_boost = next((e for e in entries if e[1] == "IsBoost"), None)
        self.assertIsNotNone(is_boost)
        self.assertEqual(is_boost[3], False)
        self.assertEqual(is_boost[4], SignalType.BOOLEAN)
        
        # Find Priority entry (should be integer 50)
        priority = next((e for e in entries if e[1] == "Priority"), None)
        self.assertIsNotNone(priority)
        self.assertEqual(priority[3], 50)
        self.assertEqual(priority[4], SignalType.INTEGER)
    
    def test_parse_remove_line(self):
        """Test parsing a REMOVE line."""
        line = "2025-12-05 00:00:35.404 [REMOVE=MANUAL_SKID-120423595285_235952857_0579, SDENTP490038] [TransferState=TransferCompleted], [ResultCode=Complete]"
        entries = self.parser._parse_line_to_entries(line)
        
        self.assertGreater(len(entries), 0)
        self.assertEqual(entries[0][0], "SDENTP490038")
        self.assertEqual(entries[0][3], "REMOVE")
    
    def test_timestamp_parsing(self):
        """Test that timestamps are parsed correctly."""
        line = "2025-12-05 00:00:36.322 [UPDATE=336182, BBADFB0397] [CurrentLocation=test]"
        entries = self.parser._parse_line_to_entries(line)
        
        self.assertGreater(len(entries), 0)
        timestamp = entries[0][2]
        
        self.assertIsInstance(timestamp, datetime)
        self.assertEqual(timestamp.year, 2025)
        self.assertEqual(timestamp.month, 12)
        self.assertEqual(timestamp.day, 5)
        self.assertEqual(timestamp.hour, 0)
        self.assertEqual(timestamp.minute, 0)
        self.assertEqual(timestamp.second, 36)
        self.assertEqual(timestamp.microsecond, 322000)
    
    def test_type_inference_boolean(self):
        """Test boolean type inference."""
        self.assertEqual(self.parser._infer_type_for_key("IsBoost", "True"), SignalType.BOOLEAN)
        self.assertEqual(self.parser._infer_type_for_key("IsMultiJob", "False"), SignalType.BOOLEAN)
        self.assertEqual(self.parser._infer_type_for_key("SomeKey", "True"), SignalType.BOOLEAN)
        self.assertEqual(self.parser._infer_type_for_key("SomeKey", "False"), SignalType.BOOLEAN)
    
    def test_type_inference_integer(self):
        """Test integer type inference."""
        self.assertEqual(self.parser._infer_type_for_key("Priority", "50"), SignalType.INTEGER)
        self.assertEqual(self.parser._infer_type_for_key("AltCount", "0"), SignalType.INTEGER)
        self.assertEqual(self.parser._infer_type_for_key("SomeKey", "123"), SignalType.INTEGER)
    
    def test_type_inference_string(self):
        """Test string type inference."""
        self.assertEqual(self.parser._infer_type_for_key("TransferState", "Queued"), SignalType.STRING)
        self.assertEqual(self.parser._infer_type_for_key("CurrentLocation", "B1ACNV13301-120"), SignalType.STRING)
    
    def test_value_parsing(self):
        """Test value parsing based on type."""
        self.assertEqual(self.parser._parse_value_for_type("True", SignalType.BOOLEAN), True)
        self.assertEqual(self.parser._parse_value_for_type("False", SignalType.BOOLEAN), False)
        self.assertEqual(self.parser._parse_value_for_type("50", SignalType.INTEGER), 50)
        self.assertEqual(self.parser._parse_value_for_type("hello", SignalType.STRING), "hello")
    
    def test_empty_values_skipped(self):
        """Test that empty values and 'None' values are skipped."""
        line = "2025-12-05 00:00:36.322 [UPDATE=336182, BBADFB0397] [Empty=], [NoneVal=None], [Valid=test]"
        entries = self.parser._parse_line_to_entries(line)
        
        # Empty and None should be skipped
        entry_names = [e[1] for e in entries]
        self.assertNotIn("Empty", entry_names)
        self.assertNotIn("NoneVal", entry_names)
        self.assertIn("Valid", entry_names)
    
    def test_invalid_line_returns_empty(self):
        """Test that invalid lines return empty list."""
        invalid_lines = [
            "not a valid line",
            "2025-12-05 00:00:36.322 [INVALID=test, carrier]",  # Wrong action
            "",
            "   ",
        ]
        for line in invalid_lines:
            entries = self.parser._parse_line_to_entries(line)
            self.assertEqual(len(entries), 0, f"Expected empty for: {line}")
    
    def test_can_parse_mcs_format(self):
        """Test can_parse returns True for MCS format."""
        # Create a temp file with MCS content
        import tempfile
        import os
        
        content = """2025-12-05 00:00:36.322 [UPDATE=336182, BBADFB0397] [CurrentLocation=B1ACNV13301-120]
2025-12-05 00:00:36.322 [UPDATE=336182, BBADFB0397] [TransferState=Paused]
2025-12-05 00:00:36.469 [UPDATE=336182, BBADFB0397] [TransferState=Transferring]
"""
        
        fd, path = tempfile.mkstemp(suffix='.log')
        try:
            os.write(fd, content.encode('utf-8'))
            os.close(fd)
            
            result = self.parser.can_parse(path)
            self.assertTrue(result)
        finally:
            os.unlink(path)
    
    def test_can_parse_non_mcs_format(self):
        """Test can_parse returns False for non-MCS format."""
        import tempfile
        import os
        
        content = """2025-09-22 13:00:00.199 [Debug] [some/path] [INPUT2:I_MOVE_IN] (Boolean) : ON
2025-09-22 13:00:00.200 [Debug] [some/path] [INPUT2:I_MOVE_OUT] (Boolean) : OFF
"""
        
        fd, path = tempfile.mkstemp(suffix='.log')
        try:
            os.write(fd, content.encode('utf-8'))
            os.close(fd)
            
            result = self.parser.can_parse(path)
            self.assertFalse(result)
        finally:
            os.unlink(path)
    
    def test_parse_simplified_format(self):
        """Test parsing simplified format with single-parameter action header."""
        # Simplified format: [ACTION=CarrierID] instead of [ACTION=CommandID, CarrierID]
        line = "2025-12-09 00:00:01.443 [UPDATE=SDADTN490165] [CarrierLoc=B1ACNV13301-108]"
        entries = self.parser._parse_line_to_entries(line)
        
        # Should have 2 entries: _Action and CarrierLoc (mapped to CurrentLocation)
        self.assertEqual(len(entries), 2)
        
        # Check device_id
        self.assertEqual(entries[0][0], "SDADTN490165")
        
        # Check _Action entry
        self.assertEqual(entries[0][1], "_Action")
        self.assertEqual(entries[0][3], "UPDATE")
        
        # Check CurrentLocation entry (should be mapped from CarrierLoc)
        self.assertEqual(entries[1][1], "CurrentLocation")
        self.assertEqual(entries[1][3], "B1ACNV13301-108")
    
    def test_signal_name_mapping(self):
        """Test that CarrierLoc is mapped to CurrentLocation."""
        # Test various signal name mappings
        test_cases = [
            ("2025-12-09 00:00:01.443 [UPDATE=CARRIER123] [CarrierLoc=LOC-001]", "CurrentLocation"),
            ("2025-12-09 00:00:01.443 [UPDATE=CARRIER123] [CarrierLocation=LOC-001]", "CurrentLocation"),
            ("2025-12-09 00:00:01.443 [UPDATE=CARRIER123] [CurrentLocation=LOC-001]", "CurrentLocation"),
        ]
        
        for line, expected_signal in test_cases:
            entries = self.parser._parse_line_to_entries(line)
            signal_names = [e[1] for e in entries]
            self.assertIn(expected_signal, signal_names, 
                         f"Expected {expected_signal} in {signal_names} for line: {line}")
    
    def test_can_parse_simplified_format(self):
        """Test can_parse returns True for simplified MCS format."""
        import tempfile
        import os
        
        content = """2025-12-09 00:00:01.443 [UPDATE=SDADTN490165] [CarrierLoc=B1ACNV13301-108]
2025-12-09 00:00:01.443 [UPDATE=SDADTN490165] [CarrierTransferringState=WaitIn]
2025-12-09 00:00:01.960 [UPDATE=SDADTN490165] [CarrierTransferringState=Transferring]
2025-12-09 00:00:13.493 [REMOVE=SDADTN490140] [CarrierID=SDADTN490140], [CarrierLoc=B1ACNV13301-606]
"""
        
        fd, path = tempfile.mkstemp(suffix='.log')
        try:
            os.write(fd, content.encode('utf-8'))
            os.close(fd)
            
            result = self.parser.can_parse(path)
            self.assertTrue(result)
        finally:
            os.unlink(path)
    
    def test_simplified_no_command_id(self):
        """Test that simplified format doesn't create _CommandID entry."""
        line = "2025-12-09 00:00:01.443 [UPDATE=SDADTN490165] [CarrierLoc=B1ACNV13301-108]"
        entries = self.parser._parse_line_to_entries(line)
        
        signal_names = [e[1] for e in entries]
        # Should NOT have _CommandID in simplified format
        self.assertNotIn("_CommandID", signal_names)
        # Should have _Action
        self.assertIn("_Action", signal_names)
        # Should have CurrentLocation (mapped from CarrierLoc)
        self.assertIn("CurrentLocation", signal_names)


if __name__ == '__main__':
    unittest.main()
