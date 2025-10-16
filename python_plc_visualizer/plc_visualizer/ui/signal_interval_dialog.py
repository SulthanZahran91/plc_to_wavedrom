"""Dialog and plot for visualizing intervals between signal transitions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, List

from PyQt6.QtCore import Qt, QRectF, QSize, QPointF
from PyQt6.QtGui import QColor, QFont, QPainter, QPen
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from plc_visualizer.utils import SignalData


@dataclass
class IntervalPoint:
    """Represents the duration between successive value changes."""

    index: int
    start: datetime
    end: datetime
    duration_seconds: float
    from_value: object
    to_value: object


class IntervalPlotWidget(QWidget):
    """Simple bar chart widget for plotting transition intervals."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._intervals: List[IntervalPoint] = []
        self._max_duration: float = 0.0
        self.setMinimumSize(QSize(300, 240))

    def set_intervals(self, intervals: Iterable[IntervalPoint]):
        """Set the data to be displayed."""
        self._intervals = list(intervals)
        self._max_duration = max(
            (point.duration_seconds for point in self._intervals),
            default=0.0,
        )
        self.update()

    def paintEvent(self, event):  # noqa: D401 - QWidget override
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect()
        painter.fillRect(rect, self.palette().base())

        if not self._intervals or self._max_duration <= 0:
            painter.setPen(QColor("#546e7a"))
            painter.setFont(QFont("Arial", 11))
            painter.drawText(
                rect,
                Qt.AlignmentFlag.AlignCenter,
                "No transition intervals available for this signal.",
            )
            return

        left_margin = 70
        right_margin = 24
        top_margin = 24
        bottom_margin = 52

        plot_rect = QRectF(
            left_margin,
            top_margin,
            max(0.0, rect.width() - left_margin - right_margin),
            max(0.0, rect.height() - top_margin - bottom_margin),
        )

        if plot_rect.width() <= 0 or plot_rect.height() <= 0:
            return

        axis_pen = QPen(QColor("#90a4ae"))
        axis_pen.setWidth(1)

        # Axes
        painter.setPen(axis_pen)
        painter.drawLine(plot_rect.bottomLeft(), plot_rect.bottomRight())
        painter.drawLine(plot_rect.bottomLeft(), plot_rect.topLeft())

        # Horizontal grid lines and labels
        grid_pen = QPen(QColor("#cfd8dc"))
        grid_pen.setStyle(Qt.PenStyle.DashLine)
        label_font = QFont("Arial", 9)
        painter.setFont(label_font)

        steps = 4
        for step in range(steps + 1):
            value = (self._max_duration / steps) * step if steps else self._max_duration
            y = plot_rect.bottom() - (
                (value / self._max_duration) * plot_rect.height()
                if self._max_duration
                else 0.0
            )
            painter.setPen(grid_pen)
            painter.drawLine(
                QPointF(plot_rect.left(), y),
                QPointF(plot_rect.right(), y),
            )
            painter.setPen(QColor("#607d8b"))
            painter.drawText(
                QRectF(0, y - 8, left_margin - 6, 16),
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                f"{value:.2f}s",
            )

        # Bars
        bar_count = len(self._intervals)
        spacing = plot_rect.width() / max(bar_count, 1)
        bar_width = max(8.0, min(40.0, spacing * 0.6))
        bar_color = QColor("#42a5f5")
        text_font = QFont("Arial", 9, QFont.Weight.Medium)

        for idx, point in enumerate(self._intervals):
            center_x = plot_rect.left() + spacing * idx + spacing / 2
            bar_height = (
                (point.duration_seconds / self._max_duration) * plot_rect.height()
                if self._max_duration
                else 0.0
            )
            bar_rect = QRectF(
                center_x - bar_width / 2,
                plot_rect.bottom() - bar_height,
                bar_width,
                bar_height,
            )

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(bar_color)
            painter.drawRoundedRect(bar_rect, 3, 3)

            # Duration label above bar
            painter.setFont(text_font)
            painter.setPen(QColor("#37474f"))
            label_rect = QRectF(
                center_x - bar_width,
                max(plot_rect.top(), bar_rect.top() - 22),
                bar_width * 2,
                20,
            )
            painter.drawText(
                label_rect,
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom,
                f"{point.duration_seconds:.2f}s",
            )

            # X-axis tick labels
            painter.setPen(QColor("#455a64"))
            tick_rect = QRectF(
                center_x - bar_width,
                plot_rect.bottom() + 6,
                bar_width * 2,
                18,
            )
            painter.drawText(
                tick_rect,
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
                str(point.index),
            )

        # Axis titles
        painter.setPen(QColor("#37474f"))
        painter.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        painter.drawText(
            QRectF(plot_rect.left(), rect.height() - bottom_margin + 16, plot_rect.width(), 20),
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
            "Change Index",
        )

        painter.save()
        painter.translate(18, plot_rect.center().y())
        painter.rotate(-90)
        painter.drawText(
            QRectF(
                -plot_rect.height() / 2,
                -18,
                plot_rect.height(),
                20,
            ),
            Qt.AlignmentFlag.AlignCenter,
            "Duration (seconds)",
        )
        painter.restore()


class SignalIntervalDialog(QDialog):
    """Dialog that presents interval statistics and a simple plot."""

    def __init__(self, signal_data: SignalData, parent: QWidget | None = None):
        super().__init__(parent)
        self.signal_data = signal_data
        self.intervals = self._build_interval_points(signal_data)

        self.setWindowTitle(f"Transition Intervals — {signal_data.display_label}")
        self.resize(820, 620)

        layout = QVBoxLayout(self)

        description = QLabel(
            "Duration measured between successive value changes for the selected signal."
        )
        description.setWordWrap(True)
        description.setStyleSheet("color: #455a64; padding-bottom: 4px;")
        layout.addWidget(description)

        self.plot_widget = IntervalPlotWidget(self)
        self.plot_widget.set_intervals(self.intervals)
        layout.addWidget(self.plot_widget, stretch=1)

        self.table = QTableWidget(len(self.intervals), 5, self)
        self.table.setHorizontalHeaderLabels([
            "Change #",
            "From Value",
            "To Value",
            "Started At",
            "Interval (s)",
        ])
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table, stretch=1)

        self._populate_table()

        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        button_box.rejected.connect(self.reject)
        button_box.accepted.connect(self.accept)
        layout.addWidget(button_box)

    @staticmethod
    def _format_timestamp(value: datetime) -> str:
        return value.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

    def _populate_table(self):
        font_bold = QFont()
        font_bold.setBold(True)

        for row, point in enumerate(self.intervals):
            items = [
                QTableWidgetItem(str(point.index)),
                QTableWidgetItem(str(point.from_value)),
                QTableWidgetItem(str(point.to_value)),
                QTableWidgetItem(self._format_timestamp(point.start)),
                QTableWidgetItem(f"{point.duration_seconds:.3f}"),
            ]

            for col, item in enumerate(items):
                if col == 0:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    item.setFont(font_bold)
                elif col == 4:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                else:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                self.table.setItem(row, col, item)

        self.table.resizeColumnsToContents()

    @staticmethod
    def _build_interval_points(signal_data: SignalData) -> List[IntervalPoint]:
        """Convert SignalData states into interval points for plotting."""
        states = signal_data.states or []
        if len(states) < 2:
            return []

        points: List[IntervalPoint] = []
        for index, (current, nxt) in enumerate(zip(states[:-1], states[1:]), start=1):
            duration = max(0.0, (nxt.start_time - current.start_time).total_seconds())
            points.append(
                IntervalPoint(
                    index=index,
                    start=current.start_time,
                    end=nxt.start_time,
                    duration_seconds=duration,
                    from_value=current.value,
                    to_value=nxt.value,
                )
            )
        return points
