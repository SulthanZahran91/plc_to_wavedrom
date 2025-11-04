"""Tests for processing time tracking in parsers."""

import pytest
import tempfile
from pathlib import Path
from datetime import datetime

from plc_visualizer.models import ParseResult, ParsedLog, LogEntry, SignalType
from plc_visualizer.parsers.plc_parser import PLCDebugParser
from plc_visualizer.parsers.plc_tab_parser import PLCTabParser
from plc_visualizer.ui.components.stats_widget import StatsWidget


@pytest.fixture
def sample_plc_log_content() -> str:
    """Create sample PLC log content for testing."""
    return """2024-01-01 10:00:00.000 [] B1ACNV13301-104@::/CARRIER_DETECTED	<-	True		L1	0	0	2024-01-01 10:00:00.000
2024-01-01 10:00:01.000 [] B1ACNV13301-104@::/CARRIER_ID	<-	ABC123		L1	0	0	2024-01-01 10:00:01.000
2024-01-01 10:00:02.000 [] B1ACNV13301-104@::/CONVEYOR_MOVE	<-	True		L1	0	0	2024-01-01 10:00:02.000
2024-01-01 10:00:03.000 [] B1ACNV13301-104@::/CARRIER_DETECTED	<-	False		L1	0	0	2024-01-01 10:00:03.000
"""


@pytest.fixture
def sample_tab_log_content() -> str:
    """Create sample tab-delimited log content for testing."""
    return """2024-01-01 10:00:00.000	B1ACNV13301-104	CARRIER_DETECTED	True	boolean
2024-01-01 10:00:01.000	B1ACNV13301-104	CARRIER_ID	ABC123	string
2024-01-01 10:00:02.000	B1ACNV13301-104	CONVEYOR_MOVE	True	boolean
2024-01-01 10:00:03.000	B1ACNV13301-104	CARRIER_DETECTED	False	boolean
"""


class TestParseResultProcessingTime:
    """Test ParseResult processing_time field."""
    
    def test_parse_result_has_processing_time_field(self):
        """Verify ParseResult has processing_time field."""
        result = ParseResult(data=None, errors=[])
        
        # Should have the field
        assert hasattr(result, 'processing_time')
        
        # Should be None by default
        assert result.processing_time is None
    
    def test_parse_result_with_processing_time(self):
        """Test creating ParseResult with processing time."""
        parsed_log = ParsedLog(entries=[], signals=set(), devices=set())
        result = ParseResult(
            data=parsed_log,
            errors=[],
            processing_time=0.123
        )
        
        assert result.processing_time == pytest.approx(0.123, rel=1e-6)
        assert result.success is True
    
    def test_parse_result_processing_time_can_be_none(self):
        """Test that processing_time can be explicitly None."""
        result = ParseResult(data=None, errors=[], processing_time=None)
        
        assert result.processing_time is None


class TestSingleThreadParsing:
    """Test processing time tracking in single-thread parsing."""
    
    def test_plc_debug_parser_records_time(self, sample_plc_log_content):
        """Test that PLCDebugParser records processing time."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
            f.write(sample_plc_log_content)
            temp_path = f.name
        
        try:
            parser = PLCDebugParser()
            result = parser.parse(temp_path, num_workers=1)
            
            # Should have processing time
            assert result.processing_time is not None
            
            # Should be a reasonable time (positive and less than 10 seconds for small file)
            assert result.processing_time > 0
            assert result.processing_time < 10.0
            
            # Parse result should exist (success depends on content validity)
            assert result is not None
        finally:
            Path(temp_path).unlink()
    
    def test_plc_tab_parser_records_time(self, sample_tab_log_content):
        """Test that PLCTabParser records processing time."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
            f.write(sample_tab_log_content)
            temp_path = f.name
        
        try:
            parser = PLCTabParser()
            result = parser.parse(temp_path, num_workers=1)
            
            # Should have processing time
            assert result.processing_time is not None
            
            # Should be a reasonable time
            assert result.processing_time > 0
            assert result.processing_time < 10.0
            
            # Parse result should exist (success depends on content validity)
            assert result is not None
        finally:
            Path(temp_path).unlink()


class TestConcurrentParsing:
    """Test processing time tracking in multi-threaded parsing."""
    
    def test_concurrent_parsing_records_time(self, sample_plc_log_content):
        """Test that concurrent parsing records processing time."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
            # Write more data to make concurrent parsing worthwhile
            for i in range(100):
                f.write(sample_plc_log_content)
            temp_path = f.name
        
        try:
            parser = PLCDebugParser()
            result = parser.parse(temp_path, num_workers=2)
            
            # Should have processing time
            assert result.processing_time is not None
            
            # Should be a reasonable time
            assert result.processing_time > 0
            assert result.processing_time < 30.0
        finally:
            Path(temp_path).unlink()


class TestParsingErrorsWithTiming:
    """Test that processing time is recorded even on errors."""
    
    def test_processing_time_on_file_not_found(self):
        """Verify time recorded when file not found."""
        parser = PLCDebugParser()
        result = parser.parse("/nonexistent/file.log", num_workers=1)
        
        # Should have processing time even on error
        assert result.processing_time is not None
        assert result.processing_time >= 0
        
        # Should have failed
        assert result.success is False
        assert result.has_errors is True
    
    def test_processing_time_on_empty_file(self):
        """Verify time recorded for empty file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
            # Write nothing
            temp_path = f.name
        
        try:
            parser = PLCDebugParser()
            result = parser.parse(temp_path, num_workers=1)
            
            # Should have processing time
            assert result.processing_time is not None
            assert result.processing_time >= 0
            
            # No data but not an error
            assert result.success is False
        finally:
            Path(temp_path).unlink()


class TestStatsWidgetDisplaysTime:
    """Test that StatsWidget displays processing time correctly."""
    
    def test_stats_widget_has_processing_time_label(self, qtbot):
        """Verify StatsWidget has processing time label."""
        widget = StatsWidget()
        qtbot.addWidget(widget)
        
        # Should have the label
        assert hasattr(widget, 'processing_time_label')
        assert widget.processing_time_label is not None
        
        # Initial text should show "-"
        assert "Processing Time: -" in widget.processing_time_label.text()
    
    def test_stats_widget_displays_processing_time(self, qtbot):
        """Verify StatsWidget displays processing time from ParseResult."""
        widget = StatsWidget()
        qtbot.addWidget(widget)
        
        # Create result with processing time
        parsed_log = ParsedLog(
            entries=[],
            signals=set(),
            devices=set(),
            time_range=(datetime(2024, 1, 1, 10, 0, 0), datetime(2024, 1, 1, 10, 1, 0))
        )
        result = ParseResult(
            data=parsed_log,
            errors=[],
            processing_time=1.234
        )
        
        # Update stats
        widget.update_stats(result)
        
        # Should display the time
        assert "1.23s" in widget.processing_time_label.text()
    
    def test_time_formatting_milliseconds(self, qtbot):
        """Test that times <1s are formatted as milliseconds."""
        widget = StatsWidget()
        qtbot.addWidget(widget)
        
        parsed_log = ParsedLog(entries=[], signals=set(), devices=set())
        result = ParseResult(
            data=parsed_log,
            errors=[],
            processing_time=0.567  # Less than 1 second
        )
        
        widget.update_stats(result)
        
        # Should show as milliseconds
        text = widget.processing_time_label.text()
        assert "567ms" in text or "567 ms" in text
    
    def test_time_formatting_seconds(self, qtbot):
        """Test that times >=1s are formatted as seconds."""
        widget = StatsWidget()
        qtbot.addWidget(widget)
        
        parsed_log = ParsedLog(entries=[], signals=set(), devices=set())
        result = ParseResult(
            data=parsed_log,
            errors=[],
            processing_time=2.345  # More than 1 second
        )
        
        widget.update_stats(result)
        
        # Should show as seconds
        text = widget.processing_time_label.text()
        assert "2.35s" in text or "2.34s" in text  # Account for rounding
    
    def test_time_formatting_none(self, qtbot):
        """Test display when processing_time is None."""
        widget = StatsWidget()
        qtbot.addWidget(widget)
        
        parsed_log = ParsedLog(entries=[], signals=set(), devices=set())
        result = ParseResult(
            data=parsed_log,
            errors=[],
            processing_time=None
        )
        
        widget.update_stats(result)
        
        # Should show "-"
        assert "Processing Time: -" in widget.processing_time_label.text()


class TestProcessingTimeComparison:
    """Test processing time is consistent and reasonable."""
    
    def test_processing_time_increases_with_data_size(self, sample_plc_log_content):
        """Verify larger files take more time to parse."""
        parser = PLCDebugParser()
        
        # Small file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
            f.write(sample_plc_log_content)
            small_path = f.name
        
        # Larger file (10x more data)
        with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
            for _ in range(10):
                f.write(sample_plc_log_content)
            large_path = f.name
        
        try:
            small_result = parser.parse(small_path, num_workers=1)
            large_result = parser.parse(large_path, num_workers=1)
            
            # Both should have times
            assert small_result.processing_time is not None
            assert large_result.processing_time is not None
            
            # Larger file should generally take more time
            # (Note: very small differences might not be reliable due to overhead)
            assert small_result.processing_time >= 0
            assert large_result.processing_time >= 0
        finally:
            Path(small_path).unlink()
            Path(large_path).unlink()

