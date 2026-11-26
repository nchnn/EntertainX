from PySide6.QtWidgets import QWidget

from ui.components.video.media_card import MediaCard
from ui.pages.page_shell import GridPage
from ui.pages.sample_data import GAMES


class BrowseGamesPage(GridPage):
    def __init__(self, parent: QWidget | None = None) -> None:
        cards = [
            MediaCard(
                "gamepad",
                game["title"],
                game["genre"],
                game["players"],
                category=game["genre"],
            )
            for game in GAMES
        ]
        super().__init__(
            "Browse Games",
            "Small, quick games built into EntertainX - no installs required.",
            cards,
            search_placeholder="Search games",
            badge="In development",
            parent=parent,
        )
