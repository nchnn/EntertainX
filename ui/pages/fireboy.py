from PySide6.QtWidgets import QWidget

from ui.pages.game_detail import GameDetailPage


class FireboyPage(GameDetailPage):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(
            "Fireboy & Watergirl",
            "Co-op puzzle platforming, right inside the app.",
            "gamepad",
            "Guide two characters through a shared temple using different "
            "abilities. Built for two players on one keyboard, with instant restarts.",
            [
                "Local two-player controls (WASD + arrow keys)",
                "Level select with completion tracking",
                "Fullscreen-ready canvas inside the app window",
            ],
            "The game canvas is scheduled for Phase 6 of the build.",
            parent=parent,
        )
