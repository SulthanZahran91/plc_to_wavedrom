"""Pytest fixtures for script-level tests."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def log_file() -> str:
    """Provide a representative sample log for chunked loading tests."""
    sample = Path(__file__).parent.parent / "sample_logs" / "plc_tab_parser.log"
    if not sample.exists():
        pytest.skip("sample log file not available for chunked loading tests")
    return str(sample)
