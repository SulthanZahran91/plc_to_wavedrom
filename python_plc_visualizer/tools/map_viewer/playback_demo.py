#!/usr/bin/env python3
"""
Playback demo for the map viewer using generated CSV signal data.

This demo loads test_map.xml and test_signals.csv, then replays
the signals in real-time to demonstrate signal-driven color updates.

Usage:
    python playback_demo.py
    python playback_demo.py --map test_map.xml --signals test_signals.csv --speed 2.0
"""

import sys
import csv
import argparse
import logging
from pathlib import Path
from datetime import datetime
from typing import Iterable, Iterator, List
from PySide6.QtWidgets import QApplication, QMainWindow, QDockWidget, QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt, QTimer

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from tools.map_viewer import MapParser, MapRenderer, MediaControls
    from tools.map_viewer.state_model import UnitStateModel, SignalEvent
    from tools.map_viewer.config_loader import load_mapping_and_policy
except ModuleNotFoundError:
    # Fallback for environments that still package map_viewer as a top-level module
    from map_viewer import MapParser, MapRenderer, MediaControls
    from map_viewer.state_model import UnitStateModel, SignalEvent
    from map_viewer.config_loader import load_mapping_and_policy


def _resolve_resource(path_value: Path, base_dir: Path) -> Path:
    """Resolve maps/signals/config paths relative to the script if needed."""
    if path_value.is_absolute():
        return path_value

    if path_value.exists():
        return path_value

    candidate = base_dir / path_value
    if candidate.exists():
        return candidate
    return path_value


class SignalPlayer:
    """Replays signal events from a CSV file."""

    def __init__(self, csv_path: str, state_model: UnitStateModel):
        self.state_model = state_model
        self.events = []
        self.current_index = 0
        self.is_playing = False
        self.playback_speed = 1.0

        # Load CSV
        with open(csv_path, 'r', newline='') as f:
            reader = csv.reader(f)
            first_row = next(reader, None)
            if first_row is None:
                return

            header_map = self._detect_header(first_row)
            data_iter: Iterable[List[str]]
            if header_map:
                data_iter = reader
            else:
                data_iter = self._chain_first(first_row, reader)
                header_map = {
                    'timestamp': 0,
                    'deviceid': 1,
                    'signal': 2,
                    'value': 3
                }

            for row in data_iter:
                if len(row) < 4:
                    continue

                timestamp_raw = row[header_map['timestamp']].strip()
                device_id = row[header_map['deviceid']].strip()
                signal_name = row[header_map['signal']].strip()
                value_raw = row[header_map['value']].strip()

                # Parse timestamp
                ts = self._parse_timestamp(timestamp_raw)

                # Convert value to appropriate type
                value = self._convert_value(value_raw)

                event = SignalEvent(
                    device_id=device_id,
                    signal_name=signal_name,
                    value=value,
                    timestamp=ts.timestamp()
                )
                self.events.append(event)

        # Sort by timestamp
        self.events.sort(key=lambda e: e.timestamp)

        if self.events:
            # Calculate relative times from first event
            self.start_time = self.events[0].timestamp
            self.end_time = self.events[-1].timestamp
        self.duration = self.end_time - self.start_time

    @staticmethod
    def _chain_first(first_row: List[str], rest: Iterator[List[str]]) -> Iterator[List[str]]:
        yield first_row
        yield from rest

    @staticmethod
    def _detect_header(first_row: List[str]) -> dict | None:
        normalized = [col.strip().lower() for col in first_row]
        expected = ['timestamp', 'deviceid', 'signal', 'value']
        if normalized[:4] == expected:
            return {name: idx for idx, name in enumerate(expected)}
        return None

    @staticmethod
    def _parse_timestamp(value: str) -> datetime:
        for fmt in ('%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d %H:%M:%S'):
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue
        raise ValueError(f"Unsupported timestamp format: {value}")

    @staticmethod
    def _convert_value(value: str):
        for caster in (int, float):
            try:
                return caster(value)
            except ValueError:
                continue
        return value

    def get_next_event(self) -> SignalEvent | None:
        """Get the next event to play."""
        if self.current_index >= len(self.events):
            return None
        event = self.events[self.current_index]
        self.current_index += 1
        return event

    def get_delay_to_next(self) -> float:
        """Get delay in milliseconds to next event."""
        if self.current_index >= len(self.events):
            return 0

        prev_event = self.events[self.current_index - 1]
        next_event = self.events[self.current_index]
        delay_sec = (next_event.timestamp - prev_event.timestamp) / self.playback_speed
        return delay_sec * 1000  # Convert to ms

    def reset(self):
        """Reset playback to the beginning."""
        self.current_index = 0

    def has_more(self) -> bool:
        """Check if there are more events to play."""
        return self.current_index < len(self.events)

    def progress(self) -> float:
        """Get playback progress as a fraction (0.0 to 1.0)."""
        if not self.events:
            return 0.0
        return self.current_index / len(self.events)


class PlaybackWindow(QMainWindow):
    """Main window with signal playback controls."""

    def __init__(self, xml_path: str, csv_path: str, yaml_cfg: str):
        super().__init__()
        self.setWindowTitle("Map Viewer - Signal Playback Demo")
        self.resize(1200, 800)

        # UI
        self.renderer = MapRenderer()
        self.setCentralWidget(self.renderer)

        # Parser → renders static layout
        self.parser = MapParser()
        self.parser.objectsParsed.connect(self.renderer.set_objects)
        objects = self.parser.parse_file(xml_path)

        # Device→Unit + Color rules → State model → Renderer color updates
        device_map, color_policy = load_mapping_and_policy(yaml_cfg)
        self.state_model = UnitStateModel(device_map, color_policy)
        self.state_model.stateChanged.connect(self.renderer.update_rect_color_by_unit)

        # Signal player
        self.player = SignalPlayer(csv_path, self.state_model)

        # Media controls dock
        self._build_media_dock()
        self._build_status_dock()

        # Playback timer
        self.playback_timer = QTimer(self)
        self.playback_timer.timeout.connect(self._play_next_event)

        # Update status
        self._update_status()

        # Wire up controls
        self.media_controls.btn_play.clicked.connect(self._toggle_play)
        self.media_controls.btn_back_10s.clicked.connect(self._restart)
        self.media_controls.cmb_speed.currentTextChanged.connect(self._on_speed_changed)
        self.media_controls.media_slider.sliderMoved.connect(self._on_slider_moved)

    def _build_media_dock(self):
        """Create media controls dock."""
        dock = QDockWidget(self)
        dock.setObjectName("MediaPlayerDock")
        dock.setAllowedAreas(Qt.DockWidgetArea.BottomDockWidgetArea)
        dock.setTitleBarWidget(QWidget(dock))  # hide title bar

        self.media_controls = MediaControls(dock)
        self.media_controls.btn_play.setText("▶ Play")
        self.media_controls.btn_back_10s.setText("⟲ Restart")
        self.media_controls.btn_fwd_10s.setVisible(False)  # Not implemented
        self.media_controls.txt_time.setVisible(False)  # Not implemented

        dock.setWidget(self.media_controls)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, dock)

    def _build_status_dock(self):
        """Create status display dock."""
        dock = QDockWidget("Playback Status", self)
        dock.setObjectName("StatusDock")
        dock.setAllowedAreas(Qt.DockWidgetArea.TopDockWidgetArea)

        status_widget = QWidget()
        layout = QVBoxLayout(status_widget)

        self.status_label = QLabel("Ready to play")
        self.status_label.setStyleSheet("""
            QLabel {
                padding: 10px;
                font-size: 12pt;
                background-color: #f5f5f5;
                border: 1px solid #ccc;
                border-radius: 4px;
            }
        """)
        layout.addWidget(self.status_label)

        dock.setWidget(status_widget)
        self.addDockWidget(Qt.DockWidgetArea.TopDockWidgetArea, dock)

    def _toggle_play(self):
        """Toggle play/pause."""
        if self.player.is_playing:
            self._pause()
        else:
            self._play()

    def _play(self):
        """Start playback."""
        if not self.player.has_more():
            self.player.reset()

        self.player.is_playing = True
        self.media_controls.btn_play.setText("⏸ Pause")
        self._play_next_event()

    def _pause(self):
        """Pause playback."""
        self.player.is_playing = False
        self.playback_timer.stop()
        self.media_controls.btn_play.setText("▶ Play")
        self._update_status()

    def _restart(self):
        """Restart playback from the beginning."""
        was_playing = self.player.is_playing
        self._pause()
        self.player.reset()
        self._update_status()
        if was_playing:
            self._play()

    def _play_next_event(self):
        """Play the next event in the sequence."""
        if not self.player.has_more():
            self._pause()
            self.status_label.setText("✓ Playback complete")
            self.media_controls.media_slider.setValue(100)
            return

        # Get and send next event
        event = self.player.get_next_event()
        if event:
            self.state_model.on_signal(event)

        # Update UI
        self._update_status()

        # Schedule next event
        if self.player.has_more():
            delay = self.player.get_delay_to_next()
            self.playback_timer.start(int(delay))

    def _update_status(self):
        """Update status display."""
        total = len(self.player.events)
        current = self.player.current_index
        progress = self.player.progress() * 100

        if self.player.is_playing:
            status = f"▶ Playing: {current}/{total} events ({progress:.1f}%)"
        elif current >= total:
            status = f"✓ Complete: {total} events"
        elif current > 0:
            status = f"⏸ Paused: {current}/{total} events ({progress:.1f}%)"
        else:
            status = f"Ready: {total} events loaded"

        self.status_label.setText(status)

        # Update slider
        self.media_controls.media_slider.setMaximum(100)
        self.media_controls.media_slider.setValue(int(progress))

        # Update time label
        if self.player.duration > 0:
            current_time = (current / total) * self.player.duration if total > 0 else 0
            self.media_controls.lbl_current_time.setText(
                f"{current_time:.1f}s / {self.player.duration:.1f}s"
            )

    def _on_speed_changed(self, speed_text: str):
        """Handle playback speed change."""
        try:
            speed = float(speed_text.replace('×', ''))
            self.player.playback_speed = speed
        except ValueError:
            pass

    def _on_slider_moved(self, position: int):
        """Handle slider position change."""
        # Seek to position
        target_index = int((position / 100.0) * len(self.player.events))
        self.player.current_index = max(0, min(target_index, len(self.player.events) - 1))
        self._update_status()


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")

    parser = argparse.ArgumentParser(
        description='Playback demo for map viewer',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        '--map',
        type=Path,
        default=Path('test_map.xml'),
        help='Path to XML map file (default: test_map.xml)'
    )

    parser.add_argument(
        '--signals',
        type=Path,
        default=Path('test_signals.csv'),
        help='Path to CSV signal file (default: test_signals.csv)'
    )

    parser.add_argument(
        '--config',
        type=Path,
        default=Path(__file__).parent / 'mappings_and_rules.yaml',
        help='Path to YAML config file (default: mappings_and_rules.yaml)'
    )

    parser.add_argument(
        '--speed',
        type=float,
        default=1.0,
        help='Initial playback speed (default: 1.0)'
    )

    args = parser.parse_args()
    script_dir = Path(__file__).parent
    args.map = _resolve_resource(args.map, script_dir)
    args.signals = _resolve_resource(args.signals, script_dir)
    args.config = _resolve_resource(args.config, script_dir)

    # Check files exist
    if not args.map.exists():
        print(f"Error: Map file not found: {args.map}")
        print("\nGenerate test data first:")
        print("  python generate_test_data.py")
        sys.exit(1)

    if not args.signals.exists():
        print(f"Error: Signal file not found: {args.signals}")
        print("\nGenerate test data first:")
        print("  python generate_test_data.py")
        sys.exit(1)

    if not args.config.exists():
        print(f"Error: Config file not found: {args.config}")
        sys.exit(1)

    app = QApplication(sys.argv)
    window = PlaybackWindow(
        xml_path=str(args.map),
        csv_path=str(args.signals),
        yaml_cfg=str(args.config)
    )

    # Set initial speed
    speed_text = f"{args.speed}×"
    index = window.media_controls.cmb_speed.findText(speed_text)
    if index >= 0:
        window.media_controls.cmb_speed.setCurrentIndex(index)

    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
