from __future__ import annotations

from typing import Callable

from PySide6.QtCore import (
    QEasingCurve,
    QEvent,
    QPropertyAnimation,
    QSize,
    Qt,
    Property,
    QTimer,
)
from PySide6.QtGui import QEnterEvent
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

_CATEGORIES = ["Video", "Music", "Games"]
_ICONS = {
    "Video": "film",
    "Music": "music",
    "Games": "gamepad",
    "Admin": "shield",
}
_TOOLTIPS = {
    "Video": "<b>Film</b><br><span style='color:#B8B2B5;'>Movies, TV Shows & Trailers</span>",
    "Music": "<b>Music</b><br><span style='color:#B8B2B5;'>Songs, Albums & Playlists</span>",
    "Games": "<b>Games</b><br><span style='color:#B8B2B5;'>Playable In-GUI Games & Catalog</span>",
    "Admin": "<b>Admin</b><br><span style='color:#B8B2B5;'>User & System Administration</span>",
}


class Sidebar(QWidget):
    """Icon-only navigation rail with auto-hide overflow behavior.

    Collapses to a narrow 6px indicator at the left edge; expands smoothly
    on hover to reveal the Film, Music, and Games icon controls.
    """

    COLLAPSED_WIDTH = 0
    EXPANDED_WIDTH = 64

    def __init__(
        self,
        username: str | Callable[[str], None] = "",
        on_category: Callable[[str], None] | None = None,
        on_logout: Callable[[], None] | None = None,
        is_admin: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("Sidebar")
        self.setMouseTracking(True)

        # Support both Sidebar(on_category) and Sidebar(username, on_category, ...)
        if callable(username) and on_category is None:
            on_category = username
            username = ""

        self._on_category = on_category or (lambda _c: None)
        self._on_logout = on_logout
        self._active = ""
        self._buttons: dict[str, QPushButton] = {}
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        self.logout_button: QPushButton | None = None

        self._current_width = self.COLLAPSED_WIDTH
        self.setFixedWidth(self.COLLAPSED_WIDTH)

        self._anim = QPropertyAnimation(self, b"rail_width")
        self._anim.setDuration(220)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._leave_timer = QTimer(self)
        self._leave_timer.setSingleShot(True)
        self._leave_timer.setInterval(120)
        self._leave_timer.timeout.connect(self._do_collapse)

        categories = list(_CATEGORIES)
        if is_admin:
            categories.append("Admin")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, theme.SPACE_XL, 8, theme.SPACE_MD)
        layout.setSpacing(theme.SPACE_MD)
        layout.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)

        for category in categories:
            btn = self._build_icon_button(category)
            self._group.addButton(btn)
            self._buttons[category] = btn
            layout.addWidget(btn)

        layout.addStretch(1)

        self.set_active(_CATEGORIES[0])

    # ── Property for smooth width animation ─────────────────────────────────
    def _get_rail_width(self) -> int:
        return self._current_width

    def _set_rail_width(self, width: int) -> None:
        self._current_width = width
        self.setFixedWidth(width)

    rail_width = Property(int, _get_rail_width, _set_rail_width)

    # ── Construction ────────────────────────────────────────────────────────
    def _build_icon_button(self, category: str) -> QPushButton:
        button = QPushButton()
        button.setProperty("variant", "nav-icon")
        button.setCheckable(True)
        button.setIcon(
            make_icon(_ICONS[category], theme.TEXT_MUTED, 22, theme.PRIMARY)
        )
        button.setIconSize(QSize(22, 22))
        button.setFixedSize(46, 46)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setToolTip(_TOOLTIPS.get(category, category))
        button.clicked.connect(lambda checked=False, c=category: self.set_active(c))
        return button

    # ── Auto-hide hover behavior ────────────────────────────────────────────
    def enterEvent(self, event: QEnterEvent) -> None:
        self._leave_timer.stop()
        self.expand()
        super().enterEvent(event)

    def leaveEvent(self, event: QEvent) -> None:
        self._leave_timer.start()
        super().leaveEvent(event)

    def expand(self) -> None:
        if self._anim.state() == QPropertyAnimation.State.Running:
            self._anim.stop()
        if self._current_width != self.EXPANDED_WIDTH:
            self._anim.setStartValue(self._current_width)
            self._anim.setEndValue(self.EXPANDED_WIDTH)
            self._anim.start()

    def collapse(self) -> None:
        self._leave_timer.start()

    def _do_collapse(self) -> None:
        if self._anim.state() == QPropertyAnimation.State.Running:
            self._anim.stop()
        if self._current_width != self.COLLAPSED_WIDTH:
            self._anim.setStartValue(self._current_width)
            self._anim.setEndValue(self.COLLAPSED_WIDTH)
            self._anim.start()

    # ── Navigation ──────────────────────────────────────────────────────────
    def active_category(self) -> str:
        return self._active

    def mark_active(self, name: str) -> None:
        """Update the rail highlight without navigating again."""
        self._active = name if name in self._buttons else ""
        for category, button in self._buttons.items():
            active = category == name
            button.setChecked(active)
            button.setProperty("active", "true" if active else "false")
            theme.restyle(button)

    def set_active(self, name: str) -> None:
        if name not in self._buttons:
            return
        self.mark_active(name)
        self._on_category(name)
