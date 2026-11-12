from PySide6.QtWidgets import QWidget

from ui.components.media_card import MediaCard
from ui.pages.page_shell import GridPage
from ui.pages.sample_data import VIDEOS


class YouTubePage(GridPage):
    def __init__(self, parent: QWidget | None = None) -> None:
        cards = [
            MediaCard(
                "play",
                video["title"],
                video["channel"],
                video["length"],
                thumb_height=132,
            )
            for video in VIDEOS
        ]
        super().__init__(
            "YouTube",
            "Watch, search, and queue videos from the channels you follow.",
            cards,
            search_placeholder="Search videos",
            parent=parent,
        )
