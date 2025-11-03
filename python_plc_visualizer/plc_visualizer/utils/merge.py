"""Utilities for merging parsed log data from multiple sources."""

from __future__ import annotations

from dataclasses import replace
from typing import Iterable

from plc_visualizer.models import ParseError, ParseResult, ParsedLog


def merge_parsed_logs(parsed_logs: Iterable[ParsedLog]) -> ParsedLog | None:
    """Merge multiple ParsedLog objects into a single combined log.

    Args:
        parsed_logs: Iterable of ParsedLog instances to merge

    Returns:
        Combined ParsedLog covering all entries, or None if nothing to merge
    """
    logs = [log for log in parsed_logs if log is not None]
    if not logs:
        return None

    combined_entries: list = []
    combined_signals: set[str] = set()
    combined_devices: set[str] = set()
    start_times = []
    end_times = []

    for log in logs:
        combined_entries.extend(log.entries)
        combined_signals.update(log.signals)
        combined_devices.update(log.devices)

        if log.time_range:
            start, end = log.time_range
            start_times.append(start)
            end_times.append(end)

    # Ensure entries are sorted chronologically across files
    combined_entries.sort(key=lambda entry: entry.timestamp)

    combined_range = None
    if start_times and end_times:
        combined_range = (min(start_times), max(end_times))

    return ParsedLog(
        entries=combined_entries,
        signals=combined_signals,
        devices=combined_devices,
        time_range=combined_range,
    )


def merge_parse_results(results_by_file: dict[str, ParseResult]) -> ParseResult:
    """Merge ParseResult objects keyed by file path.

    Ensures errors retain their originating file path and combines all
    successfully parsed logs into a single ParsedLog.

    Note: processing_time is not set here - it should be set by the caller
    to reflect the total wall-clock time for the entire operation.

    Args:
        results_by_file: Mapping of absolute file path to ParseResult

    Returns:
        ParseResult representing merged data and aggregated errors
    """
    merged_logs = []
    aggregated_errors: list[ParseError] = []

    for file_path, result in results_by_file.items():
        if result.data:
            merged_logs.append(result.data)

        for error in result.errors:
            # Preserve existing error details but ensure file_path is set
            if error.file_path == file_path:
                aggregated_errors.append(error)
            else:
                aggregated_errors.append(
                    replace(error, file_path=file_path)
                )

        # Capture total-failure cases (no data but also no explicit errors)
        if not result.success and not result.errors:
            aggregated_errors.append(ParseError(
                line=0,
                content="",
                reason="Parsing failed with no additional details",
                file_path=file_path,
            ))

    merged_log = merge_parsed_logs(merged_logs)

    return ParseResult(
        data=merged_log,
        errors=aggregated_errors,
    )
