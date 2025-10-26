"""Signal interval dialog with radio buttons, percentile-based autoscaling, and time-window binning.

Features
- Modes:
    • Change → change (original)
    • True pulse width (rising → falling)
    • Custom token pattern: tokenA → tokenB (case-insensitive)
- Plot:
    • Time-window binning: choose a fixed bin duration (seconds); all intervals whose *start* falls in the window are aggregated
    • Mean-per-bin line (+ optional min–max band)
    • Y-axis autoscale = [floor_percentile .. cap_percentile] (not forced to start at zero)
    • Set cap to 100 to disable clipping
    • Tooltips per bin (count, min/mean/max, time window)
- Call site:
    dialog = SignalIntervalDialog(signal_data, parent)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Iterable, List, Optional, Tuple

from PySide6.QtCore import Qt, QRectF, QSize, QPointF, QSignalBlocker
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QPolygonF
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QRadioButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QToolTip,
    QVBoxLayout,
    QWidget,
)

# ----- Project model type -----
from plc_visualizer.utils import SignalData


# =========================
# Data + builders
# =========================

@dataclass
class IntervalPoint:
    index: int
    start: datetime
    end: datetime
    duration_seconds: float
    from_value: object
    to_value: object


def _bool_like(v: object) -> Optional[bool]:
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return bool(v)
    if isinstance(v, str):
        s = v.strip().lower()
        if s in ("1", "true", "t", "on", "high"):
            return True
        if s in ("0", "false", "f", "off", "low"):
            return False
    return None


def build_change_to_change(signal_data: SignalData) -> List[IntervalPoint]:
    states = signal_data.states or []
    if len(states) < 2:
        return []
    points: List[IntervalPoint] = []
    for index, (cur, nxt) in enumerate(zip(states[:-1], states[1:]), start=1):
        dur = max(0.0, (nxt.start_time - cur.start_time).total_seconds())
        points.append(IntervalPoint(
            index=index,
            start=cur.start_time,
            end=nxt.start_time,
            duration_seconds=dur,
            from_value=cur.value,
            to_value=nxt.value,
        ))
    return points


def build_true_pulse_intervals(
    signal_data: SignalData,
    *,
    require_falling_edge: bool = True,
    min_high: Optional[float] = None,
) -> List[IntervalPoint]:
    """Measure HIGH time from rising (LOW->HIGH) to next falling (HIGH->LOW)."""
    states = signal_data.states or []
    if not states:
        return []

    def is_high(v: object) -> bool:
        b = _bool_like(v)
        if b is not None:
            return b
        return str(v).strip().lower() in ("1", "true", "on", "high", "t")

    out: List[IntervalPoint] = []
    pending_i: Optional[int] = None
    idx = 1

    for i, st in enumerate(states):
        cur_h = is_high(st.value)
        prev_h = is_high(states[i - 1].value) if i > 0 else None

        # rising edge
        if cur_h and (prev_h is False or (i == 0 and pending_i is None)):
            pending_i = i

        # falling edge completes pulse
        if pending_i is not None and (not cur_h) and (i > 0 and prev_h is True):
            start_t = states[pending_i].start_time
            end_t = st.start_time
            dur = max(0.0, (end_t - start_t).total_seconds())
            if (min_high is None) or (dur >= min_high):
                out.append(IntervalPoint(
                    index=idx, start=start_t, end=end_t,
                    duration_seconds=dur, from_value=True, to_value=False
                ))
                idx += 1
            pending_i = None

    # trailing HIGH without falling edge
    if pending_i is not None and not require_falling_edge:
        start_t = states[pending_i].start_time
        end_t = states[-1].start_time
        dur = max(0.0, (end_t - start_t).total_seconds())
        if (min_high is None) or (dur >= min_high):
            out.append(IntervalPoint(
                index=idx, start=start_t, end=end_t,
                duration_seconds=dur, from_value=True, to_value=None
            ))

    return out


def build_token_pattern(
    signal_data: SignalData,
    start_token: str,
    end_token: str,
    *,
    require_end: bool = True
) -> List[IntervalPoint]:
    """Measure time from any state whose string value matches start_token (case-insensitive)
    to the next state that matches end_token."""
    stoken = start_token.strip().lower()
    etoken = end_token.strip().lower()
    states = signal_data.states or []
    if not states or not stoken or not etoken:
        return []

    def match_s(v: object) -> bool:
        return stoken == str(v).strip().lower()

    def match_e(v: object) -> bool:
        return etoken == str(v).strip().lower()

    out: List[IntervalPoint] = []
    pending_i: Optional[int] = None
    idx = 1

    for i, st in enumerate(states):
        if pending_i is None:
            if match_s(st.value):
                pending_i = i
        else:
            if match_e(st.value):
                start_t = states[pending_i].start_time
                end_t = st.start_time
                dur = max(0.0, (end_t - start_t).total_seconds())
                out.append(IntervalPoint(
                    index=idx, start=start_t, end=end_t,
                    duration_seconds=dur, from_value=states[pending_i].value, to_value=st.value
                ))
                idx += 1
                pending_i = None

    if pending_i is not None and not require_end:
        start_t = states[pending_i].start_time
        end_t = states[-1].start_time
        dur = max(0.0, (end_t - start_t).total_seconds())
        out.append(IntervalPoint(
            index=idx, start=start_t, end=end_t,
            duration_seconds=dur, from_value=states[pending_i].value, to_value=None
        ))

    return out


# =========================
# Plotting helpers
# =========================

def _format_seconds_brief(s: float) -> str:
    if s < 1e-3:
        return f"{s*1e6:.0f}µs"
    if s < 1:
        ms = s * 1e3
        return f"{ms:.0f}ms" if ms >= 10 else f"{ms:.1f}ms"
    if s < 60:
        return f"{s:.0f}s" if s >= 10 else f"{s:.1f}s"
    if s < 3600:
        m = s / 60.0
        return f"{m:.0f}m" if m >= 10 else f"{m:.1f}m"
    h = s / 3600.0
    return f"{h:.1f}h"


def _nice_tick_step(max_value: float, target_ticks: int = 5) -> float:
    if max_value <= 0:
        return 1.0
    raw = max_value / max(target_ticks, 1)
    import math
    exp = math.floor(math.log10(raw))
    base = raw / (10 ** exp)
    if base <= 1:
        nice = 1
    elif base <= 2:
        nice = 2
    elif base <= 5:
        nice = 5
    else:
        nice = 10
    return nice * (10 ** exp)


def _percentile(values: List[float], p: float, *, already_sorted: bool = False) -> float:
    if not values:
        return 0.0
    vals = values if already_sorted else sorted(values)
    if p <= 0:
        return vals[0]
    if p >= 1:
        return vals[-1]
    idx = p * (len(vals) - 1)
    lo = int(idx)
    hi = min(lo + 1, len(vals) - 1)
    frac = idx - lo
    return vals[lo] * (1 - frac) + vals[hi] * frac


def _fmt_ts_short(dt: datetime) -> str:
    # HH:MM:SS.mmm
    return dt.strftime("%H:%M:%S.%f")[:-3]


def _fmt_offset(start0: datetime, t: datetime) -> str:
    # +Xs style offset
    delta = (t - start0).total_seconds()
    sign = "+" if delta >= 0 else "-"
    return f"{sign}{_format_seconds_brief(abs(delta))}"


@dataclass
class _TBin:
    # time-window bin
    start_t: datetime
    end_t: datetime
    count: int
    min_v: float
    max_v: float
    sum_v: float

    @property
    def mean(self) -> float:
        return self.sum_v / max(self.count, 1)


class IntervalPlotWidget(QWidget):
    """
    High-density interval plot as a line (mean per time-window bin) with optional min–max band.

    Y-axis autoscale to [p_low .. p_high]:
        - floor_percentile (p_low) defaults to 0.0 (min)
        - cap_percentile   (p_high) defaults to 0.99 (P99); set to 1.0 to disable capping

    Binning:
        - Fixed window size (bin_duration_s). Each interval contributes to the bin of its *start* time.
    """

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        *,
        bin_duration_s: float = 0.1,  # 100 ms default
        cap_percentile: float = 0.99,
        floor_percentile: float = 0.0,
        show_band: bool = True,
    ):
        super().__init__(parent)
        self._intervals: List[IntervalPoint] = []
        self._durations: List[float] = []
        self._durations_sorted: List[float] = []
        self._points_sorted: List[IntervalPoint] = []
        self._t0: Optional[datetime] = None

        self._bin_duration_s = max(1e-9, float(bin_duration_s))
        self._cap_p = float(max(0.0, min(1.0, cap_percentile)))
        self._floor_p = float(max(0.0, min(1.0, floor_percentile)))
        self._show_band = show_band

        self._bins: List[_TBin] = []
        self._last_plot_rect: Optional[QRectF] = None

        # Current scale
        self._y_min: float = 0.0
        self._y_max: float = 1.0

        self.setMouseTracking(True)
        self.setMinimumSize(QSize(360, 260))

        # Palette
        self._axis_color = QColor("#90a4ae")
        self._grid_color = QColor("#cfd8dc")
        self._label_color = QColor("#607d8b")
        self._title_color = QColor("#37474f")
        self._line_color = QColor("#1e88e5")
        self._band_color = QColor("#42a5f5")
        self._outlier_color = QColor("#ef5350")

    # -------- Public API --------

    def set_intervals(self, intervals: Iterable[IntervalPoint]):
        """Accept intervals for the CURRENT MODE. Recomputes bins & Y-scale."""
        self._intervals = list(intervals)
        self._points_sorted = sorted(self._intervals, key=lambda p: p.start)
        self._durations = [p.duration_seconds for p in self._intervals]
        self._durations_sorted = sorted(self._durations)
        self._t0 = self._points_sorted[0].start if self._points_sorted else None
        self._update_scale(recompute_bins=True)
        self.update()

    def set_cap_percentile(self, cap_percentile: float):
        """0..1 inclusive; use 1.0 for no cap."""
        self._cap_p = float(max(0.0, min(1.0, cap_percentile)))
        self._update_scale(recompute_bins=False)
        self.update()

    def set_floor_percentile(self, floor_percentile: float):
        """0..1 inclusive; default 0.0 (min). Increases the lower baseline."""
        self._floor_p = float(max(0.0, min(1.0, floor_percentile)))
        self._update_scale(recompute_bins=False)
        self.update()

    def set_show_band(self, show: bool):
        self._show_band = bool(show)
        self.update()

    def set_bin_duration(self, seconds: float):
        """Set fixed bin window size (seconds)."""
        self._bin_duration_s = max(1e-9, float(seconds))
        self._update_scale(recompute_bins=True)
        self.update()

    # -------- QWidget overrides --------

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect()
        painter.fillRect(rect, self.palette().base())

        if not self._intervals or self._y_max <= self._y_min or not self._bins:
            painter.setPen(QColor("#546e7a"))
            painter.setFont(QFont("Arial", 11))
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "No transition intervals available for this signal.")
            return

        left_margin = 90
        right_margin = 24
        top_margin = 22
        bottom_margin = 64

        plot_rect = QRectF(
            left_margin,
            top_margin,
            max(0.0, rect.width() - left_margin - right_margin),
            max(0.0, rect.height() - top_margin - bottom_margin),
        )
        if plot_rect.width() <= 0 or plot_rect.height() <= 0:
            return

        y0, y1 = self._y_min, self._y_max

        axis_pen = QPen(self._axis_color); axis_pen.setWidth(1)
        grid_pen = QPen(self._grid_color); grid_pen.setStyle(Qt.PenStyle.DashLine)

        # Axes
        painter.setPen(axis_pen)
        painter.drawLine(plot_rect.bottomLeft(), plot_rect.bottomRight())
        painter.drawLine(plot_rect.bottomLeft(), plot_rect.topLeft())

        # Horizontal grid + labels (use "nice" steps within [y0..y1])
        label_font = QFont("Arial", 9)
        painter.setFont(label_font)
        step = _nice_tick_step(y1 - y0, target_ticks=5)
        tick = (y0 // step) * step  # start at a multiple ≤ y0
        if tick < y0:
            tick += step
        while tick <= y1 + 1e-12:
            y = self._map_y(tick, y0, y1, plot_rect)
            painter.setPen(grid_pen)
            painter.drawLine(QPointF(plot_rect.left(), y), QPointF(plot_rect.right(), y))
            painter.setPen(self._label_color)
            painter.drawText(
                QRectF(0, y - 8, left_margin - 10, 16),
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                _format_seconds_brief(tick),
            )
            tick += step

        # Floor / Cap lines
        painter.setPen(QPen(QColor("#b0bec5"), 1, Qt.PenStyle.DotLine))
        fy = self._map_y(y0, y0, y1, plot_rect)
        painter.drawLine(QPointF(plot_rect.left(), fy), QPointF(plot_rect.right(), fy))
        painter.setPen(self._label_color)
        painter.drawText(
            QRectF(plot_rect.left(), fy - 14, plot_rect.width(), 14),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            f"Floor ({int(self._floor_p*100)}th): {_format_seconds_brief(y0)}",
        )
        painter.setPen(QPen(QColor("#b0bec5"), 1, Qt.PenStyle.DotLine))
        cy = self._map_y(y1, y0, y1, plot_rect)
        painter.drawLine(QPointF(plot_rect.left(), cy), QPointF(plot_rect.right(), cy))
        painter.setPen(self._label_color)
        painter.drawText(
            QRectF(plot_rect.left(), cy - 14, plot_rect.width(), 14),
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
            f"Cap ({int(self._cap_p*100)}th): {_format_seconds_brief(y1)}",
        )

        # Geometry for bins
        n_bins = len(self._bins)
        spacing = plot_rect.width() / n_bins

        mean_pts = QPolygonF()
        upper_pts: List[QPointF] = []
        lower_pts: List[QPointF] = []
        outlier_bins: List[Tuple[float, bool]] = []

        for i, b in enumerate(self._bins):
            cx = plot_rect.left() + spacing * (i + 0.5)
            # clamp to [y0..y1] for plotting
            y_mean = self._map_y(min(max(b.mean, y0), y1), y0, y1, plot_rect)
            y_min = self._map_y(min(max(b.min_v, y0), y1), y0, y1, plot_rect)
            y_maxv = self._map_y(min(max(b.max_v, y0), y1), y0, y1, plot_rect)

            mean_pts.append(QPointF(cx, y_mean))
            upper_pts.append(QPointF(cx, y_min))
            lower_pts.append(QPointF(cx, y_maxv))
            outlier_bins.append((cx, b.max_v > y1))  # only flag above-cap

        # Min–max band
        if self._show_band and len(upper_pts) >= 2:
            band = QPolygonF()
            for p in upper_pts:
                band.append(p)
            for p in reversed(lower_pts):
                band.append(p)
            band_color = QColor(self._band_color)
            band_color.setAlpha(60)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(band_color)
            painter.drawPolygon(band)

        # Mean line
        painter.setBrush(Qt.BrushStyle.NoBrush)
        line_pen = QPen(self._line_color); line_pen.setWidth(2)
        painter.setPen(line_pen)
        if len(mean_pts) == 1:
            p = mean_pts[0]
            painter.drawEllipse(p, 2.5, 2.5)
        else:
            painter.drawPolyline(mean_pts)

        # Outlier markers (triangle at cap)
        out_pen = QPen(self._outlier_color); out_pen.setWidth(2)
        painter.setPen(out_pen)
        for cx, has_out in outlier_bins:
            if not has_out:
                continue
            tri_w = max(3.0, spacing * 0.15)
            y = cy
            pts = QPolygonF([QPointF(cx, y - tri_w), QPointF(cx - tri_w, y), QPointF(cx + tri_w, y)])
            painter.drawPolyline(pts)

        # X ticks (sparse, show time windows)
        painter.setPen(self._axis_color)
        painter.setFont(QFont("Arial", 9))
        x_tick_count = min(8, n_bins)
        if x_tick_count > 1:
            for j in range(x_tick_count):
                i = int(j * (n_bins - 1) / (x_tick_count - 1))
                b = self._bins[i]
                cx = plot_rect.left() + spacing * (i + 0.5)
                painter.drawLine(QPointF(cx, plot_rect.bottom()), QPointF(cx, plot_rect.bottom() + 4))
                painter.setPen(self._label_color)
                label = self._format_bin_label(b)
                painter.drawText(
                    QRectF(cx - 60, plot_rect.bottom() + 6, 120, 30),
                    Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
                    label,
                )
                painter.setPen(self._axis_color)

        # Axis titles
        painter.setPen(self._title_color)
        painter.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        painter.drawText(
            QRectF(plot_rect.left(), self.height() - 52 + 16, plot_rect.width(), 20),
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
            f"Time (bins of {_format_seconds_brief(self._bin_duration_s)})",
        )
        painter.save()
        painter.translate(18, plot_rect.center().y())
        painter.rotate(-90)
        painter.drawText(
            QRectF(-plot_rect.height() / 2, -18, plot_rect.height(), 20),
            Qt.AlignmentFlag.AlignCenter,
            "Duration",
        )
        painter.restore()

        self._last_plot_rect = plot_rect

    def mouseMoveEvent(self, event):
        if not self._bins or not self._last_plot_rect:
            return
        x = event.position().x()
        pr = self._last_plot_rect
        if x < pr.left() or x > pr.right():
            QToolTip.hideText()
            return
        n = len(self._bins)
        spacing = pr.width() / n
        i = int((x - pr.left()) / spacing)
        i = max(0, min(n - 1, i))
        b = self._bins[i]
        t0 = self._t0 or b.start_t
        tip = (
            f"Window: {_fmt_ts_short(b.start_t)} – {_fmt_ts_short(b.end_t)}  "
            f"({_fmt_offset(t0, b.start_t)} … {_fmt_offset(t0, b.end_t)})\n"
            f"Count: {b.count}\n"
            f"Min: {_format_seconds_brief(b.min_v)}  "
            f"Mean: {_format_seconds_brief(b.mean)}  "
            f"Max: {_format_seconds_brief(b.max_v)}"
        )
        QToolTip.showText(self.mapToGlobal(event.position().toPoint()), tip, self)

    # -------- Internals --------

    def _update_scale(self, *, recompute_bins: bool):
        # Y-range from current durations, based on percentiles
        if not self._durations:
            self._y_min, self._y_max = 0.0, 1.0
            if recompute_bins or self._bins:
                self._bins = []
            return

        durs_sorted = self._durations_sorted if self._durations_sorted else sorted(self._durations)
        lo = _percentile(durs_sorted, self._floor_p, already_sorted=True)
        hi = _percentile(durs_sorted, self._cap_p, already_sorted=True)
        if self._cap_p >= 1.0:
            hi = durs_sorted[-1]
        if hi <= lo:
            eps = max(1e-9, abs(hi) * 1e-6 + 1e-9)
            lo -= eps
            hi += eps
        pad = 0.04 * (hi - lo)
        self._y_min = lo - pad
        self._y_max = hi + pad

        if recompute_bins or not self._bins:
            self._bins = self._make_time_bins(self._points_sorted, self._bin_duration_s)

    def _map_y(self, value: float, y0: float, y1: float, rect: QRectF) -> float:
        if y1 <= y0:
            return rect.bottom()
        t = (value - y0) / (y1 - y0)
        t = max(0.0, min(1.0, t))
        return rect.bottom() - t * rect.height()

    def _make_time_bins(self, points: List[IntervalPoint], bin_dur_s: float) -> List[_TBin]:
        if not points:
            return []
        # sort by start (already sorted in set_intervals)
        start0 = points[0].start
        last_end = max((p.end for p in points), default=start0)
        total_span_s = max(0.0, (last_end - start0).total_seconds())
        if total_span_s == 0.0:
            # single timestamp — one bin
            return [self._make_bin_from_points(start0, start0 + timedelta(seconds=bin_dur_s), points)]

        import math
        n_bins = max(1, math.ceil(total_span_s / bin_dur_s))
        bins: List[_TBin] = []
        # initialize
        for i in range(n_bins):
            s = start0 + timedelta(seconds=i * bin_dur_s)
            e = s + timedelta(seconds=bin_dur_s)
            bins.append(_TBin(start_t=s, end_t=e, count=0, min_v=float("inf"), max_v=float("-inf"), sum_v=0.0))

        # assign by start time
        for p in points:
            idx = int(((p.start - start0).total_seconds()) // bin_dur_s)
            if idx < 0:
                idx = 0
            elif idx >= n_bins:
                idx = n_bins - 1  # clamp tail-edge
            b = bins[idx]
            v = p.duration_seconds
            b.count += 1
            b.sum_v += v
            if v < b.min_v: b.min_v = v
            if v > b.max_v: b.max_v = v

        # finalize infs for empty bins (set to previous non-empty or 0)
        prev_val = None
        for b in bins:
            if b.count == 0:
                if prev_val is not None:
                    b.min_v = b.max_v = b.sum_v = prev_val
                else:
                    b.min_v = b.max_v = b.sum_v = 0.0
            else:
                prev_val = b.mean

        return bins

    def _make_bin_from_points(self, s: datetime, e: datetime, pts: List[IntervalPoint]) -> _TBin:
        if not pts:
            return _TBin(start_t=s, end_t=e, count=0, min_v=0.0, max_v=0.0, sum_v=0.0)
        vals = [p.duration_seconds for p in pts]
        return _TBin(
            start_t=s, end_t=e,
            count=len(vals),
            min_v=min(vals), max_v=max(vals), sum_v=sum(vals)
        )

    def _format_bin_label(self, b: _TBin) -> str:
        # Prefer offsets from t0 (short). If unknown, show clock time.
        if self._t0 is not None:
            return f"{_fmt_offset(self._t0, b.start_t)} – {_fmt_offset(self._t0, b.end_t)}"
        return f"{_fmt_ts_short(b.start_t)}–{_fmt_ts_short(b.end_t)}"


# =========================
# Dialog (with radio buttons and time-window binning)
# =========================

class SignalIntervalDialog(QDialog):
    MAX_TABLE_ROWS = 5000
    """Dialog that presents interval statistics and a binned line plot with mode switches."""

    def __init__(self, signal_data: SignalData, parent: QWidget | None = None):
        # Guard: only parent QDialog if it's a QWidget; else None to avoid type errors
        qt_parent = parent if isinstance(parent, QWidget) else None
        super().__init__(qt_parent)

        self.signal_data = signal_data
        self._bin_duration_user_overridden = False

        self.setWindowTitle(f"Transition Intervals — {signal_data.display_label}")
        self.resize(980, 720)

        # --- Layout
        root = QVBoxLayout(self)

        desc = QLabel("Measure duration for different patterns and visualize with time-window binning.")
        desc.setWordWrap(True)
        root.addWidget(desc)

        # ---- Controls bar
        controls_box = QGroupBox("Measurement")
        controls_layout = QHBoxLayout(controls_box)

        # Radio group
        self.rb_change = QRadioButton("Change → change")
        self.rb_pulse = QRadioButton("True pulse width (↑→↓)")
        self.rb_custom = QRadioButton("Custom: token A → token B")
        self.rb_change.setChecked(True)

        radios_col = QVBoxLayout()
        radios_col.addWidget(self.rb_change)
        radios_col.addWidget(self.rb_pulse)
        radios_col.addWidget(self.rb_custom)
        controls_layout.addLayout(radios_col)

        # Custom pattern inputs
        form = QFormLayout()
        self.le_start = QLineEdit(); self.le_start.setPlaceholderText("e.g., ARMED")
        self.le_end = QLineEdit();   self.le_end.setPlaceholderText("e.g., FIRED")
        self.le_start.setEnabled(False)
        self.le_end.setEnabled(False)
        form.addRow("Start token:", self.le_start)
        form.addRow("End token:", self.le_end)
        controls_layout.addLayout(form)

        # Plot options
        opts_col = QVBoxLayout()

        # Show band
        self.cb_band = QCheckBox("Show min–max band"); self.cb_band.setChecked(True)
        opts_col.addWidget(self.cb_band)

        # Cap percentile
        cap_row = QHBoxLayout()
        cap_row.addWidget(QLabel("Cap percentile:"))
        self.sb_cap = QSpinBox()
        self.sb_cap.setRange(50, 100)  # 100 == no cap
        self.sb_cap.setValue(99)
        self.sb_cap.setSuffix("th")
        self.sb_cap.setToolTip("Set to 100 to disable capping (use full max).")
        cap_row.addWidget(self.sb_cap)
        cap_row.addStretch(1)
        opts_col.addLayout(cap_row)

        # Bin duration (seconds)
        bin_row = QHBoxLayout()
        bin_row.addWidget(QLabel("Bin duration:"))
        self.sb_bin_dur = QDoubleSpinBox()
        self.sb_bin_dur.setRange(1e-6, 3600.0)
        self.sb_bin_dur.setDecimals(6)
        self.sb_bin_dur.setSingleStep(0.001)
        self.sb_bin_dur.setValue(0.1)  # default 100 ms
        self.sb_bin_dur.setSuffix(" s")
        self.sb_bin_dur.setToolTip("Fixed time window size. All intervals whose *start* falls inside are aggregated.")
        bin_row.addWidget(self.sb_bin_dur)
        bin_row.addStretch(1)
        opts_col.addLayout(bin_row)

        controls_layout.addLayout(opts_col)
        root.addWidget(controls_box)

        # ---- Plot
        self.plot_widget = IntervalPlotWidget(
            self,
            bin_duration_s=self.sb_bin_dur.value(),
            cap_percentile=self.sb_cap.value() / 100.0,
            floor_percentile=0.0,      # axis will start at min by default (not zero)
            show_band=self.cb_band.isChecked(),
        )
        root.addWidget(self.plot_widget, stretch=1)

        # ---- Table
        self.table = QTableWidget(0, 5, self)
        self.table.setHorizontalHeaderLabels(["Change #", "From Value", "To Value", "Started At", "Interval (s)"])
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        root.addWidget(self.table, stretch=1)

        # ---- Buttons
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        btns.rejected.connect(self.reject)
        btns.accepted.connect(self.accept)
        root.addWidget(btns)

        # Wire events
        self.rb_change.toggled.connect(self._on_mode_changed)
        self.rb_pulse.toggled.connect(self._on_mode_changed)
        self.rb_custom.toggled.connect(self._on_mode_changed)
        self.cb_band.toggled.connect(lambda on: self.plot_widget.set_show_band(on))
        self.sb_cap.valueChanged.connect(self._on_cap_changed)
        self.sb_bin_dur.valueChanged.connect(self._on_bin_dur_changed)

        # Enable/disable custom inputs
        self.rb_custom.toggled.connect(self._toggle_custom_inputs)
        self.le_start.editingFinished.connect(self._rebuild_and_refresh)
        self.le_end.editingFinished.connect(self._rebuild_and_refresh)

        # initial build
        self._rebuild_and_refresh()

    # ------- UI handlers

    def _toggle_custom_inputs(self, checked: bool):
        self.le_start.setEnabled(checked)
        self.le_end.setEnabled(checked)

    def _on_cap_changed(self, val: int):
        self.plot_widget.set_cap_percentile(val / 100.0)

    def _on_bin_dur_changed(self, val: float):
        self._bin_duration_user_overridden = True
        self.plot_widget.set_bin_duration(val)

    def _on_mode_changed(self, _: bool):
        self._rebuild_and_refresh()

    # ------- Data / render

    def _rebuild_and_refresh(self):
        if self.rb_change.isChecked():
            intervals = build_change_to_change(self.signal_data)
        elif self.rb_pulse.isChecked():
            intervals = build_true_pulse_intervals(self.signal_data, require_falling_edge=True, min_high=None)
        else:
            start_token = self.le_start.text()
            end_token = self.le_end.text()
            intervals = build_token_pattern(self.signal_data, start_token=start_token, end_token=end_token, require_end=True)

        self._set_intervals(intervals)

    def _set_intervals(self, intervals: List[IntervalPoint]):
        # push to plot (this recomputes stats from CURRENT intervals)
        if intervals and not self._bin_duration_user_overridden:
            self._set_default_bin_duration(intervals)

        self.plot_widget.set_show_band(self.cb_band.isChecked())
        self.plot_widget.set_cap_percentile(self.sb_cap.value() / 100.0)
        self.plot_widget.set_bin_duration(self.sb_bin_dur.value())
        self.plot_widget.set_intervals(intervals)

        # Update table
        self._populate_table(intervals)

    @staticmethod
    def _format_timestamp(value: datetime) -> str:
        return value.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

    def _populate_table(self, intervals: List[IntervalPoint]):
        self.table.setUpdatesEnabled(False)
        try:
            self.table.clearContents()
            self.table.clearSpans()

            total = len(intervals)
            if total == 0:
                self.table.setRowCount(0)
                return

            max_rows = self.MAX_TABLE_ROWS
            if total > max_rows:
                head_count = max_rows // 2
                tail_count = max_rows - head_count
                display_rows: List[Optional[IntervalPoint]] = (
                    intervals[:head_count] + [None] + intervals[-tail_count:]
                )
            else:
                display_rows = list(intervals)

            self.table.setRowCount(len(display_rows))
            font_bold = QFont(); font_bold.setBold(True)

            for row, point in enumerate(display_rows):
                if point is None:
                    skipped = total - max_rows
                    ellipsis = QTableWidgetItem(f"… {skipped} intervals omitted for responsiveness …")
                    ellipsis.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    ellipsis.setFlags(Qt.ItemFlag.NoItemFlags)
                    ellipsis.setFont(font_bold)
                    self.table.setItem(row, 0, ellipsis)
                    self.table.setSpan(row, 0, 1, self.table.columnCount())
                    continue

                items = [
                    QTableWidgetItem(str(point.index)),
                    QTableWidgetItem(str(point.from_value)),
                    QTableWidgetItem(str(point.to_value)),
                    QTableWidgetItem(self._format_timestamp(point.start)),
                    QTableWidgetItem(f"{point.duration_seconds:.6f}"),
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

            if len(display_rows) <= 500:
                self.table.resizeColumnsToContents()
            self.table.scrollToTop()
        finally:
            self.table.setUpdatesEnabled(True)

    def _set_default_bin_duration(self, intervals: List[IntervalPoint]):
        starts = [point.start for point in intervals]
        if not starts:
            return

        min_start = min(starts)
        max_start = max(starts)
        span_seconds = max((max_start - min_start).total_seconds(), 0.0)

        if span_seconds <= 0:
            representative = intervals[0].duration_seconds if intervals else 0.0
            target_duration = max(representative, 1e-6)
        else:
            target_duration = span_seconds / 50.0

        target_duration = max(self.sb_bin_dur.minimum(), min(target_duration, self.sb_bin_dur.maximum()))

        blocker = QSignalBlocker(self.sb_bin_dur)
        self.sb_bin_dur.setValue(target_duration)
        del blocker
