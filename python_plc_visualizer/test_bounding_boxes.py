#!/usr/bin/env python3
"""Visualize the actual bounding boxes being used."""

import sys
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent))

from PyQt6.QtWidgets import QApplication, QGraphicsView, QGraphicsScene
from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QPen, QColor

from plc_visualizer.ui.signal_label_item import SignalLabelItem
from plc_visualizer.ui.signal_item import SignalItem
from plc_visualizer.models import SignalType
from plc_visualizer.utils import SignalData, SignalState

# Create test data
start_time = datetime(2024, 1, 1, 10, 30, 45)
end_time = datetime(2024, 1, 1, 10, 31, 1)

signal_data = SignalData(
    name="TEST_SIGNAL",
    device_id="DEVICE_1",
    key="DEVICE_1::TEST_SIGNAL",
    signal_type=SignalType.BOOLEAN,
    entries=[],
    states=[
        SignalState(start_time, start_time + timedelta(seconds=5), True),
        SignalState(start_time + timedelta(seconds=5), end_time, False),
    ]
)

app = QApplication(sys.argv)

# Create scene
scene = QGraphicsScene()

# Create label item
label = SignalLabelItem("DEVICE_1", "TEST_SIGNAL")
label.setPos(0, 50)  # Position at y=50
scene.addItem(label)

# Create waveform item
waveform = SignalItem(signal_data, (start_time, end_time), 500)
waveform.setPos(180, 50)  # Position at x=label width, y=50
scene.addItem(waveform)

# Draw debug boxes around bounding rects
pen = QPen(QColor(255, 0, 0), 3)  # Red, thick pen

# Label bounding box
label_rect = label.mapToScene(label.boundingRect()).boundingRect()
label_box = scene.addRect(label_rect, pen)
label_box.setZValue(100)  # Draw on top

# Waveform bounding box
waveform_rect = waveform.mapToScene(waveform.boundingRect()).boundingRect()
waveform_box = scene.addRect(waveform_rect, pen)
waveform_box.setZValue(100)  # Draw on top

# Create view
view = QGraphicsView(scene)
view.setRenderHint(view.renderHints() | view.renderHints().Antialiasing)
view.setWindowTitle("Bounding Box Debug View")
view.resize(800, 200)
view.show()

print("="*70)
print("BOUNDING BOX DEBUG")
print("="*70)
print()
print(f"Label position: {label.pos()}")
print(f"Label boundingRect: {label.boundingRect()}")
print(f"Label scene rect: {label_rect}")
print()
print(f"Waveform position: {waveform.pos()}")
print(f"Waveform boundingRect: {waveform.boundingRect()}")
print(f"Waveform scene rect: {waveform_rect}")
print()
print("Red boxes show the actual bounding rectangles")
print("Gray area = label, White area = waveform")
print()
print("If they're separate, you should see:")
print("  - Gray box from x=0 to x=180")
print("  - White box from x=180 to x=680")
print("="*70)

sys.exit(app.exec())
