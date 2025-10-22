#!/usr/bin/env python3
"""Quick test for chunked loading without full parse.

This script demonstrates chunked loading by extracting just the time range
from the first and last lines, avoiding the need to parse the entire file.
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
import re

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from plc_visualizer.parsers import parser_registry
from plc_visualizer.utils import create_chunked_log


def extract_time_range_fast(log_file: str) -> tuple[datetime, datetime] | None:
    """Extract time range by reading first and last lines.

    Args:
        log_file: Path to log file

    Returns:
        Tuple of (start_time, end_time) or None if extraction fails
    """
    # Try to extract timestamps from first and last lines
    try:
        with open(log_file, 'r') as f:
            # Get first non-empty line
            first_line = None
            for line in f:
                if line.strip():
                    first_line = line
                    break

            if not first_line:
                return None

            # Get last non-empty line
            f.seek(0, 2)  # Go to end
            file_size = f.tell()

            # Read last few KB to find last line
            chunk_size = min(8192, file_size)
            f.seek(max(0, file_size - chunk_size))
            last_chunk = f.read()

            last_line = None
            for line in reversed(last_chunk.splitlines()):
                if line.strip():
                    last_line = line
                    break

            if not last_line:
                return None

        # Parse timestamps from lines
        # Assuming format: "YYYY-MM-DD HH:MM:SS.microseconds [] ..."
        timestamp_pattern = r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d+)'

        first_match = re.search(timestamp_pattern, first_line)
        last_match = re.search(timestamp_pattern, last_line)

        if not first_match or not last_match:
            return None

        start_time = datetime.strptime(first_match.group(1), '%Y-%m-%d %H:%M:%S.%f')
        end_time = datetime.strptime(last_match.group(1), '%Y-%m-%d %H:%M:%S.%f')

        return (start_time, end_time)

    except Exception as e:
        print(f"Error extracting time range: {e}")
        return None


def test_chunked_loading_quick(log_file: str):
    """Quick test of chunked loading.

    Args:
        log_file: Path to log file to test
    """
    print("=" * 60)
    print("Quick Chunked Loading Test")
    print("=" * 60)
    print(f"File: {log_file}")
    print()

    # Step 1: Extract time range from first/last lines
    print("Step 1: Extracting time range (fast)...")
    time_range = extract_time_range_fast(log_file)
    if not time_range:
        print("❌ Could not extract time range")
        return

    start_time, end_time = time_range
    print(f"✅ Time range: {start_time} to {end_time}")
    duration = (end_time - start_time).total_seconds()
    print(f"   Duration: {duration:.1f} seconds ({duration/60:.1f} minutes)")
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

    # Step 3: Load first chunk
    print("Step 3: Loading first 5-minute window...")
    chunk_start = start_time
    chunk_end = chunk_start + timedelta(seconds=300)
    entries = chunk_manager.get_entries_in_range(chunk_start, chunk_end)
    print(f"✅ Loaded {len(entries)} entries from first chunk")
    print(f"   Chunks in memory: {chunk_manager.chunks_in_memory}")
    if entries:
        print(f"   First entry: {entries[0].timestamp}")
        print(f"   Last entry: {entries[-1].timestamp}")
    print()

    # Step 4: Load a middle chunk
    print("Step 4: Loading a middle window...")
    middle_time = start_time + timedelta(seconds=duration / 2)
    chunk_start = middle_time
    chunk_end = chunk_start + timedelta(seconds=300)
    entries = chunk_manager.get_entries_in_range(chunk_start, chunk_end)
    print(f"✅ Loaded {len(entries)} entries from middle chunk")
    print(f"   Chunks in memory: {chunk_manager.chunks_in_memory}")
    print()

    # Step 5: Load last chunk
    print("Step 5: Loading last 5-minute window...")
    chunk_start = end_time - timedelta(seconds=300)
    chunk_end = end_time
    entries = chunk_manager.get_entries_in_range(chunk_start, chunk_end)
    print(f"✅ Loaded {len(entries)} entries from last chunk")
    print(f"   Chunks in memory: {chunk_manager.chunks_in_memory}")
    print()

    # Step 6: Simulate panning
    print("Step 6: Simulating panning forward (5 steps)...")
    pan_start = start_time
    for i in range(5):
        chunk_start = pan_start + timedelta(seconds=i * 150)  # 2.5 min steps
        chunk_end = chunk_start + timedelta(seconds=300)

        if chunk_end > end_time:
            break

        entries = chunk_manager.get_entries_in_range(chunk_start, chunk_end, with_prefetch=True)
        print(f"   Pan {i+1}: Loaded {len(entries)} entries")

    print(f"   Final chunks in memory: {chunk_manager.chunks_in_memory}")
    print()

    # Step 7: Signal discovery
    print("Step 7: Signal discovery...")
    print(f"✅ Discovered {len(chunked_log.signals)} unique signals")
    if chunked_log.signals:
        sample_signals = sorted(chunked_log.signals)[:3]
        for signal in sample_signals:
            print(f"   - {signal}")
    print()

    print("=" * 60)
    print("✅ Chunked loading system working correctly!")
    print(f"   Only {chunk_manager.chunks_in_memory}/{chunked_log.max_chunks_in_memory} chunks in memory")
    print("=" * 60)


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python test_chunked_loading_quick.py <log_file>")
        print()
        print("Example:")
        print("  python scripts/test_chunked_loading_quick.py generated_logs/benchmark/plc_tab_parser_01.log")
        sys.exit(1)

    log_file = sys.argv[1]

    if not Path(log_file).exists():
        print(f"❌ File not found: {log_file}")
        sys.exit(1)

    test_chunked_loading_quick(log_file)


if __name__ == "__main__":
    main()
