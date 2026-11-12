from PySide6.QtWidgets import QWidget

from ui.components.media_card import MediaCard
from ui.pages.page_shell import GridPage
from ui.pages.sample_data import SHOWS


class TVShowsPage(GridPage):
    def __init__(self, parent: QWidget | None = None) -> None:
        cards = [
            MediaCard(
                "film",
                show["title"],
                show["genre"],
                show["seasons"],
                category=show["genre"],
            )
            for show in SHOWS
        ]
        super().__init__(
            "TV Shows",
            "Keep up with the series you follow, season by season.",
            cards,
            search_placeholder="Search shows",
            parent=parent,
        )
