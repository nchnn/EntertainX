from PySide6.QtWidgets import QWidget

from ui.components.media_card import MediaCard
from ui.pages.page_shell import GridPage
from ui.pages.sample_data import ALBUMS


class MusicPage(GridPage):
    def __init__(self, parent: QWidget | None = None) -> None:
        cards = [
            MediaCard(
                "music",
                album["title"],
                album["artist"],
                album["tracks"],
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
