from __future__ import annotations

from typing import Callable

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from theme import theme_manager as theme
from ui.components.icons import make_icon
from ui.components.surfaces import Divider, ElidedLabel, label

_BASE_CATEGORIES = ["Video", "Music", "Games", "My Lists", "Settings"]
CATEGORIES = _BASE_CATEGORIES  # kept for backward compatibility

_ICONS = {
    "Video": "film",
    "Music": "music",
    "Games": "gamepad",
    "My Lists": "list",
    "Settings": "gear",
    "Admin": "shield",
}


class Sidebar(QWidget):
    """Navigation rail: categories in the middle, account + log out at the bottom.

    Branding lives only in the window title bar, so the rail starts directly
    with navigation and ends with a single, anchored profile row.
    """

    def __init__(
        self,
        username: str,
        on_category: Callable[[str], None],
        on_logout: Callable[[], None] | None = None,
        is_admin: bool = False,
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
        self.logout_button: QPushButton | None = None

        # Build category list: admins get the Admin item appended.
        categories = list(_BASE_CATEGORIES)
        if is_admin:
            categories.append("Admin")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        nav = QVBoxLayout()
        nav.setContentsMargins(
            theme.SPACE_MD, theme.SPACE_XL, theme.SPACE_MD, theme.SPACE_MD
        )
        nav.setSpacing(theme.SPACE_XS)
        for category in categories:
            button = self._build_nav_button(category)
            self._group.addButton(button)
            self._buttons[category] = button
            nav.addWidget(button)
        layout.addLayout(nav)

        layout.addStretch(1)
        layout.addWidget(Divider())

        self.profile_section = self._build_profile(username)
        layout.addWidget(self.profile_section)

        self.set_active(CATEGORIES[0])

    # ── Construction ────────────────────────────────────────────────────────
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

    def _build_profile(self, username: str) -> QWidget:
        footer = QWidget()
        row = QHBoxLayout(footer)
        row.setContentsMargins(
            theme.SPACE_MD, theme.SPACE_MD, theme.SPACE_MD, theme.SPACE_LG
        )
        row.setSpacing(theme.SPACE_SM)

        initial = (username.strip() or "?")[0].upper()
        self.avatar_label = QLabel(initial)
        self.avatar_label.setProperty("role", "avatar")
        self.avatar_label.setFixedSize(30, 30)
        self.avatar_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        row.addWidget(self.avatar_label, 0, Qt.AlignmentFlag.AlignVCenter)

        account = QVBoxLayout()
        account.setContentsMargins(0, 0, 0, 0)
        account.setSpacing(1)

        self.username_label = ElidedLabel(username)
        self.username_label.setProperty("role", "username")
        self.username_label.setToolTip(username)
        self.username_label.setMinimumWidth(0)
        self.username_label.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred
        )
        account.addWidget(self.username_label)

        self.status_label = label("Signed in", "caption", wrap=False)
        account.addWidget(self.status_label)

        row.addLayout(account, 1)

        if self._on_logout is not None:
            self.logout_button = QPushButton()
            self.logout_button.setProperty("variant", "icon")
            self.logout_button.setIcon(make_icon("logout", theme.PRIMARY, 18))
            self.logout_button.setIconSize(QSize(18, 18))
            self.logout_button.setFixedSize(36, 36)
            self.logout_button.setToolTip("Log out")
            self.logout_button.setAccessibleName("Log out")
            self.logout_button.setCursor(Qt.CursorShape.PointingHandCursor)
            self.logout_button.clicked.connect(self._handle_logout)
            row.addWidget(self.logout_button, 0, Qt.AlignmentFlag.AlignVCenter)

        return footer

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

    # ── Session ─────────────────────────────────────────────────────────────
    def _handle_logout(self) -> None:
        if self._on_logout is not None:
            self._on_logout()
