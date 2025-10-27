"""Centralized colors and helpers to keep UI windows visually consistent."""

from __future__ import annotations

from typing import Sequence

from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

# Palette --------------------------------------------------------------------
PRIMARY_NAVY = "#003D82"
PRIMARY_ACCENT = "#4285F4"
ACCENT_HOVER = "#1967D2"
ACCENT_PRESSED = "#0D47A1"

SECONDARY_GRAY = "#9E9E9E"
SECONDARY_HOVER = "#757575"
SECONDARY_PRESSED = "#616161"

SURFACE_BG = "#F4F6FB"
CARD_BG = "#FFFFFF"
SOFT_BORDER = "#D7DEE4"
MUTED_TEXT = "#607D8B"


# Reusable styles ------------------------------------------------------------
PRIMARY_BUTTON_STYLE = f"""
QPushButton {{
    background-color: {PRIMARY_ACCENT};
    color: white;
    border: none;
    border-radius: 6px;
    font-size: 13px;
    font-weight: bold;
    padding: 8px 18px;
}}
QPushButton:hover {{
    background-color: {ACCENT_HOVER};
}}
QPushButton:pressed {{
    background-color: {ACCENT_PRESSED};
}}
QPushButton:disabled {{
    background-color: #BDBDBD;
    color: #f5f5f5;
}}
"""

SECONDARY_BUTTON_STYLE = f"""
QPushButton {{
    background-color: {SECONDARY_GRAY};
    color: white;
    border: none;
    border-radius: 6px;
    font-size: 13px;
    font-weight: bold;
    padding: 8px 18px;
}}
QPushButton:hover {{
    background-color: {SECONDARY_HOVER};
}}
QPushButton:pressed {{
    background-color: {SECONDARY_PRESSED};
}}
QPushButton:disabled {{
    background-color: #BDBDBD;
    color: #f5f5f5;
}}
"""


def apply_primary_button_style(button: QPushButton) -> None:
    """Apply the accent button style used throughout the main window."""
    button.setStyleSheet(PRIMARY_BUTTON_STYLE)


def apply_secondary_button_style(button: QPushButton) -> None:
    """Apply the neutral/secondary button style."""
    button.setStyleSheet(SECONDARY_BUTTON_STYLE)


def surface_stylesheet(object_name: str) -> str:
    """Return a stylesheet that paints a widget with the shared surface color."""
    return f"""
    QWidget#{object_name} {{
        background-color: {SURFACE_BG};
    }}
    """


def card_panel_styles(object_name: str) -> str:
    """Return a stylesheet for panels with rounded borders on white cards."""
    return f"""
    QWidget#{object_name}, QFrame#{object_name} {{
        background-color: {CARD_BG};
        border-radius: 10px;
        border: 1px solid {SOFT_BORDER};
    }}
    """


def create_header_bar(
    title: str,
    subtitle: str | None = None,
    *,
    extra_widgets: Sequence[QWidget] | None = None,
) -> QWidget:
    """Create a navy header bar with optional actions matching the main window."""
    header = QWidget()
    header.setObjectName("ThemedHeader")
    header.setStyleSheet(
        f"""
        QWidget#ThemedHeader {{
            background-color: {PRIMARY_NAVY};
        }}
        QLabel#HeaderTitle {{
            color: white;
            font-size: 16px;
            font-weight: bold;
        }}
        QLabel#HeaderSubtitle {{
            color: rgba(255, 255, 255, 0.8);
            font-size: 12px;
        }}
        """
    )

    layout = QHBoxLayout(header)
    layout.setContentsMargins(18, 12, 18, 12)
    layout.setSpacing(12)

    text_container = QWidget()
    text_layout = QVBoxLayout(text_container)
    text_layout.setContentsMargins(0, 0, 0, 0)
    text_layout.setSpacing(2)

    title_label = QLabel(title)
    title_label.setObjectName("HeaderTitle")
    text_layout.addWidget(title_label)

    if subtitle:
        subtitle_label = QLabel(subtitle)
        subtitle_label.setObjectName("HeaderSubtitle")
        subtitle_label.setWordWrap(True)
        text_layout.addWidget(subtitle_label)

    layout.addWidget(text_container, stretch=0)
    layout.addStretch(1)

    if extra_widgets:
        for widget in extra_widgets:
            layout.addWidget(widget, stretch=0)

    return header


__all__ = [
    "ACCENT_HOVER",
    "ACCENT_PRESSED",
    "CARD_BG",
    "MUTED_TEXT",
    "PRIMARY_ACCENT",
    "PRIMARY_BUTTON_STYLE",
    "PRIMARY_NAVY",
    "SECONDARY_BUTTON_STYLE",
    "SECONDARY_GRAY",
    "SECONDARY_HOVER",
    "SECONDARY_PRESSED",
    "SOFT_BORDER",
    "SURFACE_BG",
    "apply_primary_button_style",
    "apply_secondary_button_style",
    "card_panel_styles",
    "create_header_bar",
    "surface_stylesheet",
]
