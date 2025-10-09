"""Tests for the default PLC log parser."""

import tempfile
from pathlib import Path

import pytest

from plc_visualizer.models import SignalType
from plc_visualizer.parsers.default_parser import DefaultParser


@pytest.fixture
def parser():
    """Create a parser instance."""
    return DefaultParser()


@pytest.fixture
def sample_log_file():
    """Create a temporary log file with sample data."""
    content = """DEVICE_A MOTOR_START 10:30:45 true boolean
DEVICE_A SENSOR_A 10:30:46 ready string
DEVICE_A COUNTER_1 10:30:47 100 integer
DEVICE_A MOTOR_START 10:30:50 false boolean
DEVICE_A SENSOR_A 10:30:51 error string
INVALID LINE HERE
DEVICE_A COUNTER_1 10:30:52 150 integer"""

    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
        f.write(content)
        temp_path = f.name

    yield temp_path

    # Cleanup
    Path(temp_path).unlink()


class TestParseValidEntries:
    """Test parsing of valid log entries."""

    def test_parse_boolean_values(self, parser):
        """Test parsing boolean signals."""
        content = """DEVICE_A MOTOR_START 10:30:45 true boolean
DEVICE_A MOTOR_STOP 10:30:46 false boolean
DEVICE_B FLAG_A 10:30:47 1 boolean
DEVICE_B FLAG_B 10:30:48 0 boolean"""

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
            f.write(content)
            temp_path = f.name

        try:
            result = parser.parse(temp_path)

            assert result.success
            assert result.data.entry_count == 4
            assert result.data.entries[0].value is True
            assert result.data.entries[1].value is False
            assert result.data.entries[2].value is True
            assert result.data.entries[3].value is False
            assert result.data.entries[0].device_id == "DEVICE_A"
            assert result.data.entries[2].device_id == "DEVICE_B"
            assert len(result.errors) == 0
        finally:
            Path(temp_path).unlink()

    def test_parse_string_values(self, parser):
        """Test parsing string signals."""
        content = """DEVICE_A SENSOR_A 10:30:45 ready string
DEVICE_B SENSOR_B 10:30:46 error string"""

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
            f.write(content)
            temp_path = f.name

        try:
            result = parser.parse(temp_path)

            assert result.success
            assert result.data.entry_count == 2
            assert result.data.entries[0].value == "ready"
            assert result.data.entries[1].value == "error"
            assert result.data.entries[0].signal_type == SignalType.STRING
            assert result.data.entries[0].device_id == "DEVICE_A"
            assert len(result.errors) == 0
        finally:
            Path(temp_path).unlink()

    def test_parse_integer_values(self, parser):
        """Test parsing integer signals."""
        content = """DEVICE_A COUNTER_1 10:30:45 100 integer
DEVICE_B COUNTER_2 10:30:46 -50 integer"""

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
            f.write(content)
            temp_path = f.name

        try:
            result = parser.parse(temp_path)

            assert result.success
            assert result.data.entry_count == 2
            assert result.data.entries[0].value == 100
            assert result.data.entries[1].value == -50
            assert result.data.entries[0].signal_type == SignalType.INTEGER
            assert result.data.entries[1].device_id == "DEVICE_B"
            assert len(result.errors) == 0
        finally:
            Path(temp_path).unlink()

    def test_parse_timestamps(self, parser):
        """Test timestamp parsing."""
        content = """DEVICE_A SIGNAL_A 10:30:45 test string
DEVICE_B SIGNAL_B 1:05:03 test string"""

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
            f.write(content)
            temp_path = f.name

        try:
            result = parser.parse(temp_path)

            assert result.success
            assert result.data.entry_count == 2

            entry1 = result.data.entries[0]
            assert entry1.timestamp.hour == 10
            assert entry1.timestamp.minute == 30
            assert entry1.timestamp.second == 45

            entry2 = result.data.entries[1]
            assert entry2.timestamp.hour == 1
            assert entry2.timestamp.minute == 5
            assert entry2.timestamp.second == 3
        finally:
            Path(temp_path).unlink()

    def test_collect_unique_signals(self, parser):
        """Test collection of unique signal names."""
        content = """DEVICE_A MOTOR_START 10:30:45 true boolean
DEVICE_A SENSOR_A 10:30:46 ready string
DEVICE_A MOTOR_START 10:30:47 false boolean"""

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
            f.write(content)
            temp_path = f.name

        try:
            result = parser.parse(temp_path)

            assert result.success
            assert result.data.signal_count == 2
            assert "DEVICE_A::MOTOR_START" in result.data.signals
            assert "DEVICE_A::SENSOR_A" in result.data.signals
        finally:
            Path(temp_path).unlink()

    def test_calculate_time_range(self, parser):
        """Test time range calculation."""
        content = """DEVICE_A SIGNAL_A 10:30:45 test string
DEVICE_B SIGNAL_B 10:32:15 test string
DEVICE_C SIGNAL_C 10:31:00 test string"""

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
            f.write(content)
            temp_path = f.name

        try:
            result = parser.parse(temp_path)

            assert result.success
            assert result.data.time_range is not None

            start, end = result.data.time_range
            assert start.hour == 10
            assert start.minute == 30
            assert start.second == 45
            assert end.minute == 32
            assert end.second == 15
        finally:
            Path(temp_path).unlink()


class TestHandleInvalidEntries:
    """Test handling of invalid log entries."""

    def test_malformed_lines(self, parser, sample_log_file):
        """Test that malformed lines are collected as errors."""
        result = parser.parse(sample_log_file)

        assert result.success
        assert result.data.entry_count == 6  # 6 valid entries
        assert result.error_count == 1  # 1 invalid line
        assert result.errors[0].line == 6
        assert "INVALID LINE HERE" in result.errors[0].content

    def test_invalid_time_format(self, parser):
        """Test error on invalid time format."""
        content = "DEVICE_A SIGNAL_A 25:99:99 test string"

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
            f.write(content)
            temp_path = f.name

        try:
            result = parser.parse(temp_path)

            assert not result.success or result.has_errors
            assert result.error_count == 1
            assert "time format" in result.errors[0].reason.lower()
        finally:
            Path(temp_path).unlink()

    def test_invalid_type(self, parser):
        """Test error on invalid signal type."""
        content = "DEVICE_A SIGNAL_A 10:30:45 test float"

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
            f.write(content)
            temp_path = f.name

        try:
            result = parser.parse(temp_path)

            assert result.error_count == 1
            assert "Invalid type" in result.errors[0].reason
        finally:
            Path(temp_path).unlink()

    def test_invalid_boolean_value(self, parser):
        """Test error on invalid boolean value."""
        content = "DEVICE_A SIGNAL_A 10:30:45 maybe boolean"

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
            f.write(content)
            temp_path = f.name

        try:
            result = parser.parse(temp_path)

            assert result.error_count == 1
            assert "Invalid boolean value" in result.errors[0].reason
        finally:
            Path(temp_path).unlink()

    def test_invalid_integer_value(self, parser):
        """Test error on invalid integer value."""
        content = "DEVICE_A COUNTER 10:30:45 abc integer"

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
            f.write(content)
            temp_path = f.name

        try:
            result = parser.parse(temp_path)

            assert result.error_count == 1
            assert "Invalid integer value" in result.errors[0].reason
        finally:
            Path(temp_path).unlink()

    def test_handle_empty_lines(self, parser):
        """Test that empty lines are skipped."""
        content = """DEVICE_A SIGNAL_A 10:30:45 test string

DEVICE_B SIGNAL_B 10:30:46 test string"""

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
            f.write(content)
            temp_path = f.name

        try:
            result = parser.parse(temp_path)

            assert result.success
            assert result.data.entry_count == 2
            assert result.error_count == 0
        finally:
            Path(temp_path).unlink()

    def test_handle_empty_file(self, parser):
        """Test handling of empty file."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
            temp_path = f.name

        try:
            result = parser.parse(temp_path)

            assert not result.success
            assert result.data is None
            assert result.error_count == 0
        finally:
            Path(temp_path).unlink()


class TestCanParse:
    """Test format detection."""

    def test_detect_valid_format(self, parser):
        """Test detection of valid format."""
        content = """DEVICE_A MOTOR_START 10:30:45 true boolean
DEVICE_A SENSOR_A 10:30:46 ready string
DEVICE_B COUNTER_1 10:30:47 100 integer"""

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
            f.write(content)
            temp_path = f.name

        try:
            assert parser.can_parse(temp_path) is True
        finally:
            Path(temp_path).unlink()

    def test_reject_invalid_format(self, parser):
        """Test rejection of invalid format."""
        content = """This is not a valid log file
Just some random text
Nothing matches the expected format"""

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
            f.write(content)
            temp_path = f.name

        try:
            assert parser.can_parse(temp_path) is False
        finally:
            Path(temp_path).unlink()

    def test_reject_empty_content(self, parser):
        """Test rejection of empty file."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
            temp_path = f.name

        try:
            assert parser.can_parse(temp_path) is False
        finally:
            Path(temp_path).unlink()


class TestStreamingParse:
    """Test streaming parser functionality."""

    def test_streaming_parse(self, parser, sample_log_file):
        """Test streaming parse yields entries."""
        entries = list(parser.parse_streaming(sample_log_file))

        assert len(entries) == 6  # 6 valid entries (invalid line skipped)
        assert all(hasattr(entry, 'signal_name') for entry in entries)
        assert all(hasattr(entry, 'timestamp') for entry in entries)
        assert all(hasattr(entry, 'device_id') for entry in entries)
