from typing import Callable
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QStackedWidget
from PySide6.QtCore import Qt
from theme.theme_manager import PRIMARY, BG_DARK, TEXT_PRIMARY, BG_CARD

from ui.pages.video_youtube import YouTubePage
from ui.pages.video_movies import MoviesPage
from ui.pages.video_tvshows import TVShowsPage
from ui.pages.music import MusicPage
from ui.pages.games_chess import ChessPage
from ui.pages.games_fireboy import FireboyPage
from ui.pages.games_browse import BrowseGamesPage
from ui.pages.my_lists import MyListsPage
from ui.pages.settings import SettingsPage

_TAB_BASE = f"""
    QPushButton {{
        background: transparent;
        color: {TEXT_PRIMARY};
        border: none;
        border-bottom: 2px solid transparent;
        border-radius: 0px;
        padding: 10px 20px;
        font-size: 13px;
    }}
    QPushButton:hover {{
        color: #ffffff;
        border-bottom: 2px solid rgba(108,99,255,0.5);
    }}
"""

_TAB_ACTIVE = f"""
    QPushButton {{
        background: transparent;
        color: #ffffff;
        border: none;
        border-bottom: 2px solid {PRIMARY};
        border-radius: 0px;
        padding: 10px 20px;
        font-size: 13px;
        font-weight: bold;
    }}
"""


class ContentArea(QWidget):
    def __init__(self, on_logout: Callable, parent=None) -> None:
        super().__init__(parent)
        self._on_logout = on_logout
        self._last_tab: dict[str, int] = {}

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
                ("Settings", SettingsPage(on_logout=on_logout)),
            ],
        }

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Sub-tab bar
        self._tab_bar = QWidget()
        self._tab_bar.setFixedHeight(48)
        self._tab_bar.setStyleSheet(f"background-color: {BG_CARD}; border-bottom: 1px solid #2a2a4a;")
        self._tab_layout = QHBoxLayout(self._tab_bar)
        self._tab_layout.setContentsMargins(16, 0, 16, 0)
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
            for label, widget in tabs:
                idx = self._stack.addWidget(widget)
                self._page_index[cat][label] = idx

        # Show default
        self.show_category("Video")

    def show_category(self, name: str) -> None:
        if name not in self._categories:
            return

        tabs = self._categories[name]
        last = self._last_tab.get(name, 0)

        # Rebuild tab bar
        # Remove old buttons
        while self._tab_layout.count() > 1:  # keep trailing stretch
            item = self._tab_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self._tab_bar.setVisible(len(tabs) > 1)

        self._current_cat = name
        self._tab_buttons: list[QPushButton] = []

        for i, (label, _) in enumerate(tabs):
            btn = QPushButton(label)
            btn.setStyleSheet(_TAB_ACTIVE if i == last else _TAB_BASE)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked, idx=i: self._switch_subtab(idx))
            self._tab_layout.insertWidget(i, btn)
            self._tab_buttons.append(btn)

        self._switch_subtab(last, save=False)

    def _switch_subtab(self, index: int, save: bool = True) -> None:
        cat = self._current_cat
        tabs = self._categories[cat]
        if index >= len(tabs):
            index = 0

        label = tabs[index][0]
        page_idx = self._page_index[cat][label]
        self._stack.setCurrentIndex(page_idx)

        if save:
            self._last_tab[cat] = index

        # Update button styles
        for i, btn in enumerate(self._tab_buttons):
            btn.setStyleSheet(_TAB_ACTIVE if i == index else _TAB_BASE)
