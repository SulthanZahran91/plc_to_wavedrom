"""Central session manager for parsed log data and shared window state."""

from __future__ import annotations

import atexit
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from PySide6.QtCore import QObject, QThread, Signal

from plc_visualizer.models import ParseResult, ParsedLog, TimeBookmark
from plc_visualizer.parsers import parser_registry
from plc_visualizer.utils import (
    SignalData,
    ViewportState,
    merge_parse_results,
    process_signals_for_waveform,
)


class ParserThread(QThread):
    """Background thread responsible for parsing one or more log files."""

    finished = Signal(object, object, object)  # aggregated_result, per_file_results, signal_data_list
    progress = Signal(int, int, str)  # current_index, total_files, file_path
    error = Signal(str)
    _executor: ProcessPoolExecutor | None = None
    _mp_context: mp.context.BaseContext | None = None

    def __init__(self, file_paths: List[str], parent=None):
        super().__init__(parent)
        self.file_paths = file_paths

    def run(self):
        """Parse files sequentially within the worker thread."""
        import time
        from dataclasses import replace
        
        try:
            start_time = time.perf_counter()
            
            per_file_results: Dict[str, ParseResult] = {}
            total_files = len(self.file_paths)

            for index, file_path in enumerate(self.file_paths, start=1):
                per_file_results[file_path] = parser_registry.parse(file_path)
                self.progress.emit(index, total_files, file_path)

            aggregated_result = merge_parse_results(per_file_results)
            signal_data_list: list[SignalData] = []
            if aggregated_result.success and aggregated_result.data:
                signal_data_list = self._compute_signal_data(aggregated_result.data)

            # Calculate total elapsed time
            elapsed_time = time.perf_counter() - start_time
            
            # Update the aggregated result with total processing time
            aggregated_result = replace(aggregated_result, processing_time=elapsed_time)

            self.finished.emit(aggregated_result, per_file_results, signal_data_list)
        except Exception as exc:  # pragma: no cover - logged upstream
            self.error.emit(f"Failed to parse files: {exc}")

    @classmethod
    def _compute_signal_data(cls, parsed_log: ParsedLog):
        """Compute waveform data, optionally offloading to a subprocess."""
        try:
            entry_count = getattr(parsed_log, "entry_count", 0)
            if entry_count and entry_count >= 10000:
                if cls._executor is None:
                    if cls._mp_context is None:
                        try:
                            cls._mp_context = mp.get_context("spawn")
                        except ValueError:
                            cls._mp_context = mp.get_context()
                    try:
                        cls._executor = ProcessPoolExecutor(
                            max_workers=1,
                            mp_context=cls._mp_context,
                        )
                    except TypeError:
                        cls._executor = ProcessPoolExecutor(max_workers=1)
                future = cls._executor.submit(process_signals_for_waveform, parsed_log)
                return future.result()
            return process_signals_for_waveform(parsed_log)
        except Exception:  # pragma: no cover - fallback path
            return process_signals_for_waveform(parsed_log)

    @classmethod
    def shutdown_executor(cls):
        """Dispose of the shared process pool."""
        if cls._executor is not None:
            cls._executor.shutdown(wait=False)
            cls._executor = None


atexit.register(ParserThread.shutdown_executor)


class SessionManager(QObject):
    """Coordinates parsing, caching, and distribution of parsed log data."""

    session_cleared = Signal()
    session_ready = Signal(object, object, object)  # aggregated_result, per_file_results, signal_data_list
    parse_started = Signal(list)  # file paths
    parse_progress = Signal(int, int, str)
    parse_failed = Signal(str)
    
    # Bookmark signals
    bookmarks_changed = Signal()  # Emitted when bookmark list changes
    bookmark_jump_requested = Signal(datetime)  # Emitted when jumping to a bookmark
    
    # Time sync signals
    sync_requested = Signal(datetime)  # Emitted when sync all views is requested

    def __init__(self, parent=None):
        super().__init__(parent)
        self._parser_thread: Optional[ParserThread] = None
        self._current_files: list[str] = []
        self._aggregated_result: Optional[ParseResult] = None
        self._parsed_log: Optional[ParsedLog] = None
        self._signal_data_list: list[SignalData] = []
        self._signal_data_map: dict[str, SignalData] = {}
        self._file_results: Dict[str, ParseResult] = {}
        
        # Shared viewport state for time synchronization
        self._viewport_state = ViewportState(self)
        
        # Bookmark management
        self._bookmarks: list[TimeBookmark] = []
        self._current_bookmark_index: int = -1

    # ------------------------------------------------------------------ Properties
    @property
    def parsed_log(self) -> Optional[ParsedLog]:
        return self._parsed_log

    @property
    def signal_data_list(self) -> list[SignalData]:
        return list(self._signal_data_list)

    @property
    def signal_data_map(self) -> dict[str, SignalData]:
        return dict(self._signal_data_map)

    @property
    def file_results(self) -> Dict[str, ParseResult]:
        return dict(self._file_results)

    @property
    def current_files(self) -> list[str]:
        return list(self._current_files)

    @property
    def is_parsing(self) -> bool:
        return bool(self._parser_thread and self._parser_thread.isRunning())
    
    @property
    def viewport_state(self) -> ViewportState:
        """Get the shared viewport state for time synchronization."""
        return self._viewport_state
    
    @property
    def bookmarks(self) -> list[TimeBookmark]:
        """Get all bookmarks sorted by timestamp."""
        return sorted(self._bookmarks)

    # ------------------------------------------------------------------ Public API
    def parse_files(self, file_paths: list[str]) -> bool:
        """Kick off a parse job for the provided file paths."""
        if not file_paths:
            return False

        if self._parser_thread and self._parser_thread.isRunning():
            return False

        self._current_files = list(file_paths)
        self._clear_session_data()

        self._parser_thread = ParserThread(file_paths, self)
        self._parser_thread.finished.connect(self._on_parse_finished)
        self._parser_thread.error.connect(self._on_parse_error)
        self._parser_thread.progress.connect(self.parse_progress)
        self.parse_started.emit(list(file_paths))
        self._parser_thread.start()
        return True

    def clear_session(self):
        """Reset all parsed state."""
        if self._parser_thread and self._parser_thread.isRunning():
            self._parser_thread.requestInterruption()
            self._parser_thread.quit()
            self._parser_thread.wait()
        self._parser_thread = None
        self._current_files = []
        self._clear_session_data()
        self.session_cleared.emit()

    def remove_file(self, file_path: str):
        """Remove a file from the active list (e.g., when user deletes it)."""
        normalized = str(Path(file_path))
        self._current_files = [path for path in self._current_files if path != normalized]
    
    # ------------------------------------------------------------------ Bookmarks
    def add_bookmark(self, timestamp: datetime, label: str, description: str = "") -> TimeBookmark:
        """Add a new bookmark at the specified timestamp.
        
        Args:
            timestamp: Time to bookmark
            label: Short label for the bookmark
            description: Optional detailed description
            
        Returns:
            The created bookmark
        """
        bookmark = TimeBookmark(
            timestamp=timestamp,
            label=label,
            description=description
        )
        self._bookmarks.append(bookmark)
        self._bookmarks.sort()  # Keep sorted by timestamp
        self.bookmarks_changed.emit()
        return bookmark
    
    def remove_bookmark(self, index: int) -> bool:
        """Remove bookmark at the specified index.
        
        Args:
            index: Index in the sorted bookmark list
            
        Returns:
            True if removed successfully, False otherwise
        """
        sorted_bookmarks = self.bookmarks
        if index < 0 or index >= len(sorted_bookmarks):
            return False
        
        bookmark_to_remove = sorted_bookmarks[index]
        self._bookmarks.remove(bookmark_to_remove)
        self.bookmarks_changed.emit()
        return True
    
    def jump_to_bookmark(self, index: int) -> bool:
        """Jump to the bookmark at the specified index.
        
        Args:
            index: Index in the sorted bookmark list
            
        Returns:
            True if jumped successfully, False otherwise
        """
        sorted_bookmarks = self.bookmarks
        if index < 0 or index >= len(sorted_bookmarks):
            return False
        
        bookmark = sorted_bookmarks[index]
        self._current_bookmark_index = index
        self.bookmark_jump_requested.emit(bookmark.timestamp)
        return True
    
    def next_bookmark(self) -> bool:
        """Jump to the next bookmark in chronological order.
        
        Returns:
            True if jumped, False if at end or no bookmarks
        """
        if not self._bookmarks:
            return False
        
        next_index = self._current_bookmark_index + 1
        if next_index >= len(self._bookmarks):
            next_index = 0  # Wrap around
        
        return self.jump_to_bookmark(next_index)
    
    def prev_bookmark(self) -> bool:
        """Jump to the previous bookmark in chronological order.
        
        Returns:
            True if jumped, False if at start or no bookmarks
        """
        if not self._bookmarks:
            return False
        
        prev_index = self._current_bookmark_index - 1
        if prev_index < 0:
            prev_index = len(self._bookmarks) - 1  # Wrap around
        
        return self.jump_to_bookmark(prev_index)
    
    def clear_bookmarks(self):
        """Remove all bookmarks."""
        self._bookmarks.clear()
        self._current_bookmark_index = -1
        self.bookmarks_changed.emit()
    
    # ------------------------------------------------------------------ Time Sync
    def sync_all_views(self, target_time: datetime):
        """Synchronize all views to the specified time.
        
        Args:
            target_time: The time to sync all views to
        """
        # Directly update viewport state for timing diagrams (shared state)
        self._viewport_state.jump_to_time(target_time)
        
        # Emit signal for other view types (LogTable, MapViewer)
        self.sync_requested.emit(target_time)

    # ------------------------------------------------------------------ Internals
    def _on_parse_finished(
        self,
        aggregated_result: ParseResult,
        per_file_results: dict[str, ParseResult],
        signal_data_list: list[SignalData],
    ):
        self._aggregated_result = aggregated_result
        self._parsed_log = aggregated_result.data
        self._file_results = per_file_results
        self._signal_data_list = list(signal_data_list)
        self._signal_data_map = {signal.key: signal for signal in signal_data_list}
        self.session_ready.emit(aggregated_result, per_file_results, signal_data_list)
        self._teardown_parser_thread()

    def _on_parse_error(self, message: str):
        self.parse_failed.emit(message)
        self._teardown_parser_thread()

    def _teardown_parser_thread(self):
        if self._parser_thread:
            self._parser_thread.deleteLater()
            self._parser_thread = None

    def _clear_session_data(self):
        self._aggregated_result = None
        self._parsed_log = None
        self._signal_data_list = []
        self._signal_data_map = {}
        self._file_results = {}
        self.clear_bookmarks()
