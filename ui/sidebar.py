from typing import Callable
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Qt
from theme.theme_manager import BG_SIDEBAR, PRIMARY, TEXT_PRIMARY, TEXT_MUTED, BG_DARK

CATEGORIES = ["Video", "Music", "Games", "My Lists", "Settings"]

_ICONS = {
    "Video": "▶",
    "Music": "🎵",
    "Games": "🎮",
    "My Lists": "☰",
    "Settings": "⚙",
}

_BTN_BASE = f"""
    QPushButton {{
        background: transparent;
        color: {TEXT_PRIMARY};
        border: none;
        border-left: 3px solid transparent;
        border-radius: 0px;
        padding: 12px 20px;
        text-align: left;
        font-size: 14px;
    }}
    QPushButton:hover {{
        background: rgba(108, 99, 255, 0.15);
    }}
"""

_BTN_ACTIVE = f"""
    QPushButton {{
        background: rgba(108, 99, 255, 0.2);
        color: #ffffff;
        border: none;
        border-left: 3px solid {PRIMARY};
        border-radius: 0px;
        padding: 12px 20px;
        text-align: left;
        font-size: 14px;
        font-weight: bold;
    }}
"""


class Sidebar(QWidget):
    def __init__(self, username: str, on_category: Callable[[str], None], parent=None) -> None:
        super().__init__(parent)
        self.setFixedWidth(220)
        self.setStyleSheet(f"background-color: {BG_SIDEBAR};")
        self._on_category = on_category
        self._active = ""
        self._buttons: dict[str, QPushButton] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # App name + username header
        header = QWidget()
        header.setStyleSheet(f"background-color: {BG_SIDEBAR};")
        hlayout = QVBoxLayout(header)
        hlayout.setContentsMargins(20, 24, 20, 16)
        hlayout.setSpacing(4)

        app_lbl = QLabel("EntertainX")
        app_lbl.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {PRIMARY}; background: transparent;")
        hlayout.addWidget(app_lbl)

        user_lbl = QLabel(f"👤 {username}")
        user_lbl.setStyleSheet(f"font-size: 12px; color: {TEXT_MUTED}; background: transparent;")
        hlayout.addWidget(user_lbl)

        layout.addWidget(header)

        # Divider
        div = QLabel()
        div.setFixedHeight(1)
        div.setStyleSheet(f"background: #2a2a4a;")
        layout.addWidget(div)

        layout.addSpacing(8)

        # Category buttons
        for cat in CATEGORIES:
            btn = QPushButton(f"  {_ICONS[cat]}  {cat}")
            btn.setStyleSheet(_BTN_BASE)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked, c=cat: self.set_active(c))
            self._buttons[cat] = btn
            layout.addWidget(btn)

        layout.addStretch()

        # Activate default
        self.set_active(CATEGORIES[0])

    def active_category(self) -> str:
        return self._active

    def set_active(self, name: str) -> None:
        if name not in self._buttons:
            return
        self._active = name
        for cat, btn in self._buttons.items():
            btn.setStyleSheet(_BTN_ACTIVE if cat == name else _BTN_BASE)
        self._on_category(name)
