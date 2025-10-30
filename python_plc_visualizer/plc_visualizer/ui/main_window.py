"""Main application window for PLC Log Visualizer."""

from datetime import datetime
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QResizeEvent, QAction, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QHBoxLayout,
    QLabel,
    QInputDialog,
)

from plc_visualizer.app import SessionManager
from plc_visualizer.models import ParseResult
from plc_visualizer.utils import SignalData, compute_signal_states
from .components.split_pane_manager import SplitPaneManager
from .views.home_view import HomeView
from .windows.timing_window import TimingDiagramView
from .windows.log_table_window import LogTableView
from .windows.interval_window import SignalIntervalDialog
from .windows.map_viewer_window import MapViewerView
from .dialogs.signal_selection_dialog import SignalSelectionDialog
from .dialogs.bookmark_dialog import BookmarkDialog
from .dialogs.help_dialog import HelpDialog


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self):
        super().__init__()
        platform_name = ""
        app = QApplication.instance()
        if app:
            try:
                platform_name = app.platformName().lower()
            except Exception:
                platform_name = ""
        self._is_wayland = "wayland" in platform_name
        print(f"[MainWindow] Initialized on platform '{platform_name}', is_wayland={self._is_wayland}")

        self.session_manager = SessionManager(self)
        
        # Split pane manager for views
        self._split_pane_manager: Optional[SplitPaneManager] = None
        self._home_view: Optional[HomeView] = None
        
        # Dialog windows
        self._interval_windows: dict[str, SignalIntervalDialog] = {}
        self._interval_selection_window: Optional[SignalSelectionDialog] = None
        self._bookmark_dialog: Optional[BookmarkDialog] = None
        self._help_dialog: Optional[HelpDialog] = None

        self._sync_button: Optional[QPushButton] = None

        self._init_ui()
        self._bind_session_manager()

    def _init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("PLC Log Visualizer")
        self.setMinimumSize(1400, 900)

        self._create_menu_bar()

        # Create header widget
        header_widget = QWidget()
        header_widget.setStyleSheet("""
            QWidget {
                background-color: #003D82;
                padding: 10px 18px;
            }
        """)
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(18, 10, 18, 10)
        header_layout.setSpacing(10)

        # Header title
        header_label = QLabel("PLC Log Visualizer")
        header_label.setStyleSheet("color: white; font-size: 16px; font-weight: bold;")
        header_layout.addWidget(header_label)
        header_layout.addStretch()

        # Help button in header
        help_button = QPushButton("❓ Help")
        help_button.setMaximumWidth(80)
        help_button.setStyleSheet("""
            QPushButton {
                background-color: #34A853;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2D8E47;
            }
            QPushButton:pressed {
                background-color: #1E7735;
            }
        """)
        help_button.clicked.connect(self._show_help_dialog)
        header_layout.addWidget(help_button)

        # Sync All Views button in header
        self._sync_button = QPushButton("🔗 Sync Views")
        self._sync_button.setMaximumWidth(120)
        self._sync_button.setEnabled(False)  # Disabled until data is loaded
        self._sync_button.setStyleSheet("""
            QPushButton {
                background-color: #4285F4;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1967D2;
            }
            QPushButton:pressed {
                background-color: #0D47A1;
            }
            QPushButton:disabled {
                background-color: #BDBDBD;
                color: #E0E0E0;
            }
        """)
        self._sync_button.clicked.connect(self._on_sync_all_views)
        header_layout.addWidget(self._sync_button)
        
        # Clear File button in header
        clear_button = QPushButton("Clear")
        clear_button.setMaximumWidth(90)
        clear_button.setStyleSheet("""
            QPushButton {
                background-color: #F44336;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #D32F2F;
            }
            QPushButton:pressed {
                background-color: #B71C1C;
            }
        """)
        clear_button.clicked.connect(self._on_clear_file)
        header_layout.addWidget(clear_button)

        # Main layout structure
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Add header
        main_layout.addWidget(header_widget)

        # Split Pane Manager fills entire area below header
        self._split_pane_manager = SplitPaneManager()
        self._split_pane_manager.view_closed.connect(self._on_view_closed)
        main_layout.addWidget(self._split_pane_manager, 1)
        
        # Create and add HomeView as the initial tab
        self._home_view = HomeView(self.session_manager, self)
        self._home_view.upload_widget.files_selected.connect(self._on_files_selected)
        self._home_view.file_list_widget.file_removed.connect(self._on_file_removed_from_list)
        
        # Connect view button signals to view creation methods
        self._home_view.timing_diagram_requested.connect(self._add_timing_view)
        self._home_view.log_table_requested.connect(self._add_log_table_view)
        self._home_view.map_viewer_requested.connect(self._add_map_viewer_view)
        self._home_view.signal_intervals_requested.connect(self._open_signal_interval_windows)
        
        self._split_pane_manager.add_view(self._home_view, "🏠 Home")

        self.setStyleSheet("""
            QMainWindow {
                background-color: #ffffff;
            }
        """)

    def _bind_session_manager(self):
        """Connect session manager signals to window handlers."""
        self.session_manager.parse_started.connect(self._on_parse_started)
        self.session_manager.parse_progress.connect(self._on_parse_progress)
        self.session_manager.parse_failed.connect(self._on_parse_error)
        self.session_manager.session_ready.connect(self._on_session_ready)
        self.session_manager.session_cleared.connect(self._on_session_cleared)
        
        # Connect bookmark signals
        self.session_manager.bookmark_jump_requested.connect(self._on_bookmark_jump)
        self.session_manager.bookmarks_changed.connect(self._on_bookmarks_changed)

    def _create_menu_bar(self):
        """Create the menu bar with view and bookmark menus."""
        menu_bar = self.menuBar()
        
        # View menu for adding new views
        view_menu = menu_bar.addMenu("&View")

        timing_action = view_menu.addAction("New &Timing Diagram")
        timing_action.setShortcut(QKeySequence("Ctrl+T"))
        timing_action.triggered.connect(self._add_timing_view)

        table_action = view_menu.addAction("New &Log Table")
        table_action.setShortcut(QKeySequence("Ctrl+L"))
        table_action.triggered.connect(self._add_log_table_view)

        map_viewer_action = view_menu.addAction("New Map &Viewer")
        map_viewer_action.setShortcut(QKeySequence("Ctrl+M"))
        map_viewer_action.triggered.connect(self._add_map_viewer_view)
        
        view_menu.addSeparator()

        interval_action = view_menu.addAction("Plot &Signal Intervals")
        interval_action.triggered.connect(self._open_signal_interval_windows)
        
        # Bookmarks menu
        bookmarks_menu = menu_bar.addMenu("&Bookmarks")
        
        add_bookmark_action = bookmarks_menu.addAction("&Add Bookmark at Current Time")
        add_bookmark_action.setShortcut(QKeySequence("Ctrl+B"))
        add_bookmark_action.triggered.connect(self._add_bookmark_at_current_time)
        
        show_bookmarks_action = bookmarks_menu.addAction("&Show Bookmarks")
        show_bookmarks_action.setShortcut(QKeySequence("Ctrl+Shift+B"))
        show_bookmarks_action.triggered.connect(self._show_bookmark_dialog)
        
        bookmarks_menu.addSeparator()
        
        next_bookmark_action = bookmarks_menu.addAction("&Next Bookmark")
        next_bookmark_action.setShortcut(QKeySequence("Ctrl+]"))
        next_bookmark_action.triggered.connect(self.session_manager.next_bookmark)
        
        prev_bookmark_action = bookmarks_menu.addAction("&Previous Bookmark")
        prev_bookmark_action.setShortcut(QKeySequence("Ctrl+["))
        prev_bookmark_action.triggered.connect(self.session_manager.prev_bookmark)
        
        # Help menu
        help_menu = menu_bar.addMenu("&Help")
        
        help_action = help_menu.addAction("&Multi-View System Help")
        help_action.setShortcut(QKeySequence("F1"))
        help_action.triggered.connect(self._show_help_dialog)

    # View management methods -----------------------------------------------
    def _add_timing_view(self):
        """Add a new timing diagram view to the split pane manager."""
        if not self._split_pane_manager:
            return
        
        view = TimingDiagramView(self.session_manager.viewport_state, self)
        view.set_interval_request_handler(self._open_signal_interval_for_key)
        
        # Set data if available
        parsed_log = self.session_manager.parsed_log
        signal_data = self.session_manager.signal_data_list
        if parsed_log:
            view.set_data(parsed_log, signal_data)
        
        self._split_pane_manager.add_view(view, "Timing Diagram")
    
    def _add_log_table_view(self):
        """Add a new log table view to the split pane manager."""
        if not self._split_pane_manager:
            return
        
        view = LogTableView(self)
        view.set_interval_request_handler(self._open_signal_interval_for_key)
        
        # Set data if available
        parsed_log = self.session_manager.parsed_log
        signal_data = self.session_manager.signal_data_list
        if parsed_log:
            view.set_data(parsed_log, signal_data)
        
        self._split_pane_manager.add_view(view, "Log Table")
    
    def _add_map_viewer_view(self):
        """Add a new map viewer view to the split pane manager."""
        if not self._split_pane_manager:
            return
        
        signal_data = self.session_manager.signal_data_list
        
        # Find default map files
        base_path = Path(__file__).parent.parent.parent / "tools" / "map_viewer"
        xml_file = base_path / "test.xml"
        yaml_file = base_path / "mappings_and_rules.yaml"
        
        xml_path = str(xml_file) if xml_file.exists() else None
        yaml_path = str(yaml_file) if yaml_file.exists() else None
        
        view = MapViewerView(signal_data, xml_path, yaml_path, self)
        self._split_pane_manager.add_view(view, "Map Viewer")
    
    def _on_view_closed(self, view: QWidget):
        """Handle when a view is closed."""
        # Clean up any resources associated with the view
        if hasattr(view, 'clear'):
            view.clear()
    
    # Sync and bookmark methods ---------------------------------------------
    def _on_sync_all_views(self):
        """Sync all views to the current time of the active view."""
        if not self._split_pane_manager:
            return
        
        active_view = self._split_pane_manager.get_active_view()
        if not active_view:
            QMessageBox.information(
                self,
                "No Active View",
                "Please select a view first."
            )
            return
        
        # Get current time from active view
        current_time = None
        if isinstance(active_view, TimingDiagramView):
            visible_range = active_view.viewport_state.visible_time_range
            if visible_range:
                current_time = visible_range[0]  # Use start of visible range
        
        if current_time:
            self.session_manager.sync_all_views(current_time)
        else:
            QMessageBox.information(
                self,
                "No Time Available",
                "The active view does not have a time position to sync."
            )
    
    def _add_bookmark_at_current_time(self):
        """Add a bookmark at the current time position."""
        # Get current time from active timing view
        current_time = None
        if self._split_pane_manager:
            active_view = self._split_pane_manager.get_active_view()
            if isinstance(active_view, TimingDiagramView):
                visible_range = active_view.viewport_state.visible_time_range
                if visible_range:
                    current_time = visible_range[0]
        
        if not current_time:
            # Try to get from session manager's viewport state
            visible_range = self.session_manager.viewport_state.visible_time_range
            if visible_range:
                current_time = visible_range[0]
        
        if not current_time:
            QMessageBox.information(
                self,
                "No Time Available",
                "Please open a timing diagram view first."
            )
            return
        
        # Prompt for bookmark label
        label, ok = QInputDialog.getText(
            self,
            "Add Bookmark",
            f"Bookmark label for {current_time.strftime('%H:%M:%S.%f')[:-3]}:",
            text="Bookmark"
        )
        
        if ok and label.strip():
            self.session_manager.add_bookmark(current_time, label.strip())
            QMessageBox.information(
                self,
                "Bookmark Added",
                f"Added bookmark '{label.strip()}' at {current_time.strftime('%H:%M:%S.%f')[:-3]}"
            )
    
    def _show_bookmark_dialog(self):
        """Show the bookmark management dialog."""
        if self._bookmark_dialog is None or not self._bookmark_dialog.isVisible():
            self._bookmark_dialog = BookmarkDialog(
                self.session_manager.bookmarks,
                add_callback=self._on_bookmark_dialog_add,
                delete_callback=self._on_bookmark_dialog_delete,
                parent=self
            )
            self._bookmark_dialog.bookmark_selected.connect(self.session_manager.jump_to_bookmark)
        
        self._bookmark_dialog.set_bookmarks(self.session_manager.bookmarks)
        self._bookmark_dialog.show()
        self._bookmark_dialog.raise_()
        self._bookmark_dialog.activateWindow()
    
    def _on_bookmark_dialog_add(self, label: str, description: str):
        """Handle adding bookmark from dialog."""
        # Use current time
        current_time = None
        visible_range = self.session_manager.viewport_state.visible_time_range
        if visible_range:
            current_time = visible_range[0]
        
        if current_time:
            self.session_manager.add_bookmark(current_time, label, description)
    
    def _on_bookmark_dialog_delete(self, index: int):
        """Handle deleting bookmark from dialog."""
        self.session_manager.remove_bookmark(index)
    
    def _on_bookmark_jump(self, target_time: datetime):
        """Handle jumping to a bookmark time."""
        self.session_manager.viewport_state.jump_to_time(target_time)
    
    def _on_bookmarks_changed(self):
        """Handle when bookmarks list changes."""
        if self._bookmark_dialog and self._bookmark_dialog.isVisible():
            self._bookmark_dialog.set_bookmarks(self.session_manager.bookmarks)
    
    def _show_help_dialog(self):
        """Show the help dialog."""
        if self._help_dialog is None or not self._help_dialog.isVisible():
            self._help_dialog = HelpDialog(self)
        
        self._help_dialog.show()
        self._help_dialog.raise_()
        self._help_dialog.activateWindow()

    # Legacy methods (to be removed or refactored) -------------------------
    def _open_timing_diagram_window(self):
        """Launch or focus the timing diagram window."""
        if self._timing_window is not None:
            try:
                self._timing_window.show()
                self._timing_window.raise_()
                self._timing_window.activateWindow()
                return
            except RuntimeError:
                self._timing_window = None

        self._timing_window = TimingDiagramWindow(self)
        self._timing_window.set_interval_request_handler(self._open_signal_interval_for_key)
        self._timing_window.destroyed.connect(self._on_timing_window_destroyed)

        parsed_log = self.session_manager.parsed_log
        signal_data = self.session_manager.signal_data_list
        if parsed_log:
            self._timing_window.set_data(parsed_log, signal_data)
        else:
            self._timing_window.clear()

        if self._map_viewer_window is not None:
            try:
                self._timing_window.viewport_state.time_range_changed.connect(self._on_map_viewer_time_update)
            except (RuntimeError, TypeError):
                pass

        self._timing_window.show()
        self._timing_window.raise_()
        self._timing_window.activateWindow()

        if self._map_viewer_window is not None:
            visible_range = self._timing_window.viewport_state.visible_time_range
            if visible_range:
                start_time, _ = visible_range
                try:
                    self._map_viewer_window.update_time_position(start_time)
                except RuntimeError:
                    self._map_viewer_window = None

    def _on_timing_window_destroyed(self, _obj=None):
        """Reset timing window reference when it is closed."""
        self._timing_window = None

    def _open_log_table_window(self):
        """Launch or focus the log table window."""
        if self._table_window is not None:
            try:
                self._table_window.show()
                self._table_window.raise_()
                self._table_window.activateWindow()
                return
            except RuntimeError:
                self._table_window = None

        self._table_window = LogTableWindow(self)
        self._table_window.set_interval_request_handler(self._open_signal_interval_for_key)
        self._table_window.destroyed.connect(self._on_table_window_destroyed)

        parsed_log = self.session_manager.parsed_log
        signal_data = self.session_manager.signal_data_list
        if parsed_log:
            self._table_window.set_data(parsed_log, signal_data)
        else:
            self._table_window.clear()

        self._table_window.show()
        self._table_window.raise_()
        self._table_window.activateWindow()

    def _on_table_window_destroyed(self, _obj=None):
        """Reset table window reference when it is closed."""
        self._table_window = None

    def _open_map_viewer(self):
        """Launch the map viewer in a separate window."""
        try:
            from plc_visualizer.ui.integrated_map_viewer import IntegratedMapViewer

            if self._map_viewer_window is not None:
                try:
                    self._map_viewer_window.show()
                    self._map_viewer_window.raise_()
                    self._map_viewer_window.activateWindow()
                    return
                except RuntimeError:
                    self._map_viewer_window = None

            base_path = Path(__file__).parent.parent.parent / "tools" / "map_viewer"
            xml_file = None
            yaml_file = None

            if base_path.exists():
                candidate_xml = base_path / "test.xml"
                candidate_yaml = base_path / "mappings_and_rules.yaml"
                if candidate_xml.exists():
                    xml_file = candidate_xml
                if candidate_yaml.exists():
                    yaml_file = candidate_yaml

            self._map_viewer_window = IntegratedMapViewer(
                signal_data_list=self.session_manager.signal_data_list,
                xml_path=str(xml_file) if xml_file else None,
                yaml_cfg=str(yaml_file) if yaml_file else None,
                parent=self,
            )

            if self._timing_window is not None:
                try:
                    self._timing_window.viewport_state.time_range_changed.connect(self._on_map_viewer_time_update)
                except (RuntimeError, TypeError):
                    pass

            self._map_viewer_window.show()
            self._map_viewer_window.raise_()
            self._map_viewer_window.activateWindow()

            if self._timing_window is not None:
                visible_range = self._timing_window.viewport_state.visible_time_range
                if visible_range:
                    start_time, _ = visible_range
                    try:
                        self._map_viewer_window.update_time_position(start_time)
                    except RuntimeError:
                        self._map_viewer_window = None

        except ImportError as e:
            QMessageBox.warning(
                self,
                "Map Viewer Not Available",
                f"Could not load the map viewer module:\n{str(e)}"
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error Opening Map Viewer",
                f"An error occurred while opening the map viewer:\n{str(e)}"
            )

    def _open_signal_interval_windows(self):
        """Open or focus signal interval windows instead of blocking dialogs."""
        signal_data_list = self.session_manager.signal_data_list

        if not signal_data_list:
            QMessageBox.information(
                self,
                "No Signals Loaded",
                "Load a PLC log before plotting signal intervals.",
            )
            return

        if len(signal_data_list) == 1:
            self._open_signal_interval_for_key(signal_data_list[0].key)
            return

        if self._interval_selection_window is not None:
            try:
                self._interval_selection_window.show()
                self._interval_selection_window.raise_()
                self._interval_selection_window.activateWindow()
                return
            except RuntimeError:
                self._interval_selection_window = None

        selector = SignalSelectionDialog(signal_data_list, self)
        selector.setModal(False)
        selector.setWindowModality(Qt.WindowModality.NonModal)
        selector.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        selector.accepted.connect(lambda sel=selector: self._handle_signal_selection(sel))
        selector.destroyed.connect(self._on_signal_selection_window_destroyed)
        self._interval_selection_window = selector

        selector.show()
        selector.raise_()
        selector.activateWindow()

    def _handle_signal_selection(self, selector: SignalSelectionDialog):
        """Handle acceptance from the non-modal signal selector."""
        selected_key = selector.selected_key
        if selected_key:
            self._open_signal_interval_for_key(selected_key)

    def _on_signal_selection_window_destroyed(self, _obj=None):
        """Clear selection window reference once it closes."""
        self._interval_selection_window = None

    def _ensure_signal_states(self, signal_data: SignalData) -> bool:
        """Ensure SignalData has populated states by recomputing if necessary."""
        if signal_data.states:
            return True

        parsed_log = self.session_manager.parsed_log
        if not parsed_log:
            return False

        try:
            compute_signal_states(signal_data, parsed_log)
        except Exception as exc:
            print(f"[Intervals] Failed to rebuild states for {signal_data.key}: {exc}")
            return False

        return bool(signal_data.states)

    def _pin_signal_data(self, signal_key: str):
        """Prevent a signal's states from being cleared while an interval window is open."""
        signal_data = self.session_manager.signal_data_map.get(signal_key)
        if signal_data:
            signal_data.pinned = True

    def _unpin_signal_data(self, signal_key: str):
        """Allow a signal's states to be cleared when no window depends on it."""
        signal_data = self.session_manager.signal_data_map.get(signal_key)
        if signal_data:
            signal_data.pinned = False

    def _on_interval_window_destroyed(self, signal_key: str):
        """Cleanup when a signal interval window is closed."""
        self._interval_windows.pop(signal_key, None)
        self._unpin_signal_data(signal_key)

    def _open_signal_interval_for_key(self, signal_key: str):
        """Open the signal interval dialog for a specific signal key."""
        if not signal_key:
            return

        signal_data = self.session_manager.signal_data_map.get(signal_key)
        if signal_data is None:
            QMessageBox.information(
                self,
                "Signal Not Available",
                "The selected signal is no longer available. Please reload the data.",
            )
            return

        if not signal_data.states or len(signal_data.states) < 2:
            if not self._ensure_signal_states(signal_data):
                QMessageBox.information(
                    self,
                    "Transitions Not Available",
                    "Could not reconstruct transitions for this signal. Reload the log and try again.",
                )
                return

        if len(signal_data.states) < 2:
            QMessageBox.information(
                self,
                "No Transitions",
                "This signal does not have enough transitions to plot change intervals.",
            )
            return

        existing = self._interval_windows.get(signal_key)
        if existing is not None:
            try:
                existing.show()
                existing.raise_()
                existing.activateWindow()
                return
            except RuntimeError:
                self._interval_windows.pop(signal_key, None)

        window = SignalIntervalDialog(signal_data, self)
        window.setModal(False)
        window.setWindowModality(Qt.WindowModality.NonModal)
        window.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        window.destroyed.connect(lambda _obj=None, key=signal_key: self._on_interval_window_destroyed(key))
        self._interval_windows[signal_key] = window
        self._pin_signal_data(signal_key)

        window.show()
        window.raise_()
        window.activateWindow()

    def _on_map_viewer_time_update(self, start_time, _end_time):
        """Update map viewer when waveform time changes."""
        if self._map_viewer_window is not None:
            try:
                self._map_viewer_window.update_time_position(start_time)
            except RuntimeError:
                self._map_viewer_window = None

    def _on_files_selected(self, file_paths: list[str]):
        """Handle selection of one or more files."""
        if not file_paths:
            return

        resolved_paths: list[str] = []
        missing_paths: list[str] = []

        for path in file_paths:
            normalized = str(Path(path).expanduser().resolve())
            if Path(normalized).is_file():
                if normalized not in resolved_paths:
                    resolved_paths.append(normalized)
            else:
                missing_paths.append(path)

        if missing_paths:
            missing_list = "\n".join(missing_paths)
            QMessageBox.warning(
                self,
                "Missing Files",
                f"The following files could not be found:\n\n{missing_list}"
            )

        if not resolved_paths:
            return

        if self.session_manager.is_parsing:
            QMessageBox.information(
                self,
                "Parsing In Progress",
                "Please wait for the current parsing job to complete before starting a new one."
            )
            return

        # Add files to file list widget
        if self._home_view and self._home_view.file_list_widget:
            for file_path in resolved_paths:
                self._home_view.file_list_widget.add_file(file_path)

        if not self.session_manager.parse_files(resolved_paths):
            QMessageBox.information(
                self,
                "Parsing In Progress",
                "Please wait for the current parsing job to complete before starting a new one."
            )
            return

    def _on_parse_started(self, file_paths: list[str]):
        """Prepare UI for a new parse job."""
        if not file_paths:
            return

        if self._home_view:
            self._home_view.progress_bar.setVisible(True)
            self._home_view.upload_widget.setEnabled(False)
            names = ", ".join(Path(path).name for path in file_paths)
            self._home_view.upload_widget.set_status(
                f"📄 Parsing {len(file_paths)} file(s): {names}"
            )
            self._home_view.progress_bar.setRange(0, len(file_paths))
            self._home_view.progress_bar.setValue(0)
            self._home_view.progress_bar.setFormat("Parsing files... %p%")
            
            if self._home_view.stats_widget:
                self._home_view.stats_widget.clear()

        self._reset_child_windows(clear_only=True)

    def _on_session_ready(
        self,
        aggregated_result: ParseResult,
        per_file_results: dict[str, ParseResult],
        signal_data_list: list[SignalData],
    ):
        """Handle completion of a parse job."""
        if self._home_view:
            self._home_view.progress_bar.setVisible(False)
            self._home_view.progress_bar.reset()
            self._home_view.progress_bar.setFormat("Parsing files... %p%")
            self._home_view.upload_widget.setEnabled(True)

            if self._home_view.file_list_widget:
                self._home_view.file_list_widget.hide_all_progress()

        total_files = len(self.session_manager.current_files)
        successful_files = [
            path for path, result in per_file_results.items() if result.success
        ]
        failed_files = [
            path for path, result in per_file_results.items() if not result.success
        ]

        if self._home_view and self._home_view.stats_widget:
            self._home_view.stats_widget.update_stats(aggregated_result)

        if not aggregated_result.success:
            primary_error = aggregated_result.errors[0] if aggregated_result.errors else None
            details = ""
            if primary_error:
                file_name = Path(primary_error.file_path).name if primary_error.file_path else "Unknown file"
                details = f":\n\n[{file_name}] {primary_error.reason}"

            QMessageBox.critical(
                self,
                "Parsing Error",
                f"Failed to parse selected files{details}"
            )
            if self._home_view:
                self._home_view.upload_widget.set_status(
                    "📁 Drag and drop log files here\nor click to browse"
                )
            return

        parsed_log = aggregated_result.data
        
        # Update all views in split pane manager
        if self._split_pane_manager:
            for view in self._split_pane_manager.get_all_views():
                try:
                    if isinstance(view, (TimingDiagramView, LogTableView)):
                        view.set_data(parsed_log, signal_data_list)
                    elif isinstance(view, MapViewerView):
                        view.set_signal_data(signal_data_list)
                except (RuntimeError, AttributeError):
                    pass
        
        # Enable sync button when data is available
        has_data = parsed_log is not None
        if self._sync_button:
            self._sync_button.setEnabled(has_data)

        success_count = len(successful_files)
        status = f"✓ Loaded {success_count} of {total_files} file(s)"
        if aggregated_result.has_errors:
            status += f" with {aggregated_result.error_count} error(s)"
        if self._home_view:
            self._home_view.upload_widget.set_status(status)

        if aggregated_result.has_errors and aggregated_result.error_count > 5:
            QMessageBox.warning(
                self,
                "Parsing Warnings",
                f"Files parsed with {aggregated_result.error_count} error(s).\n"
                f"Successfully parsed {aggregated_result.data.entry_count} entries.\n\n"
                f"See the statistics panel for details."
            )

        if failed_files:
            failed_names = "\n".join(Path(path).name for path in failed_files)
            QMessageBox.warning(
                self,
                "Parsing Warnings",
                "Some files could not be parsed:\n\n"
                f"{failed_names}\n\n"
                "See the statistics panel for error details."
            )

    def _on_parse_error(self, error_msg: str):
        """Handle parsing errors emitted by the session manager."""
        if self._home_view:
            self._home_view.progress_bar.setVisible(False)
            self._home_view.upload_widget.setEnabled(True)
            self._home_view.progress_bar.reset()
            self._home_view.progress_bar.setFormat("Parsing files... %p%")
            self._home_view.upload_widget.set_status(
                "📁 Drag and drop log files here\nor click to browse"
            )
        if self._sync_button:
            self._sync_button.setEnabled(False)
        QMessageBox.critical(self, "Error", error_msg)

    def _on_parse_progress(self, current: int, total: int, file_path: str):
        """Update progress bar as files are parsed."""
        if total <= 0:
            return

        if self._home_view:
            self._home_view.progress_bar.setRange(0, total)
            self._home_view.progress_bar.setValue(current)
            filename = Path(file_path).name if file_path else ""
            self._home_view.progress_bar.setFormat(
                f"Parsing {current}/{total} file(s) - {filename}"
            )

            if self._home_view.file_list_widget and file_path:
                file_progress = int((current / total) * 100) if total > 0 else 0
                self._home_view.file_list_widget.update_progress(file_path, file_progress)

    def _on_session_cleared(self):
        """Reset UI when the active session is cleared."""
        if self._home_view:
            self._home_view.progress_bar.setVisible(False)
            self._home_view.progress_bar.reset()
            self._home_view.progress_bar.setFormat("Parsing files... %p%")
            self._home_view.upload_widget.setEnabled(True)
            self._home_view.upload_widget.set_status(
                "📁 Drag and drop log files here\nor click to browse"
            )

            if self._home_view.stats_widget:
                self._home_view.stats_widget.clear()

            if self._home_view.file_list_widget:
                self._home_view.file_list_widget.hide_all_progress()

        # Clear all views in split pane manager
        if self._split_pane_manager:
            for view in self._split_pane_manager.get_all_views():
                try:
                    if hasattr(view, 'clear'):
                        view.clear()
                except (RuntimeError, AttributeError):
                    pass
        
        # Disable sync button
        if self._sync_button:
            self._sync_button.setEnabled(False)
        
        self._reset_child_windows(clear_only=False)

    def _reset_child_windows(self, *, clear_only: bool):
        """Clear or close auxiliary windows depending on session state."""
        if self._timing_window is not None:
            try:
                if clear_only:
                    self._timing_window.clear()
                else:
                    self._timing_window.close()
                    self._timing_window = None
            except RuntimeError:
                self._timing_window = None

        if self._table_window is not None:
            try:
                if clear_only:
                    self._table_window.clear()
                else:
                    self._table_window.close()
                    self._table_window = None
            except RuntimeError:
                self._table_window = None

        if self._map_viewer_window is not None:
            try:
                if clear_only:
                    self._map_viewer_window.set_signal_data([])
                else:
                    self._map_viewer_window.close()
                    self._map_viewer_window = None
            except RuntimeError:
                self._map_viewer_window = None

        for window in list(self._interval_windows.values()):
            try:
                window.close()
            except RuntimeError:
                pass
        self._interval_windows.clear()

    def _on_file_removed_from_list(self, file_path: str):
        """Handle file removal from file list widget (trash button clicked)."""
        self.session_manager.remove_file(file_path)

    def _on_clear_file(self):
        """Handle Clear File button click - reset everything."""
        if self._home_view:
            if self._home_view.file_list_widget:
                self._home_view.file_list_widget.clear_all()

            if self._home_view.stats_widget:
                self._home_view.stats_widget.clear()

        self.session_manager.clear_session()

    def resizeEvent(self, event: QResizeEvent):
        """Log resize information (useful for debugging Wayland sizing)."""
        super().resizeEvent(event)
        if self._is_wayland:
            handle = self.windowHandle()
            handle_size = handle.size() if handle else None
            print(f"[MainWindow] resizeEvent old={event.oldSize()}, new={event.size()}, handle_size={handle_size}")
