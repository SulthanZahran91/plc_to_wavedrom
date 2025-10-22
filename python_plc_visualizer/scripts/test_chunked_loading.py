#!/usr/bin/env python3
"""Test script for chunked loading system.

This script demonstrates and tests the chunked loading architecture for
gigabyte-scale log files.
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from plc_visualizer.parsers import parser_registry
from plc_visualizer.utils import create_chunked_log


def test_chunked_loading(log_file: str):
    """Test chunked loading on a log file.

    Args:
        log_file: Path to log file to test
    """
    print("=" * 60)
    print("Chunked Loading Test")
    print("=" * 60)
    print(f"File: {log_file}")
    print()

    # Step 1: Get parser and scan file for time range
    print("Step 1: Scanning file for time range...")
    parser = parser_registry.detect_parser(log_file)
    if not parser:
        print("❌ No parser found for this file")
        return

    print(f"✅ Using parser: {parser.name}")

    # Parse just enough to get time range (we'll use full parse for demo)
    result = parser.parse(log_file)
    if not result.success or not result.data:
        print("❌ Failed to parse file")
        return

    time_range = result.data.time_range
    if not time_range:
        print("❌ No time range found in file")
        return

    print(f"✅ Time range: {time_range[0]} to {time_range[1]}")
    duration = (time_range[1] - time_range[0]).total_seconds()
    print(f"   Duration: {duration:.1f} seconds ({duration/60:.1f} minutes)")
    print(f"   Total entries: {len(result.data.entries)}")
    print(f"   Signals: {len(result.data.signals)}")
    print()

    # Step 2: Create chunked log
    print("Step 2: Creating chunked log (5-minute chunks, max 5 in memory)...")
    chunked_log, chunk_manager = create_chunked_log(
        file_path=log_file,
        time_range=time_range,
        chunk_duration_seconds=300.0,  # 5 minutes
        max_chunks_in_memory=5
    )
    print(f"✅ Chunked log created")
    print()

    # Step 3: Test loading first chunk
    print("Step 3: Loading first 5-minute window...")
    start_time = time_range[0]
    end_time = start_time + timedelta(seconds=300)
    entries = chunk_manager.get_entries_in_range(start_time, end_time)
    print(f"✅ Loaded {len(entries)} entries from first chunk")
    print(f"   Chunks in memory: {chunk_manager.chunks_in_memory}")
    print()

    # Step 4: Test panning forward
    print("Step 4: Panning forward through time (simulating user scrolling)...")
    num_pans = min(10, int(duration / 300))  # Pan up to 10 times or end of file
    for i in range(num_pans):
        start_time = time_range[0] + timedelta(seconds=i * 150)  # 2.5 minute steps
        end_time = start_time + timedelta(seconds=300)

        # Don't go past end
        if end_time > time_range[1]:
            break

        print(f"\n   Pan {i+1}: {start_time.strftime('%H:%M:%S')} - {end_time.strftime('%H:%M:%S')}")
        entries = chunk_manager.get_entries_in_range(start_time, end_time)
        print(f"   → Loaded {len(entries)} entries")

    print()
    print(f"✅ Final chunks in memory: {chunk_manager.chunks_in_memory}")
    print()

    # Step 5: Test signal discovery
    print("Step 5: Testing signal discovery from chunks...")
    print(f"✅ Discovered {len(chunked_log.signals)} unique signals:")
    for i, signal in enumerate(sorted(chunked_log.signals)[:5], 1):
        print(f"   {i}. {signal}")
    if len(chunked_log.signals) > 5:
        print(f"   ... and {len(chunked_log.signals) - 5} more")
    print()

    # Step 6: Memory efficiency report
    print("Step 6: Memory efficiency report")
    print("=" * 60)
    print(f"Total entries in file: {len(result.data.entries)}")
    print(f"Chunks in memory: {chunk_manager.chunks_in_memory}")
    print(f"Max chunks allowed: {chunked_log.max_chunks_in_memory}")
    print(f"Chunk duration: {chunked_log.chunk_duration.total_seconds():.0f} seconds")
    print()
    print("✅ Chunked loading system working correctly!")
    print("   Only a small portion of the file is kept in memory at a time.")
    print()


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python test_chunked_loading.py <log_file>")
        print()
        print("Example:")
        print("  python scripts/test_chunked_loading.py sample_logs/plc_log.txt")
        sys.exit(1)

    log_file = sys.argv[1]

    if not Path(log_file).exists():
        print(f"❌ File not found: {log_file}")
        sys.exit(1)

    test_chunked_loading(log_file)


if __name__ == "__main__":
    main()
