"""Signal filtering controls for waveform and data table."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Set

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QComboBox,
    QPushButton,
    QCheckBox,
    QSpacerItem,
    QSizePolicy,
    QInputDialog,
    QTreeWidget,
    QTreeWidgetItem,
)

from plc_visualizer.models import SignalType
from plc_visualizer.utils import SignalData


@dataclass(frozen=True)
class SignalInfo:
    """Summary information about a signal for filtering."""

    device_id: str
    name: str
    key: str
    signal_type: SignalType
    has_changes: bool


class SignalFilterWidget(QWidget):
    """Widget providing rich filtering controls for signals."""

    visible_signals_changed = pyqtSignal(list)

    DEBOUNCE_MS = 200

    def __init__(self, parent=None):
        super().__init__(parent)

        self._signals: List[SignalInfo] = []
        self._filtered_signals: List[SignalInfo] = []
        self._selected_signals: Set[str] = set()
        self._signals_by_device: Dict[str, List[SignalInfo]] = {}
        self._filtered_tree: Dict[str, List[SignalInfo]] = {}
        self._selected_devices: Set[str] = set()
        self._search_query: str = ""
        self._pending_search: str = ""
        self._show_only_changed: bool = False
        self._type_filters: Set[SignalType] = {
            SignalType.BOOLEAN,
            SignalType.STRING,
            SignalType.INTEGER,
        }
        self._presets: Dict[str, dict] = {}
        self._updating_list = False

        self._debounce_timer = QTimer(self)
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.timeout.connect(self._apply_search_query)

        self._init_ui()
        self.setEnabled(False)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        title = QLabel("Signal Filters")
        title.setStyleSheet("font-size: 16px; font-weight: bold; padding: 5px;")
        layout.addWidget(title)

        # Search bar
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search devices or signals (use /regex for patterns)")
        self.search_input.textChanged.connect(self._on_search_changed)
        layout.addWidget(self.search_input)

        # Type filters
        type_layout = QHBoxLayout()
        type_layout.setSpacing(12)

        self.type_checkboxes: Dict[SignalType, QCheckBox] = {}
        for signal_type, label in [
            (SignalType.BOOLEAN, "Boolean"),
            (SignalType.STRING, "String"),
            (SignalType.INTEGER, "Integer"),
        ]:
            checkbox = QCheckBox(label)
            checkbox.setChecked(True)
            checkbox.toggled.connect(self._on_type_filter_changed)
            self.type_checkboxes[signal_type] = checkbox
            type_layout.addWidget(checkbox)

        type_layout.addStretch()
        layout.addLayout(type_layout)

        # Show only changed toggle
        self.changed_checkbox = QCheckBox("Show only signals with changes")
        self.changed_checkbox.toggled.connect(self._on_changed_toggled)
        layout.addWidget(self.changed_checkbox)

        # Preset controls
        preset_layout = QHBoxLayout()
        preset_layout.setSpacing(6)

        self.preset_combo = QComboBox()
        self.preset_combo.addItem("Load preset…")
        self.preset_combo.currentIndexChanged.connect(self._on_preset_selected)
        preset_layout.addWidget(self.preset_combo, stretch=1)

        self.save_preset_btn = QPushButton("Save Preset")
        self.save_preset_btn.clicked.connect(self._on_save_preset)
        preset_layout.addWidget(self.save_preset_btn)

        layout.addLayout(preset_layout)

        # Action buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(6)

        self.select_all_btn = QPushButton("Select All")
        self.select_all_btn.clicked.connect(self._on_select_all)
        button_layout.addWidget(self.select_all_btn)

        self.deselect_all_btn = QPushButton("Deselect All")
        self.deselect_all_btn.clicked.connect(self._on_deselect_all)
        button_layout.addWidget(self.deselect_all_btn)

        clear_btn = QPushButton("Clear Filters")
        clear_btn.clicked.connect(self._on_clear_filters)
        button_layout.addWidget(clear_btn)

        button_layout.addItem(QSpacerItem(
            0,
            0,
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Minimum
        ))
        layout.addLayout(button_layout)

        # Signal list
        self.signal_tree = QTreeWidget()
        self.signal_tree.setHeaderHidden(True)
        self.signal_tree.setUniformRowHeights(True)
        self.signal_tree.itemChanged.connect(self._on_tree_item_changed)
        layout.addWidget(self.signal_tree, stretch=1)

        # Status / count label
        self.count_label = QLabel("Showing 0 of 0 signals")
        self.count_label.setStyleSheet("padding: 4px; font-size: 11px; color: #666;")
        layout.addWidget(self.count_label)

    # Public API ---------------------------------------------------------
    def set_signals(self, signal_data: List[SignalData]):
        """Populate the filter with available signals."""
        self._signals = [
            SignalInfo(
                device_id=data.device_id,
                name=data.name,
                key=data.key,
                signal_type=data.signal_type,
                has_changes=data.has_transitions,
            )
            for data in signal_data
        ]
        self._signals_by_device = {}
        for info in self._signals:
            self._signals_by_device.setdefault(info.device_id, []).append(info)

        for signals in self._signals_by_device.values():
            signals.sort(key=lambda info: info.name.lower())

        self._selected_signals = {info.key for info in self._signals}
        self._selected_devices = set(self._signals_by_device.keys())
        self._presets.clear()
        self._reset_preset_combo()
        self.setEnabled(bool(self._signals))
        self._on_clear_filters()

    def clear(self):
        """Reset the widget."""
        self._signals = []
        self._filtered_signals = []
        self._selected_signals.clear()
        self._signals_by_device.clear()
        self._selected_devices.clear()
        self.signal_tree.clear()
        self._presets.clear()
        self._reset_preset_combo()
        self.count_label.setText("Showing 0 of 0 signals")
        self.count_label.setStyleSheet("padding: 4px; font-size: 11px; color: #666;")
        self.setEnabled(False)

    # Internal helpers ---------------------------------------------------
    def _apply_filters(self):
        """Apply search and filter criteria to update the signal list."""
        filtered_tree: Dict[str, List[SignalInfo]] = {}
        query = self._search_query.strip()
        regex = None
        use_regex = False

        if query.startswith("/") and len(query) > 1:
            pattern = query[1:]
            try:
                regex = re.compile(pattern, re.IGNORECASE)
                use_regex = True
            except re.error:
                regex = None
                use_regex = False

        for device_id, signals in self._signals_by_device.items():
            for info in signals:
                if info.signal_type not in self._type_filters:
                    continue

                if self._show_only_changed and not info.has_changes:
                    continue

                search_target = f"{info.device_id} {info.name}"

                if query:
                    if use_regex and regex:
                        if not regex.search(search_target):
                            continue
                    else:
                        if query.lower() not in search_target.lower():
                            continue

                filtered_tree.setdefault(device_id, []).append(info)

        # Ensure device order is consistent and signals sorted
        for device_id in filtered_tree:
            filtered_tree[device_id].sort(key=lambda info: info.name.lower())

        self._filtered_tree = filtered_tree
        self._filtered_signals = [info for infos in filtered_tree.values() for info in infos]
        self._refresh_tree()
        self._emit_visible_signals()

    def _refresh_tree(self):
        """Refresh tree widget items after filtering."""
        self._updating_list = True
        self.signal_tree.clear()

        for device_id in sorted(self._filtered_tree.keys()):
            signals = self._filtered_tree[device_id]

            device_item = QTreeWidgetItem([device_id])
            device_item.setFlags(
                Qt.ItemFlag.ItemIsEnabled
                | Qt.ItemFlag.ItemIsSelectable
                | Qt.ItemFlag.ItemIsUserCheckable
                | Qt.ItemFlag.ItemIsAutoTristate
            )
            device_item.setData(0, Qt.ItemDataRole.UserRole, ("device", device_id))

            device_selected = all(info.key in self._selected_signals for info in self._signals_by_device.get(device_id, []))
            if device_selected:
                device_item.setCheckState(0, Qt.CheckState.Checked)
            else:
                visible_selected = any(info.key in self._selected_signals for info in signals)
                visible_unselected = any(info.key not in self._selected_signals for info in signals)
                if visible_selected and visible_unselected:
                    device_item.setCheckState(0, Qt.CheckState.PartiallyChecked)
                elif visible_selected:
                    device_item.setCheckState(0, Qt.CheckState.Checked)
                else:
                    device_item.setCheckState(0, Qt.CheckState.Unchecked)

            self.signal_tree.addTopLevelItem(device_item)

            for info in signals:
                signal_item = QTreeWidgetItem([info.name])
                signal_item.setFlags(
                    Qt.ItemFlag.ItemIsEnabled
                    | Qt.ItemFlag.ItemIsSelectable
                    | Qt.ItemFlag.ItemIsUserCheckable
                )
                signal_item.setData(0, Qt.ItemDataRole.UserRole, ("signal", info.key))

                checked = Qt.CheckState.Checked if info.key in self._selected_signals else Qt.CheckState.Unchecked
                signal_item.setCheckState(0, checked)

                tooltip = f"{info.signal_type.value.title()} signal from {info.device_id}"
                if not info.has_changes:
                    tooltip += " (no transitions)"
                signal_item.setToolTip(0, tooltip)

                device_item.addChild(signal_item)

        self.signal_tree.expandAll()
        self._updating_list = False

        self._selected_devices = {
            device_id
            for device_id, signals in self._signals_by_device.items()
            if all(info.key in self._selected_signals for info in signals)
        }

        total = sum(len(signals) for signals in self._signals_by_device.values())
        filtered_count = sum(len(signals) for signals in self._filtered_tree.values())
        selected_visible = sum(
            1 for signals in self._filtered_tree.values() for info in signals if info.key in self._selected_signals
        )

        self._update_status_label(filtered_count, total, selected_visible)
        self._update_button_states()

    def _update_status_label(self, filtered: int, total: int, selected: int):
        """Update the status label with counts and active filter state."""
        if not self._signals_by_device:
            device_text = ""
        else:
            all_devices = set(self._signals_by_device.keys())
            fully_selected = {
                device_id
                for device_id, signals in self._signals_by_device.items()
                if all(info.key in self._selected_signals for info in signals)
            }
            if fully_selected == all_devices:
                device_text = " (Devices: all)"
            else:
                selected_devices = sorted(fully_selected)
                if selected_devices:
                    device_text = " (Devices: " + ", ".join(selected_devices) + ")"
                else:
                    device_text = " (Devices: none)"
        self.count_label.setText(
            f"Showing {filtered} of {total} signals{device_text} — {selected} selected"
        )

        if self._filters_active():
            self.count_label.setStyleSheet(
                "padding: 4px; font-size: 11px; color: #0d47a1; font-weight: bold;"
            )
        else:
            self.count_label.setStyleSheet(
                "padding: 4px; font-size: 11px; color: #666;"
            )

    def _update_button_states(self):
        """Enable/disable selection buttons based on current state."""
        any_filtered = bool(self._filtered_signals)
        self.select_all_btn.setEnabled(any_filtered)
        self.deselect_all_btn.setEnabled(any_filtered)
        self.save_preset_btn.setEnabled(bool(self._signals))

    def _filters_active(self) -> bool:
        """Return True if any filter deviates from the default all-visible state."""
        if self._search_query.strip():
            return True
        if self._show_only_changed:
            return True
        if len(self._type_filters) != 3:
            return True
        if self._signals:
            all_keys = {info.key for info in self._signals}
            if self._selected_signals != all_keys:
                return True
        if self._signals_by_device:
            all_devices = set(self._signals_by_device.keys())
            fully_selected = {
                device_id
                for device_id, signals in self._signals_by_device.items()
                if all(info.key in self._selected_signals for info in signals)
            }
            if fully_selected != all_devices:
                return True
        return False

    def _emit_visible_signals(self):
        """Emit the list of visible + selected signals."""
        visible = [
            info.key
            for info in self._filtered_signals
            if info.key in self._selected_signals
        ]
        self.visible_signals_changed.emit(visible)

    def _reset_preset_combo(self):
        """Reset the preset combo box to default state."""
        self.preset_combo.blockSignals(True)
        self.preset_combo.clear()
        self.preset_combo.addItem("Load preset…")
        for name in sorted(self._presets):
            self.preset_combo.addItem(name)
        self.preset_combo.setCurrentIndex(0)
        self.preset_combo.blockSignals(False)

    def _set_device_selection(self, device_ids: Set[str]):
        """Update selected devices to the provided set."""
        all_devices = set(self._signals_by_device.keys())
        self._selected_devices = device_ids & all_devices if device_ids else set()

    def _apply_preset(self, name: str):
        """Apply a saved preset by name."""
        preset = self._presets.get(name)
        if not preset:
            return

        self._search_query = preset["search"]
        self.search_input.blockSignals(True)
        self.search_input.setText(self._search_query)
        self.search_input.blockSignals(False)

        self._type_filters = set(preset["types"])
        for signal_type, checkbox in self.type_checkboxes.items():
            checkbox.blockSignals(True)
            checkbox.setChecked(signal_type in self._type_filters)
            checkbox.blockSignals(False)

        self._show_only_changed = preset["show_only_changed"]
        self.changed_checkbox.blockSignals(True)
        self.changed_checkbox.setChecked(self._show_only_changed)
        self.changed_checkbox.blockSignals(False)

        preset_keys = set(preset.get("selected_signals", []))
        available_keys = {info.key for info in self._signals}
        if preset_keys:
            self._selected_signals = preset_keys & available_keys
        else:
            self._selected_signals = available_keys

        preset_devices = set(preset.get("devices", []))
        self._set_device_selection(preset_devices)
        self._apply_filters()

    # Event handlers -----------------------------------------------------
    def _on_search_changed(self, text: str):
        self._pending_search = text
        self._debounce_timer.start(self.DEBOUNCE_MS)

    def _apply_search_query(self):
        if self._search_query == self._pending_search:
            return

        self._search_query = self._pending_search
        self._apply_filters()

    def _on_type_filter_changed(self):
        new_filters: Set[SignalType] = set()
        for signal_type, checkbox in self.type_checkboxes.items():
            if checkbox.isChecked():
                new_filters.add(signal_type)

        if not new_filters:
            # Ensure at least one type remains selected
            self.sender().blockSignals(True)
            self.sender().setChecked(True)
            self.sender().blockSignals(False)
            return

        if new_filters == self._type_filters:
            return

        self._type_filters = new_filters
        self._apply_filters()

    def _on_changed_toggled(self, checked: bool):
        if self._show_only_changed == checked:
            return
        self._show_only_changed = checked
        self._apply_filters()

    def _on_tree_item_changed(self, item: QTreeWidgetItem, column: int):
        if self._updating_list:
            return

        payload = item.data(0, Qt.ItemDataRole.UserRole)
        if not payload:
            return

        kind, value = payload

        if kind == "device":
            device_id = value
            state = item.checkState(0)
            self._updating_list = True
            for idx in range(item.childCount()):
                child = item.child(idx)
                child_payload = child.data(0, Qt.ItemDataRole.UserRole)
                if not child_payload:
                    continue
                _, key = child_payload
                if state == Qt.CheckState.Checked:
                    self._selected_signals.add(key)
                    child.setCheckState(0, Qt.CheckState.Checked)
                elif state == Qt.CheckState.Unchecked:
                    self._selected_signals.discard(key)
                    child.setCheckState(0, Qt.CheckState.Unchecked)
            self._updating_list = False

            if state == Qt.CheckState.Checked:
                self._selected_devices.add(device_id)
            elif state == Qt.CheckState.Unchecked:
                self._selected_devices.discard(device_id)
            else:
                self._selected_devices.discard(device_id)

        elif kind == "signal":
            key = value
            state = item.checkState(0)

            if state == Qt.CheckState.Checked:
                self._selected_signals.add(key)
            else:
                self._selected_signals.discard(key)

            parent = item.parent()
            if parent:
                device_payload = parent.data(0, Qt.ItemDataRole.UserRole)
                device_id = device_payload[1] if device_payload else None

                checked_children = 0
                unchecked_children = 0
                for idx in range(parent.childCount()):
                    child = parent.child(idx)
                    child_state = child.checkState(0)
                    if child_state == Qt.CheckState.Checked:
                        checked_children += 1
                    elif child_state == Qt.CheckState.Unchecked:
                        unchecked_children += 1

                self._updating_list = True
                if checked_children == parent.childCount():
                    parent.setCheckState(0, Qt.CheckState.Checked)
                    if device_id:
                        self._selected_devices.add(device_id)
                elif unchecked_children == parent.childCount():
                    parent.setCheckState(0, Qt.CheckState.Unchecked)
                    if device_id and device_id in self._selected_devices:
                        self._selected_devices.discard(device_id)
                else:
                    parent.setCheckState(0, Qt.CheckState.PartiallyChecked)
                    if device_id and device_id in self._selected_devices:
                        self._selected_devices.discard(device_id)
                self._updating_list = False

        total = sum(len(signals) for signals in self._signals_by_device.values())
        filtered_count = sum(len(signals) for signals in self._filtered_tree.values())
        selected_visible = sum(
            1 for signals in self._filtered_tree.values() for info in signals if info.key in self._selected_signals
        )

        self._emit_visible_signals()
        self._update_button_states()
        self._update_status_label(filtered_count, total, selected_visible)

    def _on_select_all(self):
        for signals in self._filtered_tree.values():
            for info in signals:
                self._selected_signals.add(info.key)
        self._selected_devices = {
            device_id
            for device_id, signals in self._signals_by_device.items()
            if all(info.key in self._selected_signals for info in signals)
        }
        self._apply_filters()

    def _on_deselect_all(self):
        for signals in self._filtered_tree.values():
            for info in signals:
                self._selected_signals.discard(info.key)
        self._selected_devices = {
            device_id
            for device_id, signals in self._signals_by_device.items()
            if all(info.key in self._selected_signals for info in signals)
        }
        self._apply_filters()

    def _on_clear_filters(self):
        self._search_query = ""
        self._pending_search = ""
        self.search_input.blockSignals(True)
        self.search_input.clear()
        self.search_input.blockSignals(False)

        self._show_only_changed = False
        self.changed_checkbox.blockSignals(True)
        self.changed_checkbox.setChecked(False)
        self.changed_checkbox.blockSignals(False)

        self._type_filters = {
            SignalType.BOOLEAN,
            SignalType.STRING,
            SignalType.INTEGER,
        }
        for checkbox in self.type_checkboxes.values():
            checkbox.blockSignals(True)
            checkbox.setChecked(True)
            checkbox.blockSignals(False)

        self._selected_signals = {info.key for info in self._signals}
        self._selected_devices = set(self._signals_by_device.keys())
        self._apply_filters()

    def _on_save_preset(self):
        name, ok = QInputDialog.getText(self, "Save Filter Preset", "Preset name:")
        if not ok or not name.strip():
            return

        name = name.strip()
        self._presets[name] = {
            "search": self._search_query,
            "types": list(self._type_filters),
            "show_only_changed": self._show_only_changed,
            "selected_signals": list(self._selected_signals),
            "devices": list(self._selected_devices),
        }
        self._reset_preset_combo()

    def _on_preset_selected(self, index: int):
        if index <= 0:
            return
        name = self.preset_combo.itemText(index)
        self._apply_preset(name)
