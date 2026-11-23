"""Netflix-style browse page shared by Movies and TV Shows.

The page composes the pieces and owns the data flow; it contains no HTTP. All
provider calls go through ``api.tasks.run_async`` so the GUI never waits on the
network. Shelves load lazily as they near the viewport.
"""

from __future__ import annotations

from PySide6.QtCore import QPoint, QTimer
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from api.images import ImageStore
from api.movies import (
    GENRE_FILTERS,
    ROWS,
    ApiError,
    MediaDetails,
    MediaItem,
    RowSpec,
    TmdbClient,
)
from api.tasks import run_async
from theme import theme_manager as theme
from ui.components import motion
from ui.components.hero_banner import HeroBanner
from ui.components.hover_preview import HoverPreview
from ui.components.media_row import MediaRow
from ui.components.surfaces import EmptyState, InlineBanner
from ui.components.tile_grid import TileGrid
from ui.components.title_detail import TitleDetailOverlay
from ui.components.top10_panel import Top10Panel
from ui.components.trailer_dialog import TrailerDialog
from ui.pages.page_shell import PageShell

EAGER_ROWS = 3  # shelves fetched immediately; the rest wait until scrolled near
LOOKAHEAD = 360  # px below the viewport at which a shelf starts loading
SEARCH_DEBOUNCE_MS = 350
ATTRIBUTION = "This product uses the TMDB API but is not endorsed or certified by TMDB."


def friendly(error: Exception) -> str:
    """A message that is safe and useful to show; never a stack trace."""
    if isinstance(error, ApiError):
        return str(error)
    return "Something went wrong while loading this. Please try again."


class BrowsePage(PageShell):
    def __init__(
        self,
        media_type: str,
        title: str,
        provider: TmdbClient | None = None,
        store: ImageStore | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(title, "", parent=parent)
        self.media_type = media_type
        self.provider = provider if provider is not None else TmdbClient()
        self.rows: dict[str, MediaRow] = {}
        self._specs = {spec.key: spec for spec in ROWS[media_type]}
        self._requested: set[str] = set()
        self._details: dict[tuple[str, int], MediaDetails] = {}
        self._trailer_loading: set[tuple[str, int]] = set()
        self._started = False
        self._query_id = 0

        self.header.setVisible(False)

        # ── Toolbar ─────────────────────────────────────────────────────────
        from ui.components.fields import IconLineEdit

        self.search = IconLineEdit("search", f"Search {title.lower()}")
        self.search.setMaximumWidth(340)
        self.search.setMinimumWidth(200)

        self.genre_filter = QComboBox()
        self.genre_filter.setMinimumHeight(theme.CONTROL_HEIGHT)
        self.genre_filter.addItem("All genres", None)
        for genre_id, name in GENRE_FILTERS[media_type]:
            self.genre_filter.addItem(name, genre_id)
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.setProperty("variant", "subtle")
        self.refresh_button.setMinimumHeight(theme.CONTROL_HEIGHT)
        self.refresh_button.setToolTip("Reload trending and new releases")

        self.toolbar_box = QWidget()
        toolbar = QHBoxLayout(self.toolbar_box)
        toolbar.setContentsMargins(0, 0, 0, 0)
        toolbar.setSpacing(theme.SPACE_MD)
        toolbar.addWidget(self.search)
        toolbar.addWidget(self.genre_filter)
        toolbar.addStretch(1)
        toolbar.addWidget(self.refresh_button)
        self.add(self.toolbar_box)

        self.banner = InlineBanner("error")
        self.add(self.banner)

        # ── Browse view: hero + shelves ─────────────────────────────────────
        self.browse_box = QWidget()
        browse = QVBoxLayout(self.browse_box)
        browse.setContentsMargins(0, 0, 0, 0)
        browse.setSpacing(28)
        self.hero = HeroBanner(store)
        browse.addWidget(self.hero)
        self.top10 = Top10Panel(
            f"Top 10 {title} Today", store
        )
        browse.addWidget(self.top10)
        for spec in ROWS[media_type]:
            row = MediaRow(spec.title, spec.badge, store)
            self.rows[spec.key] = row
            browse.addWidget(row)
        self.add(self.browse_box)

        # ── Results view ────────────────────────────────────────────────────
        self.results_box = QWidget()
        results = QVBoxLayout(self.results_box)
        results.setContentsMargins(0, 0, 0, 0)
        results.setSpacing(theme.SPACE_LG)
        self.results_title = QLabel("")
        self.results_title.setProperty("role", "sectionTitle")
        results.addWidget(self.results_title)
        self.results_grid = TileGrid(store)
        results.addWidget(self.results_grid)
        self.empty_state = EmptyState(
            "search",
            "Nothing matches that search",
            "Try a different title or genre.",
            hint="Clear the search field to go back to everything.",
        )
        self.empty_state.setVisible(False)
        results.addWidget(self.empty_state)
        self.results_box.setVisible(False)
        self.add(self.results_box)

        # ── No-key state ────────────────────────────────────────────────────
        self.setup_state = EmptyState(
            "film",
            "Connect TMDB to fill this page",
            "Trending titles, new releases, posters and trailers come from The "
            "Movie Database, which is free for non-commercial projects. Create "
            "a key at themoviedb.org, then add TMDB_API_KEY=your_key to the "
            ".env file and restart EntertainX.",
            hint="README.md has the full steps.",
        )
        self.setup_state.setVisible(False)
        self.add(self.setup_state)

        self.attribution = QLabel(ATTRIBUTION)
        self.attribution.setProperty("role", "caption")
        self.add(self.attribution)

        # ── Floating layers (children of the page, above the scroll area) ───
        self.preview = HoverPreview(self, store)
        self.detail = TitleDetailOverlay(self, store)

        self._wire()

    # ── Wiring ──────────────────────────────────────────────────────────────
    def _wire(self) -> None:
        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(SEARCH_DEBOUNCE_MS)
        self._debounce.timeout.connect(self._run_query)
        self.search.textChanged.connect(lambda _text: self._debounce.start())
        self.genre_filter.currentIndexChanged.connect(lambda _index: self._run_query())
        self.refresh_button.clicked.connect(self.refresh)

        self.top10.tile_entered.connect(self.preview.tile_entered)
        self.top10.tile_left.connect(self.preview.tile_left)
        self.top10.item_activated.connect(self._open_details)

        self.hero.play_clicked.connect(self._play)
        self.hero.info_clicked.connect(self._open_details)

        for spec_key, row in self.rows.items():
            row.tile_entered.connect(self.preview.tile_entered)
            row.tile_left.connect(self.preview.tile_left)
            row.item_activated.connect(self._open_details)
            row.scrolled.connect(self.preview.dismiss)
            row.retry_requested.connect(lambda key=spec_key: self._retry(key))
        self.results_grid.tile_entered.connect(self.preview.tile_entered)
        self.results_grid.tile_left.connect(self.preview.tile_left)
        self.results_grid.item_activated.connect(self._open_details)

        self.preview.play_requested.connect(self._play)
        self.preview.details_requested.connect(self._open_details)
        self.preview.details_needed.connect(self._on_preview_details_needed)
        self.preview.wheel_passthrough.connect(self._forward_wheel)

        self.detail.play_requested.connect(self._play)
        self.scroll_area.verticalScrollBar().valueChanged.connect(self._on_page_scrolled)

    def _forward_wheel(self, event) -> None:
        QApplication.sendEvent(self.scroll_area.viewport(), event)

    # ── Loading shelves ──────────────────────────────────────────────────────
    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        if not self._started:
            self._started = True
            self._start()

    def hideEvent(self, event) -> None:  # noqa: N802
        super().hideEvent(event)
        self.preview.dismiss()

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self.preview.dismiss()
        if self._started:
            QTimer.singleShot(0, self._request_visible_rows)

    def _start(self) -> None:
        if not self.provider.available:
            self.toolbar_box.setVisible(False)
            self.browse_box.setVisible(False)
            self.setup_state.setVisible(True)
            return
        self.hero.set_loading()
        for row in self.rows.values():
            row.set_loading()
        self._load_top10()
        self._request_visible_rows(force_first=EAGER_ROWS)

    def refresh(self) -> None:
        self.banner.clear()
        self._requested.clear()
        self._details.clear()
        self.hero.set_loading()
        for row in self.rows.values():
            row.set_loading()
        self._load_top10()
        self._request_visible_rows(force_first=EAGER_ROWS)

    def _load_top10(self) -> None:
        run_async(
            self.provider.trending_today,
            self.media_type,
            on_done=self._on_top10_loaded,
            on_error=lambda error: self.top10.set_error(friendly(error)),
            owner=self,
        )

    def _on_top10_loaded(self, items: list[MediaItem]) -> None:
        self.top10.set_items(items)

    def _retry(self, key: str) -> None:
        self.rows[key].set_loading()
        self._requested.discard(key)
        self._request_row(key)

    def _on_page_scrolled(self, _value: int) -> None:
        self.preview.dismiss()
        self._request_visible_rows()

    def _request_visible_rows(self, force_first: int = 0) -> None:
        if not self.provider.available or self.browse_box.isHidden():
            return
        viewport = self.scroll_area.viewport()
        limit = viewport.height() + LOOKAHEAD
        for index, (key, row) in enumerate(self.rows.items()):
            if key in self._requested:
                continue
            near = row.mapTo(viewport, QPoint(0, 0)).y() < limit
            if index < force_first or near:
                self._request_row(key)

    def _request_row(self, key: str) -> None:
        if key in self._requested:
            return
        self._requested.add(key)
        spec = self._specs[key]
        run_async(
            self.provider.fetch_row,
            spec,
            self.media_type,
            on_done=lambda items, s=spec: self._on_row_loaded(s, items),
            on_error=lambda error, s=spec: self._on_row_failed(s, error),
            owner=self,
        )

    def _on_row_loaded(self, spec: RowSpec, items: list[MediaItem]) -> None:
        self.rows[spec.key].set_items(items)
        if spec.key == "trending":
            self.hero.set_items(items)
            self.hero.setVisible(bool(self.hero.items))

    def _on_row_failed(self, spec: RowSpec, error: Exception) -> None:
        message = friendly(error)
        self.rows[spec.key].set_error(message)
        if spec.key == "trending":
            self.hero.setVisible(False)
            self.banner.show_message(message)

    # ── Search and genre filter ──────────────────────────────────────────────
    def _query_provider(self, text: str, genre_id: int | None) -> list[MediaItem]:
        if text:
            items = self.provider.search(self.media_type, text)
            if genre_id is not None:
                items = [item for item in items if genre_id in item.genre_ids]
            return items
        return self.provider.discover(self.media_type, int(genre_id))  # type: ignore[arg-type]

    def _run_query(self) -> None:
        if not self.provider.available:
            return
        text = self.search.text().strip()
        genre_id = self.genre_filter.currentData()
        self._query_id += 1
        query_id = self._query_id
        self.preview.dismiss()

        if not text and genre_id is None:
            self.results_box.setVisible(False)
            self.browse_box.setVisible(True)
            motion.reveal(self.browse_box, duration=320, rise=10.0)
            return

        genre = self.genre_filter.currentText() if genre_id is not None else ""
        if text and genre:
            self.results_title.setText(f'Results for \u201c{text}\u201d in {genre}')
        elif text:
            self.results_title.setText(f'Results for \u201c{text}\u201d')
        else:
            self.results_title.setText(genre)

        self.browse_box.setVisible(False)
        self.results_box.setVisible(True)
        self.empty_state.setVisible(False)
        self.results_grid.set_items([])
        self.banner.clear()
        run_async(
            self._query_provider,
            text,
            genre_id,
            on_done=lambda items: self._on_results(query_id, items),
            on_error=lambda error: self._on_results_failed(query_id, error),
            owner=self,
        )

    def _on_results(self, query_id: int, items: list[MediaItem]) -> None:
        if query_id != self._query_id:
            return
        self.results_grid.set_items(items)
        self.empty_state.setVisible(not items)

    def _on_results_failed(self, query_id: int, error: Exception) -> None:
        if query_id != self._query_id:
            return
        self.banner.show_message(friendly(error))

    def result_titles(self) -> list[str]:
        return [tile.item.title for tile in self.results_grid.tiles]

    # ── Details and trailers ────────────────────────────────────────────────
    def _open_details(self, item: MediaItem) -> None:
        self.preview.dismiss()
        self.detail.open(item)
        cached = self._details.get(item.key)
        if cached is not None:
            self.detail.set_details(cached)
            return
        run_async(
            self.provider.details,
            item.media_type,
            item.id,
            on_done=lambda details: self._on_details(details),
            on_error=lambda error: self.detail.set_error(friendly(error)),
            owner=self,
        )

    def _on_details(self, details: MediaDetails) -> None:
        self._details[details.item.key] = details
        self.detail.set_details(details)

    def _on_preview_details_needed(self, item: MediaItem) -> None:
        cached = self._details.get(item.key)
        if cached is not None:
            self.preview.set_details(cached)
            return
        run_async(
            self.provider.details,
            item.media_type,
            item.id,
            on_done=lambda details, k=item.key: self._on_preview_details_loaded(k, details),
            owner=self,
        )

    def _on_preview_details_loaded(
        self, key: tuple[str, int], details: MediaDetails
    ) -> None:
        self._details[key] = details
        if self.preview.item and self.preview.item.key == key:
            self.preview.set_details(details)

    def _play(self, item: MediaItem) -> None:
        self.preview.dismiss()
        cached = self._details.get(item.key)
        if cached is not None:
            self._launch_trailer(cached)
            return
        if item.key in self._trailer_loading:
            return
        self._trailer_loading.add(item.key)
        self.banner.clear()
        run_async(
            self.provider.details,
            item.media_type,
            item.id,
            on_done=lambda details, k=item.key: self._on_trailer_details(k, details),
            on_error=lambda error, k=item.key: self._on_trailer_failed(k, error),
            owner=self,
        )

    def _on_trailer_details(self, key: tuple[str, int], details: MediaDetails) -> None:
        self._trailer_loading.discard(key)
        self._details[key] = details
        self.detail.set_details(details)
        self._launch_trailer(details)

    def _on_trailer_failed(self, key: tuple[str, int], error: Exception) -> None:
        self._trailer_loading.discard(key)
        self.banner.show_message(friendly(error))

    def _launch_trailer(self, details: MediaDetails) -> None:
        if not details.trailer_key:
            self.banner.show_message(
                f"No trailer is available for {details.item.title}."
            )
            return
        self.banner.clear()
        self.show_trailer(details.item.title, details.trailer_key)

    def show_trailer(self, title: str, key: str) -> None:
        """Open the in-app trailer player (overridable in tests)."""
        dialog = TrailerDialog(title, key, self.window())
        dialog.exec()
        dialog.deleteLater()
