<!-- 75fa4886-5906-44ac-a637-cc8d414e811a ea0d644e-6e04-4656-a9db-ec3af6a1d965 -->
# Comprehensive Testing Plan for Miscellaneous Fixes

## Overview

Create unit tests and integration tests following existing pytest-qt patterns to validate the 4 miscellaneous fixes implemented.

## Test Structure

### 1. Unit Tests for Signal Interval Tab View

**File:** `python_plc_visualizer/tests/test_interval_view.py`

Test the SignalIntervalDialog conversion from window to embeddable view:

- Test view_type property returns "signal_interval"
- Test widget initialization without modal attributes
- Test that view can be added to SplitPaneManager
- Test interval computation with sample signal data
- Test mode switching (change-to-change, pulse width, custom tokens)
- Test binning controls update the plot widget correctly
- Test percentile capping works as expected

**Sample test cases:**

- `test_interval_view_type()` - verify VIEW_TYPE constant
- `test_interval_view_initialization()` - check it's a QWidget not QDialog
- `test_add_to_split_pane()` - verify it integrates with tab system
- `test_change_to_change_mode()` - verify interval calculations
- `test_pulse_width_mode()` - test true pulse width intervals
- `test_custom_token_mode()` - test custom pattern matching
- `test_bin_duration_updates_plot()` - verify plot responds to bin changes

### 2. Unit Tests for Processing Time Tracking

**File:** `python_plc_visualizer/tests/test_parse_timing.py`

Test processing time measurement in parsers:

- Test ParseResult has processing_time field
- Test that processing_time is populated after parsing
- Test processing_time is in reasonable range
- Test processing_time is None when not set
- Test concurrent parsing tracks time correctly
- Test error cases still record processing time
- Test StatsWidget displays processing time correctly

**Sample test cases:**

- `test_parse_result_has_processing_time_field()` - verify field exists
- `test_single_thread_parsing_records_time()` - check timing in single-thread mode
- `test_concurrent_parsing_records_time()` - check timing in multi-thread mode
- `test_processing_time_on_error()` - verify time recorded even on failures
- `test_stats_widget_displays_time()` - verify UI shows the time
- `test_time_formatting_ms_and_seconds()` - test <1s shows as ms, >=1s as seconds

### 3. Integration Tests for Collapsible Log Table Filter

**File:** `python_plc_visualizer/tests/test_log_table_splitter.py`

Test the horizontal splitter in log table view:

- Test LogTableView has splitter with filter and table
- Test splitter is collapsible
- Test initial splitter sizes are [320, 900]
- Test filter panel can collapse
- Test both panels resize correctly
- Test splitter handle styling

**Sample test cases:**

- `test_log_table_has_splitter()` - verify splitter exists
- `test_splitter_orientation()` - check it's horizontal
- `test_initial_splitter_sizes()` - verify [320, 900]
- `test_filter_can_collapse()` - programmatically collapse and verify
- `test_splitter_children_correct()` - verify filter on left, table on right

### 4. Unit Tests for Map Viewer YAML Config

**File:** `python_plc_visualizer/tests/test_map_viewer_config.py`

Test YAML configuration loading for map viewer:

- Test load_xml_parsing_config returns correct structure
- Test config loads from YAML file successfully
- Test fallback to defaults when YAML missing
- Test fallback to defaults when YAML incomplete
- Test hex color conversion to QColor
- Test config values match YAML content
- Test backward compatibility with old hardcoded values

**Sample test cases:**

- `test_load_xml_config_structure()` - verify return dict has all keys
- `test_load_from_yaml_file()` - test actual YAML file loads
- `test_fallback_on_missing_yaml()` - test defaults when file not found
- `test_fallback_on_incomplete_yaml()` - test defaults for missing keys
- `test_hex_to_qcolor_conversion()` - verify color conversion
- `test_attributes_to_extract_loaded()` - check specific config value
- `test_forecolor_mapping_loaded()` - check color mapping

## Integration Tests

### 5. End-to-End Integration Test

**File:** `python_plc_visualizer/tests/test_misc_fixes_integration.py`

Test all 4 fixes working together in realistic scenarios:

- Load sample log file
- Open signal interval view as tab (not window)
- Verify processing time appears in stats
- Verify log table filter is collapsible
- Verify map viewer loads config from YAML (if map viewer available)

**Sample test cases:**

- `test_interval_view_opens_as_tab()` - end-to-end test opening interval view
- `test_processing_time_shown_after_parse()` - verify stats display after real parse
- `test_log_table_filter_collapsible_ui()` - interactive test of splitter
- `test_all_fixes_work_together()` - comprehensive integration test

## UI/Manual Testing Checklist

**File:** `python_plc_visualizer/TESTING_CHECKLIST_MISC_FIXES.md`

Create manual testing checklist covering:

### Signal Interval Tabs

- [ ] Open signal interval plot - verify it opens as tab not window
- [ ] Open multiple interval plots - verify they all appear as tabs
- [ ] Close interval tab - verify it closes cleanly
- [ ] Switch between interval tabs and other view tabs
- [ ] Verify interval plot behavior identical to before

### Processing Time

- [ ] Parse small log file - verify processing time shown
- [ ] Parse large log file - verify processing time shown
- [ ] Parse with errors - verify processing time still shown
- [ ] Verify time format: ms for <1s, seconds for >=1s

### Collapsible Filter

- [ ] Open Log Table view
- [ ] Drag splitter left to collapse filter panel
- [ ] Drag splitter right to restore filter panel
- [ ] Verify table remains functional when filter collapsed
- [ ] Compare to Timing Diagram splitter behavior

### YAML Config

- [ ] Verify map viewer still works
- [ ] Modify mappings_and_rules.yaml - verify changes reflected
- [ ] Delete xml_parsing section - verify fallback to defaults
- [ ] Invalid YAML - verify error handling and fallback

## Test Data Fixtures

Create reusable fixtures in `conftest.py`:

- `sample_signal_data()` - signal data with transitions for interval testing
- `parsed_log_with_time()` - ParsedLog with known processing time
- `sample_yaml_config()` - temporary YAML config for testing

## Coverage Goals

Target test coverage:

- Unit tests: 80%+ coverage of new/modified code
- Integration tests: Cover main user workflows
- Manual tests: All UI interactions validated

## Files to Create

1. `python_plc_visualizer/tests/test_interval_view.py` (~200 lines)
2. `python_plc_visualizer/tests/test_parse_timing.py` (~150 lines)
3. `python_plc_visualizer/tests/test_log_table_splitter.py` (~100 lines)
4. `python_plc_visualizer/tests/test_map_viewer_config.py` (~150 lines)
5. `python_plc_visualizer/tests/test_misc_fixes_integration.py` (~200 lines)
6. `python_plc_visualizer/tests/conftest.py` (extend existing, ~50 lines)
7. `python_plc_visualizer/TESTING_CHECKLIST_MISC_FIXES.md` (documentation)

### To-dos

- [ ] Create test_interval_view.py with unit tests for signal interval tab view
- [ ] Create test_parse_timing.py with unit tests for processing time tracking
- [ ] Create test_log_table_splitter.py with tests for collapsible filter
- [ ] Create test_map_viewer_config.py with tests for YAML config loading
- [ ] Create test_misc_fixes_integration.py with end-to-end integration tests
- [ ] Extend conftest.py with test fixtures for new tests
- [ ] Create TESTING_CHECKLIST_MISC_FIXES.md with manual testing guide