from PySide6.QtWidgets import QWidget

from ui.pages.game_detail import GameDetailPage


class ChessPage(GameDetailPage):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(
            "Chess",
            "A complete game of chess against a local engine.",
            "gamepad",
            "Play full games with legal-move highlighting, captured pieces, and "
            "undo - entirely offline, with no account or download required.",
            [
                "Local engine with three difficulty levels",
                "Legal move hints and last-move highlighting",
                "Save and resume a game from My Lists",
            ],
            "The chess engine is scheduled for Phase 6 of the build.",
            parent=parent,
        )
