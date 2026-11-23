from __future__ import annotations

from PySide6.QtWidgets import QWidget

from api.images import ImageStore
from api.movies import TmdbClient
from ui.pages.video_browse import BrowsePage


class MoviesPage(BrowsePage):
    """Trending, new, and genre shelves of movies (TMDB)."""

    def __init__(
        self,
        parent: QWidget | None = None,
        provider: TmdbClient | None = None,
        store: ImageStore | None = None,
    ) -> None:
        super().__init__("movie", "Movies", provider=provider, store=store, parent=parent)
