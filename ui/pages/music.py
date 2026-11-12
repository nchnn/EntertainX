from PySide6.QtWidgets import QWidget

from ui.components.music_card import MusicPlayerCard
from ui.pages.page_shell import GridPage
from ui.pages.sample_data import ALBUMS


class MusicPage(GridPage):
    def __init__(self, parent: QWidget | None = None) -> None:
        cards = [
            MusicPlayerCard(
                album["title"],
                album["artist"],
                album["tracks"],
                album["length"],
                category=album["artist"],
            )
            for album in ALBUMS
        ]
        super().__init__(
            "Music",
            "Albums, artists, and tracks gathered in one place.",
            cards,
            search_placeholder="Search albums",
            parent=parent,
        )
        for card in self.grid.cards:
            card.play_toggled.connect(
                lambda playing, card=card: self._on_card_toggled(card, playing)
            )

    # ── One preview at a time ───────────────────────────────────────────────
    def _on_card_toggled(self, card: MusicPlayerCard, playing: bool) -> None:
        if playing:
            self._pause_others(card)

    def _pause_others(self, active: MusicPlayerCard) -> None:
        for card in self.grid.cards:
            if card is not active:
                card.pause()

    def apply_filter(self) -> None:
        super().apply_filter()
        for card in self.grid.cards:
            if card.isHidden():
                card.pause()
