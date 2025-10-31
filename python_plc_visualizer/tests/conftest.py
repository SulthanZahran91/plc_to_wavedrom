"""Pytest configuration for tests."""

import sys
from pathlib import Path

# Add the parent directory to the path so we can import plc_visualizer
parent_dir = Path(__file__).parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

