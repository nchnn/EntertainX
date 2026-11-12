from __future__ import annotations

from typing import Callable

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from theme import theme_manager as theme
from ui.components.icons import brand_pixmap, make_icon
from ui.components.surfaces import Divider

CATEGORIES = ["Video", "Music", "Games", "My Lists", "Settings"]

_ICONS = {
    "Video": "film",
    "Music": "music",
    "Games": "gamepad",
    "My Lists": "list",
    "Settings": "gear",
}


class Sidebar(QWidget):
    """Primary navigation rail: brand, account chip, categories, log out."""

    def __init__(
        self,
        username: str,
        on_category: Callable[[str], None],
        on_logout: Callable[[], None] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("Sidebar")
        self.setFixedWidth(theme.SIDEBAR_WIDTH)

        self._on_category = on_category
        self._on_logout = on_logout
        self._active = ""
        self._buttons: dict[str, QPushButton] = {}
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addWidget(self._build_header(username))
        layout.addWidget(Divider())
        layout.addSpacing(theme.SPACE_MD)

        nav = QVBoxLayout()
        nav.setContentsMargins(theme.SPACE_MD, 0, theme.SPACE_MD, 0)
        nav.setSpacing(theme.SPACE_XS)
        for category in CATEGORIES:
            button = self._build_nav_button(category)
            self._group.addButton(button)
            self._buttons[category] = button
            nav.addWidget(button)
        layout.addLayout(nav)

        layout.addStretch(1)

        if on_logout is not None:
            layout.addWidget(Divider())
            footer = QVBoxLayout()
            footer.setContentsMargins(theme.SPACE_MD, theme.SPACE_MD, theme.SPACE_MD, theme.SPACE_LG)
            footer.setSpacing(0)

            logout = QPushButton("  Log out")
            logout.setProperty("variant", "nav")
            logout.setIcon(make_icon("logout", theme.TEXT_MUTED, 18))
            logout.setIconSize(QSize(18, 18))
            logout.setFixedHeight(40)
            logout.setCursor(Qt.CursorShape.PointingHandCursor)
            logout.setToolTip("Sign out of EntertainX")
            logout.clicked.connect(lambda: self._on_logout())
            footer.addWidget(logout)
            layout.addLayout(footer)

        self.set_active(CATEGORIES[0])

    # ── Construction ────────────────────────────────────────────────────────
    def _build_header(self, username: str) -> QWidget:
        header = QWidget()
        column = QVBoxLayout(header)
        column.setContentsMargins(
            theme.SPACE_LG + 2, theme.SPACE_XL, theme.SPACE_LG, theme.SPACE_LG
        )
        column.setSpacing(theme.SPACE_MD)

        brand_row = QHBoxLayout()
        brand_row.setContentsMargins(0, 0, 0, 0)
        brand_row.setSpacing(theme.SPACE_SM)

        mark = QLabel()
        mark.setPixmap(brand_pixmap(26))
        mark.setFixedSize(26, 26)
        brand_row.addWidget(mark, 0, Qt.AlignmentFlag.AlignVCenter)

        wordmark = QLabel("EntertainX")
        wordmark.setProperty("role", "brand")
        brand_row.addWidget(wordmark, 0, Qt.AlignmentFlag.AlignVCenter)
        brand_row.addStretch(1)
        column.addLayout(brand_row)

        chip = QFrame()
        chip.setProperty("role", "chip")
        chip_row = QHBoxLayout(chip)
        chip_row.setContentsMargins(
            theme.SPACE_SM, theme.SPACE_SM, theme.SPACE_MD, theme.SPACE_SM
        )
        chip_row.setSpacing(theme.SPACE_SM)

        initial = (username.strip() or "?")[0].upper()
        avatar = QLabel(initial)
        avatar.setProperty("role", "avatar")
        avatar.setFixedSize(30, 30)
        avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        chip_row.addWidget(avatar, 0, Qt.AlignmentFlag.AlignVCenter)

        account = QVBoxLayout()
        account.setContentsMargins(0, 0, 0, 0)
        account.setSpacing(0)

        self.username_label = QLabel(username)
        account.addWidget(self.username_label)

        signed_in = QLabel("Signed in")
        signed_in.setProperty("role", "caption")
        account.addWidget(signed_in)

        chip_row.addLayout(account, 1)
        column.addWidget(chip)

        return header

    def _build_nav_button(self, category: str) -> QPushButton:
        button = QPushButton(category)
        button.setProperty("variant", "nav")
        button.setCheckable(True)
        button.setIcon(
            make_icon(_ICONS[category], theme.TEXT_MUTED, 18, theme.PRIMARY)
        )
        button.setIconSize(QSize(18, 18))
        button.setFixedHeight(42)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.clicked.connect(lambda checked=False, c=category: self.set_active(c))
        return button

    # ── Navigation ──────────────────────────────────────────────────────────
    def active_category(self) -> str:
        return self._active

    def set_active(self, name: str) -> None:
        if name not in self._buttons:
            return
        self._active = name
        for category, button in self._buttons.items():
            active = category == name
            button.setChecked(active)
            button.setProperty("active", "true" if active else "false")
            theme.restyle(button)
        self._on_category(name)
