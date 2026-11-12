from PySide6.QtWidgets import QComboBox, QWidget

from theme import theme_manager as theme
from ui.components.media_card import MediaCard
from ui.pages.page_shell import GridPage
from ui.pages.sample_data import MOVIES


class MoviesPage(GridPage):
    def __init__(self, parent: QWidget | None = None) -> None:
        cards = [
            MediaCard(
                "film",
                movie["title"],
                movie["genre"],
                f"{movie['year']}  ·  {movie['runtime']}",
                category=movie["genre"],
            )
            for movie in MOVIES
        ]
        super().__init__(
            "Movies",
            "Find something to watch tonight, then keep it in your lists.",
            cards,
            search_placeholder="Search movies",
            parent=parent,
        )

        self.genre_filter = QComboBox()
        self.genre_filter.setMinimumHeight(theme.CONTROL_HEIGHT)
        self.genre_filter.addItem("All genres")
        for genre in sorted({movie["genre"] for movie in MOVIES}):
            self.genre_filter.addItem(genre)
        self.genre_filter.currentIndexChanged.connect(self.apply_filter)
        self.add_toolbar_widget(self.genre_filter)

    def active_category(self) -> str:
        combo = getattr(self, "genre_filter", None)
        if combo is None:
            return ""
        value = combo.currentText()
        return "" if value in ("", "All genres") else value
