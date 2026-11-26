"""GamesPage: stacked widget that hosts the catalog browser and in-app player.

Index 0: CatalogPage  (browse 920+ games)
Index 1: GamePlayerWidget  (embedded Chromium, no external browser)

Clicking a card in the catalog switches to index 1 and loads the game.
The player's Back button switches back to index 0 and unloads the page.
"""

from __future__ import annotations

from PySide6.QtWidgets import QStackedWidget, QWidget

from api.games import GameEntry
from ui.pages.games.catalog import CatalogPage
from ui.pages.games.player import GamePlayerWidget

_IDX_CATALOG = 0
_IDX_PLAYER = 1


class GamesPage(QStackedWidget):
    """Top-level widget for the Browse Games sub-tab."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._catalog = CatalogPage()
        self._player = GamePlayerWidget()

        self.addWidget(self._catalog)   # index 0
        self.addWidget(self._player)    # index 1

        self._catalog.game_selected.connect(self._open_game)
        self._player.close_requested.connect(self._close_game)

        self.setCurrentIndex(_IDX_CATALOG)

    # -- Navigation ------------------------------------------------------------

    def _open_game(self, entry: GameEntry) -> None:
        self._player.load_game(entry.name, entry.embed_url)
        self.setCurrentIndex(_IDX_PLAYER)

    def _close_game(self) -> None:
        self.setCurrentIndex(_IDX_CATALOG)
