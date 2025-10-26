"""Dialog for selecting a device and signal combination."""

from __future__ import annotations

from collections import defaultdict
from typing import Dict, Iterable, List

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from plc_visualizer.utils import SignalData
from ..theme import (
    MUTED_TEXT,
    SURFACE_BG,
    apply_primary_button_style,
    apply_secondary_button_style,
    card_panel_styles,
    create_header_bar,
    surface_stylesheet,
)


class SignalSelectionDialog(QDialog):
    """Dialog that splits signal selection into device and signal dropdowns."""

    def __init__(
        self,
        signal_data_list: Iterable[SignalData],
        parent: QDialog | None = None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Select Signal to Plot")
        self.resize(420, 180)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {SURFACE_BG};
            }}
        """)

        self._signals_by_device: Dict[str, List[SignalData]] = defaultdict(list)
        for signal in signal_data_list:
            self._signals_by_device[signal.device_id].append(signal)

        for signal_list in self._signals_by_device.values():
            signal_list.sort(key=lambda sig: sig.name.lower())

        self._device_ids = sorted(self._signals_by_device.keys(), key=str.lower)
        self._selected_key: str | None = None

        self._device_combo = QComboBox(self)
        self._signal_combo = QComboBox(self)

        self._build_ui()
        self._populate_devices()
        self._device_combo.currentIndexChanged.connect(self._populate_signals)

    @property
    def selected_key(self) -> str | None:
        """Return the fully qualified signal key."""
        return self._selected_key

    def accept(self) -> None:
        current_data = self._signal_combo.currentData()
        self._selected_key = current_data if isinstance(current_data, str) else None
        super().accept()

    # Internal helpers -------------------------------------------------
    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = create_header_bar(
            "Select Signal",
            "Choose a device and signal to open interval plots.",
        )
        layout.addWidget(header)

        content = QWidget()
        content.setObjectName("SignalSelectionContent")
        content.setStyleSheet(surface_stylesheet("SignalSelectionContent"))
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(16, 16, 16, 16)
        content_layout.setSpacing(12)
        layout.addWidget(content, stretch=1)

        intro = QLabel("Choose the device first, then pick a signal to plot.")
        intro.setWordWrap(True)
        intro.setStyleSheet(f"color: {MUTED_TEXT};")
        content_layout.addWidget(intro)

        form_card = QWidget()
        form_card.setObjectName("SignalSelectionCard")
        form_card.setStyleSheet(card_panel_styles("SignalSelectionCard"))
        form = QFormLayout(form_card)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        form.setFormAlignment(Qt.AlignmentFlag.AlignTop)
        form.setSpacing(10)
        form.addRow("Device:", self._device_combo)
        form.addRow("Signal:", self._signal_combo)
        content_layout.addWidget(form_card)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        ok_btn = buttons.button(QDialogButtonBox.StandardButton.Ok)
        cancel_btn = buttons.button(QDialogButtonBox.StandardButton.Cancel)
        if ok_btn is not None:
            apply_primary_button_style(ok_btn)
        if cancel_btn is not None:
            apply_secondary_button_style(cancel_btn)
        content_layout.addWidget(buttons)

    def _populate_devices(self) -> None:
        self._device_combo.clear()
        for device_id in self._device_ids:
            self._device_combo.addItem(device_id, device_id)
        self._populate_signals()

    def _populate_signals(self) -> None:
        self._signal_combo.blockSignals(True)
        self._signal_combo.clear()

        current_device = self._device_combo.currentData()
        signals = self._signals_by_device.get(current_device, [])

        for signal in signals:
            label = signal.name or signal.key
            self._signal_combo.addItem(label, signal.key)

        self._signal_combo.blockSignals(False)

        # If there were no devices/signals, ensure selection resets
        if self._signal_combo.count() == 0:
            self._selected_key = None
        else:
            self._signal_combo.setCurrentIndex(0)
