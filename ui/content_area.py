from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QHBoxLayout,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from theme import theme_manager as theme

from auth.auth_manager import AuthManager

from ui.pages.video_youtube import YouTubePage
from ui.pages.video_movies import MoviesPage
from ui.pages.video_tvshows import TVShowsPage
from ui.pages.music import MusicPage
from ui.pages.games_chess import ChessPage
from ui.pages.games_fireboy import FireboyPage
from ui.pages.games_browse import BrowseGamesPage
from ui.pages.my_lists import MyListsPage
from ui.pages.settings import SettingsPage


class ContentArea(QWidget):
    def __init__(
        self,
        user: dict | None = None,
        auth_manager: AuthManager | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._user = user or {}
        self._auth = auth_manager
        self._last_tab: dict[str, int] = {}
        self._current_cat = ""
        self._tab_buttons: list[QPushButton] = []
        self._tab_group: QButtonGroup | None = None

        # Build category → [(label, page_widget), ...]
        self._categories: dict[str, list[tuple[str, QWidget]]] = {
            "Video": [
                ("YouTube", YouTubePage()),
                ("Movies", MoviesPage()),
                ("TV Shows", TVShowsPage()),
            ],
            "Music": [
                ("Music", MusicPage()),
            ],
            "Games": [
                ("Chess", ChessPage()),
                ("Fireboy & Watergirl", FireboyPage()),
                ("Browse Games", BrowseGamesPage()),
            ],
            "My Lists": [
                ("My Lists", MyListsPage()),
            ],
            "Settings": [
                ("Settings", SettingsPage(user=self._user)),
            ],
        }

        # Admin page — visible only when the session has the admin role
        if self._user.get("role") == "admin" and self._auth is not None:
            from ui.pages.admin import AdminPage

            self._categories["Admin"] = [
                ("Admin", AdminPage(auth_manager=self._auth)),
            ]

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Sub-tab bar
        self._tab_bar = QWidget()
        self._tab_bar.setObjectName("TabBar")
        self._tab_bar.setFixedHeight(56)
        self._tab_layout = QHBoxLayout(self._tab_bar)
        # Padding inside the tab button is 18px, so a 14px margin puts the
        # first tab label on the same 32px axis as page titles.
        self._tab_layout.setContentsMargins(14, 0, 14, 0)
        self._tab_layout.setSpacing(0)
        self._tab_layout.addStretch()
        outer.addWidget(self._tab_bar)

        # Stacked content
        self._stack = QStackedWidget()
        outer.addWidget(self._stack)

        # Add all pages to stack
        self._page_index: dict[str, dict[str, int]] = {}
        for cat, tabs in self._categories.items():
            self._page_index[cat] = {}
            for tab_label, widget in tabs:
                idx = self._stack.addWidget(widget)
                self._page_index[cat][tab_label] = idx

        # Show default
        self.show_category("Video")

    # ── Category navigation ─────────────────────────────────────────────────
    def show_category(self, name: str) -> None:
        if name not in self._categories:
            return

        tabs = self._categories[name]
        last = self._last_tab.get(name, 0)

        # Rebuild the tab bar, keeping the trailing stretch.
        while self._tab_layout.count() > 1:
            item = self._tab_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.hide()
                widget.setParent(None)
                widget.deleteLater()

        if self._tab_group is not None:
            self._tab_group.deleteLater()
        self._tab_group = QButtonGroup(self)
        self._tab_group.setExclusive(True)

        self._current_cat = name
        self._tab_buttons = []

        for index, (tab_label, _) in enumerate(tabs):
            button = QPushButton(tab_label)
            button.setProperty("variant", "tab")
            button.setCheckable(True)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(
                lambda checked=False, i=index: self._switch_subtab(i)
            )
            self._tab_group.addButton(button)
            self._tab_layout.insertWidget(index, button)
            self._tab_buttons.append(button)

        self._switch_subtab(last, save=False)

    def _switch_subtab(self, index: int, save: bool = True) -> None:
        category = self._current_cat
        tabs = self._categories[category]
        if index >= len(tabs):
            index = 0

        tab_label = tabs[index][0]
        page_index = self._page_index[category][tab_label]
        self._stack.setCurrentIndex(page_index)

        if save:
            self._last_tab[category] = index

        if index < len(self._tab_buttons):
            for tab_index, button in enumerate(self._tab_buttons):
                active = tab_index == index
                button.setChecked(active)
                button.setProperty("active", "true" if active else "false")
                theme.restyle(button)

    # ── Introspection (used by tests) ───────────────────────────────────────
    def current_tab_index(self) -> int:
        for index, button in enumerate(self._tab_buttons):
            if button.isChecked():
                return index
        return 0

    def current_page(self) -> QWidget:
        return self._stack.currentWidget()
