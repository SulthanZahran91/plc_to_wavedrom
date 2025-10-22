"""Integrated Map Viewer that uses actual PLC signal data from the main window."""

from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime, timedelta

from PySide6.QtWidgets import QMainWindow, QDockWidget, QWidget, QMessageBox, QFileDialog
from PySide6.QtCore import Qt, QTimer

from plc_visualizer.utils import SignalData
from tools.map_viewer import MapParser, MapRenderer, MediaControls
from tools.map_viewer.state_model import UnitStateModel, SignalEvent
from tools.map_viewer.config_loader import load_mapping_and_policy


class IntegratedMapViewer(QMainWindow):
    """Map viewer integrated with PLC log data from the main window."""

    def __init__(
        self,
        signal_data_list: Optional[List[SignalData]] = None,
        xml_path: Optional[str] = None,
        yaml_cfg: Optional[str] = None,
        parent=None
    ):
        """Initialize the integrated map viewer.

        Args:
            signal_data_list: List of SignalData from the main window
            xml_path: Path to the XML map file
            yaml_cfg: Path to the YAML configuration file
            parent: Parent widget
        """
        super().__init__(parent)
        self.setWindowTitle("PLC Map Viewer")
        self.resize(1200, 800)

        # Signal data from main window
        self._signal_data_list: List[SignalData] = signal_data_list or []
        self._signal_data_map: Dict[str, SignalData] = {}
        self._current_time: Optional[datetime] = None

        # Media player state
        self._is_playing = False
        self._playback_speed = 1.0
        self._start_time: Optional[datetime] = None
        self._end_time: Optional[datetime] = None
        self._playback_timer = QTimer(self)
        self._playback_timer.timeout.connect(self._on_playback_tick)

        # Build signal map by device_id and signal name
        if self._signal_data_list:
            for signal in self._signal_data_list:
                key = f"{signal.device_id}::{signal.name}"
                self._signal_data_map[key] = signal

        # UI components
        self.renderer = MapRenderer()
        self.setCentralWidget(self.renderer)
        self._build_menu_bar()
        self._build_media_dock()

        # Initialize map components
        self.parser = MapParser()
        self.state_model: Optional[UnitStateModel] = None

        if xml_path and yaml_cfg:
            self._load_map(xml_path, yaml_cfg)
        else:
            if not self._try_load_defaults():
                self._prompt_for_map_files()

        # Calculate time range for media controls (after UI is built)
        if self._signal_data_list:
            self._update_time_range()

    def _try_load_defaults(self) -> bool:
        """Try to load default map files."""
        base_path = Path(__file__).parent.parent.parent / "tools" / "map_viewer"
        xml_file = base_path / "test.xml"
        yaml_file = base_path / "mappings_and_rules.yaml"

        if xml_file.exists() and yaml_file.exists():
            self._load_map(str(xml_file), str(yaml_file))
            return True
        return False

    def _prompt_for_map_files(self):
        """Prompt the user to choose map files interactively."""
        xml_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Map XML File",
            "",
            "XML Files (*.xml);;All Files (*)"
        )

        if not xml_path:
            QMessageBox.information(
                self,
                "Map Viewer",
                "No XML file selected. The viewer will remain blank until a file is loaded."
            )
            return

        base_path = Path(xml_path).parent
        default_yaml = base_path / "mappings_and_rules.yaml"

        if default_yaml.exists():
            yaml_path = str(default_yaml)
        else:
            yaml_path, _ = QFileDialog.getOpenFileName(
                self,
                "Select YAML Configuration",
                str(base_path),
                "YAML Files (*.yaml *.yml);;All Files (*)"
            )
            if not yaml_path:
                QMessageBox.information(
                    self,
                    "Map Viewer",
                    "No YAML configuration selected. The viewer cannot load without mappings."
                )
                return

        self._load_map(xml_path, yaml_path)

    def _load_map(self, xml_path: str, yaml_cfg: str):
        """Load and initialize the map.

        Args:
            xml_path: Path to XML map file
            yaml_cfg: Path to YAML configuration file
        """
        try:
            # Parse XML and render static layout
            self.parser.objectsParsed.connect(self.renderer.set_objects)
            objects = self.parser.parse_file(xml_path)

            # Load device mapping and color policy
            device_map, color_policy = load_mapping_and_policy(yaml_cfg)

            # Create state model
            self.state_model = UnitStateModel(device_map, color_policy)
            self.state_model.stateChanged.connect(self.renderer.update_rect_color_by_unit)

            print(f"[MapViewer] Loaded map from {xml_path}")
            print(f"[MapViewer] Loaded {len(objects)} objects from XML")
            print(f"[MapViewer] Available signals: {len(self._signal_data_map)}")

        except Exception as e:
            QMessageBox.critical(
                self,
                "Error Loading Map",
                f"Failed to load map files:\n{str(e)}"
            )

    def _build_menu_bar(self):
        """Build the menu bar."""
        menu_bar = self.menuBar()

        # File menu
        file_menu = menu_bar.addMenu("&File")

        # Open Map action
        open_map_action = file_menu.addAction("&Open Map...")
        open_map_action.triggered.connect(self.load_map_file)

    def _build_media_dock(self):
        """Build the media controls dock."""
        dock = QDockWidget(self)
        dock.setObjectName("MediaPlayerDock")
        dock.setAllowedAreas(Qt.DockWidgetArea.BottomDockWidgetArea)
        dock.setTitleBarWidget(QWidget(dock))
        self.media_controls = MediaControls(dock)
        dock.setWidget(self.media_controls)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, dock)

        # Connect media control signals
        self.media_controls.btn_play.clicked.connect(self._toggle_play)
        self.media_controls.btn_back_10s.clicked.connect(self._skip_backward)
        self.media_controls.btn_fwd_10s.clicked.connect(self._skip_forward)
        self.media_controls.cmb_speed.currentTextChanged.connect(self._on_speed_changed)
        self.media_controls.media_slider.sliderMoved.connect(self._on_slider_moved)
        self.media_controls.txt_time.returnPressed.connect(self._on_time_input)

    def set_signal_data(self, signal_data_list: List[SignalData]):
        """Update the signal data from the main window.

        Args:
            signal_data_list: List of SignalData objects
        """
        self._signal_data_list = signal_data_list
        self._signal_data_map.clear()

        # Build signal map
        for signal in signal_data_list:
            key = f"{signal.device_id}::{signal.name}"
            self._signal_data_map[key] = signal

        # Calculate time range from signal data
        self._update_time_range()

        print(f"[MapViewer] Updated with {len(signal_data_list)} signals")

    def update_time_position(self, current_time: datetime):
        """Update the map to show the state at a specific time.

        Args:
            current_time: The time position to display
        """
        if not self.state_model:
            return

        self._current_time = current_time

        # Find the signal values at this time and update the state model
        for key, signal_data in self._signal_data_map.items():
            device_id = signal_data.device_id
            signal_name = signal_data.name

            # Find the value at current_time
            value = self._get_signal_value_at_time(signal_data, current_time)

            if value is not None:
                # Create signal event
                event = SignalEvent(
                    device_id=device_id,
                    signal_name=signal_name,
                    value=value,
                    timestamp=current_time.timestamp()
                )
                self.state_model.on_signal(event)

    def _get_signal_value_at_time(self, signal_data: SignalData, target_time: datetime):
        """Get the signal value at a specific time.

        Args:
            signal_data: The signal data
            target_time: The target time

        Returns:
            The signal value at the target time, or None if not found
        """
        if not signal_data.states:
            return None

        # Find the state at the target time
        # States are assumed to be ordered by time
        current_value = None

        for state in signal_data.states:
            if state.start_time <= target_time:
                current_value = state.value
            else:
                break

        return current_value

    def _update_time_range(self):
        """Calculate and update the time range from signal data."""
        if not self._signal_data_list:
            self._start_time = None
            self._end_time = None
            return

        # Find min and max times from all signals
        min_time = None
        max_time = None

        for signal in self._signal_data_list:
            if signal.states:
                for state in signal.states:
                    if min_time is None or state.start_time < min_time:
                        min_time = state.start_time
                    if max_time is None or state.start_time > max_time:
                        max_time = state.start_time

        self._start_time = min_time
        self._end_time = max_time

        # Initialize current time to start
        if self._start_time:
            self._current_time = self._start_time
            self.update_time_position(self._current_time)
            self._update_media_controls()
            # Update placeholder to show actual timestamp format
            self.media_controls.txt_time.setPlaceholderText(
                f"e.g., {self._start_time.strftime('%Y-%m-%d %H:%M:%S')}"
            )

    def _update_media_controls(self):
        """Update media control display based on current state."""
        if not self._start_time or not self._end_time:
            return

        # Update slider position
        duration = (self._end_time - self._start_time).total_seconds()
        if duration > 0 and self._current_time:
            progress = (self._current_time - self._start_time).total_seconds() / duration
            self.media_controls.media_slider.setValue(int(progress * 100))

        # Update time label with actual timestamps
        if self._current_time:
            self.media_controls.lbl_current_time.setText(
                f"{self._format_datetime(self._current_time)} / {self._format_datetime(self._end_time)}"
            )

    def _format_time(self, seconds: float) -> str:
        """Format seconds as HH:MM:SS.mmm."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"

    def _format_datetime(self, dt: datetime) -> str:
        """Format datetime as YYYY-MM-DD HH:MM:SS.mmm."""
        return dt.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

    def _toggle_play(self):
        """Toggle play/pause state."""
        if self._is_playing:
            self._pause()
        else:
            self._play()

    def _play(self):
        """Start playback."""
        if not self._start_time or not self._end_time:
            QMessageBox.information(
                self,
                "No Data",
                "Please load signal data before playing."
            )
            return

        # Reset to start if at end
        if self._current_time and self._current_time >= self._end_time:
            self._current_time = self._start_time

        self._is_playing = True
        self.media_controls.btn_play.setText("⏸")

        # Start timer (update every 100ms)
        self._playback_timer.start(100)

    def _pause(self):
        """Pause playback."""
        self._is_playing = False
        self._playback_timer.stop()
        self.media_controls.btn_play.setText("▶")

    def _on_playback_tick(self):
        """Handle playback timer tick."""
        if not self._is_playing or not self._current_time or not self._end_time:
            return

        # Advance time based on playback speed
        # 100ms real time = 100ms * speed playback time
        time_delta = timedelta(milliseconds=100 * self._playback_speed)
        self._current_time += time_delta

        # Check if we've reached the end
        if self._current_time >= self._end_time:
            self._current_time = self._end_time
            self._pause()

        # Update map and controls
        self.update_time_position(self._current_time)
        self._update_media_controls()

    def _skip_backward(self):
        """Skip backward 10 seconds."""
        if not self._current_time or not self._start_time:
            return

        self._current_time -= timedelta(seconds=10)
        if self._current_time < self._start_time:
            self._current_time = self._start_time

        self.update_time_position(self._current_time)
        self._update_media_controls()

    def _skip_forward(self):
        """Skip forward 10 seconds."""
        if not self._current_time or not self._end_time:
            return

        self._current_time += timedelta(seconds=10)
        if self._current_time > self._end_time:
            self._current_time = self._end_time

        self.update_time_position(self._current_time)
        self._update_media_controls()

    def _on_speed_changed(self, speed_text: str):
        """Handle playback speed change."""
        try:
            speed = float(speed_text.replace('×', ''))
            self._playback_speed = speed
        except ValueError:
            pass

    def _on_slider_moved(self, position: int):
        """Handle slider position change."""
        if not self._start_time or not self._end_time:
            return

        # Convert slider position (0-100) to time
        duration = (self._end_time - self._start_time).total_seconds()
        target_seconds = (position / 100.0) * duration
        self._current_time = self._start_time + timedelta(seconds=target_seconds)

        self.update_time_position(self._current_time)
        self._update_media_controls()

    def _on_time_input(self):
        """Handle time input from text field."""
        if not self._start_time or not self._end_time:
            return

        time_text = self.media_controls.txt_time.text().strip()
        try:
            # Try to parse as full datetime first (YYYY-MM-DD HH:MM:SS or YYYY-MM-DD HH:MM:SS.mmm)
            target_time = None
            if ' ' in time_text:
                try:
                    if '.' in time_text:
                        target_time = datetime.strptime(time_text, "%Y-%m-%d %H:%M:%S.%f")
                    else:
                        target_time = datetime.strptime(time_text, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    pass

            # If not a full datetime, parse as relative time HH:MM:SS
            if target_time is None:
                parts = time_text.split(':')
                if len(parts) == 3:
                    hours = int(parts[0])
                    minutes = int(parts[1])
                    seconds = float(parts[2])
                    total_seconds = hours * 3600 + minutes * 60 + seconds
                    target_time = self._start_time + timedelta(seconds=total_seconds)
                else:
                    raise ValueError("Invalid format")

            # Check if within range
            if self._start_time <= target_time <= self._end_time:
                self._current_time = target_time
                self.update_time_position(self._current_time)
                self._update_media_controls()
                self.media_controls.txt_time.clear()
            else:
                QMessageBox.warning(
                    self,
                    "Invalid Time",
                    f"Time must be between:\n{self._format_datetime(self._start_time)}\nand\n{self._format_datetime(self._end_time)}"
                )
        except ValueError:
            QMessageBox.warning(
                self,
                "Invalid Time",
                "Please enter time in one of these formats:\n"
                "- YYYY-MM-DD HH:MM:SS.mmm (absolute)\n"
                "- YYYY-MM-DD HH:MM:SS (absolute)\n"
                "- HH:MM:SS.mmm (relative from start)\n"
                "- HH:MM:SS (relative from start)"
            )

    def load_map_file(self):
        """Allow user to load a different map XML file."""
        xml_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Map XML File",
            "",
            "XML Files (*.xml);;All Files (*)"
        )

        if xml_path:
            base_path = Path(xml_path).parent
            yaml_path = base_path / "mappings_and_rules.yaml"

            if not yaml_path.exists():
                yaml_path, _ = QFileDialog.getOpenFileName(
                    self,
                    "Select YAML Configuration",
                    str(base_path),
                    "YAML Files (*.yaml *.yml);;All Files (*)"
                )
                if not yaml_path:
                    return

            self._load_map(xml_path, str(yaml_path))
