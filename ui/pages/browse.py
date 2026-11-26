"""Netflix-style browse page shared by Movies and TV Shows.

The page composes the pieces and owns the data flow; it contains no HTTP. All
provider calls go through ``api.tasks.run_async`` so the GUI never waits on the
network. Shelves load lazily as they near the viewport.
"""

from __future__ import annotations

from PySide6.QtCore import QPoint, QRect, Qt, QTimer
from PySide6.QtGui import QPainter
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
from ui.components.video.hero_banner import HeroBanner
from ui.components.video.hover_preview import HoverPreview
from ui.components.video.media_shelf import MediaRow
from ui.components.layout import EmptyState, InlineBanner
from ui.components.video.tile_grid import TileGrid
from ui.components.video.title_detail import TitleDetailOverlay
from ui.components.video.top10_panel import Top10Panel
from ui.components.video_player_view import (
    VideoPlayerView,
    build_payload,
    configured_servers,
)
from ui.pages.page_shell import PageShell

EAGER_ROWS = 3  # shelves fetched immediately; the rest wait until scrolled near
LOOKAHEAD = 360  # px below the viewport at which a shelf starts loading
SEARCH_DEBOUNCE_MS = 350
ATTRIBUTION = "This product uses the TMDB API but is not endorsed or certified by TMDB."

_GENRE_PILL_QSS = """
QComboBox {
    background-color: rgba(255, 255, 255, 0.08);
    color: #F4F1F2;
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 18px;
    padding: 0px 28px 0px 14px;
    font-size: 13px;
    font-family: 'Figtree', 'Segoe UI', sans-serif;
}
QComboBox:hover {
    background-color: rgba(255, 255, 255, 0.14);
    border-color: rgba(255, 255, 255, 0.22);
}
QComboBox:focus {
    border-color: #E8AAB9;
}
QComboBox::drop-down {
    border: none;
    width: 22px;
}
QComboBox::down-arrow {
    image: none;
    width: 0px;
    height: 0px;
}
QComboBox QAbstractItemView {
    background-color: #2A272C;
    color: #F4F1F2;
    border: 1px solid rgba(255, 255, 255, 0.12);
    selection-background-color: rgba(232, 170, 185, 0.28);
    selection-color: #F4F1F2;
    outline: none;
    padding: 4px;
}
"""


class NavGenreCombo(QComboBox):
    """Genre filter drawn as a nav pill with a chevron."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        from ui.components.icons import make_icon

        self.setFixedHeight(36)
        self.setMinimumWidth(118)
        self.setMaximumWidth(188)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(_GENRE_PILL_QSS)
        self._chevron = make_icon("chevron-down", "#B8B2B5", 14)

    def paintEvent(self, event) -> None:  # noqa: N802
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        self._chevron.paint(
            painter,
            QRect(self.width() - 24, (self.height() - 14) // 2, 14, 14),
        )
        painter.end()


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
        self._store = store
        self.rows: dict[str, MediaRow] = {}
        self._specs = {spec.key: spec for spec in ROWS[media_type]}
        self._requested: set[str] = set()
        self._details: dict[tuple[str, int], MediaDetails] = {}
        self._trailer_loading: set[tuple[str, int]] = set()
        self._started = False
        self._query_id = 0

        self.header.setVisible(False)

        # ── Toolbar ─────────────────────────────────────────────────────────
        from PySide6.QtGui import QKeySequence, QShortcut
        from ui.components.form_fields import IconLineEdit
        from ui.components.icons import make_icon

        self.search = IconLineEdit("search", f"Search {title.lower()}...")
        self.search.setClearButtonEnabled(True)
        self.search.setMinimumWidth(0)
        self.search.setMinimumHeight(36)
        self.search.setMaximumHeight(36)

        self._search_shortcut = QShortcut(QKeySequence("Ctrl+K"), self)
        self._search_shortcut.activated.connect(self.search.setFocus)

        self.genre_filter = NavGenreCombo()
        self.genre_filter.setToolTip("Filter by genre")
        self.genre_filter.addItem("All genres", None)
        for genre_id, name in GENRE_FILTERS[media_type]:
            self.genre_filter.addItem(name, genre_id)

        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.setProperty("variant", "subtle")
        self.refresh_button.setIcon(make_icon("refresh", theme.PRIMARY, 16))
        self.refresh_button.setMinimumHeight(theme.CONTROL_HEIGHT)
        self.refresh_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.refresh_button.setToolTip("Reload trending and new releases")
        self.refresh_button.setVisible(False)

        self.toolbar_box = QWidget()
        toolbar = QHBoxLayout(self.toolbar_box)
        toolbar.setContentsMargins(0, 0, 0, 0)
        toolbar.setSpacing(theme.SPACE_SM)
        toolbar.addWidget(self.search)
        toolbar.addWidget(self.genre_filter)

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

        # Inline player: covers this page while a title plays; the back arrow returns.
        self.player_view = VideoPlayerView(self)
        self.player_view.hide()
        self.player_view.back_requested.connect(self._close_player)

        self._wire()

    # ── Wiring ──────────────────────────────────────────────────────────────
    def _wire(self) -> None:
        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(SEARCH_DEBOUNCE_MS)
        self._debounce.timeout.connect(self._run_query)
        self.search.textChanged.connect(lambda _text: self._debounce.start())
        self.genre_filter.currentIndexChanged.connect(lambda _index: self._run_query())
        def _handle_refresh() -> None:
            self.refresh_button.setText("Refreshing...")
            self.refresh_button.setEnabled(False)
            QTimer.singleShot(600, lambda: (
                self.refresh_button.setText("Refresh"),
                self.refresh_button.setEnabled(True),
            ))
            self.refresh()

        self.refresh_button.clicked.connect(_handle_refresh)

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
        if self.detail.isVisible():
            self.detail.close_overlay()
        self._close_player()

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self.player_view.setGeometry(self.rect())
        self.preview.dismiss()
        if self._started:
            QTimer.singleShot(0, self._request_visible_rows)

    def _start(self) -> None:
        if not self.provider.available:
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
        for item in items[:6]:
            if item.key not in self._details:
                run_async(
                    self.provider.details,
                    item.media_type,
                    item.id,
                    on_done=self._update_tiles_with_details,
                    owner=self,
                )

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
        for item in items[:6]:
            if item.key not in self._details:
                run_async(
                    self.provider.details,
                    item.media_type,
                    item.id,
                    on_done=self._update_tiles_with_details,
                    owner=self,
                )

    def _update_tiles_with_details(self, details: MediaDetails) -> None:
        self._details[details.item.key] = details
        key = details.item.key
        for row in self.rows.values():
            for tile in row.tiles:
                if tile.item.key == key:
                    tile.update_item(details.item, self._store)
        for tile in self.top10._tiles:
            if tile.item.key == key:
                tile.item = details.item
                tile.load_image(self._store)

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
    def _fetch_details(
        self,
        item: MediaItem,
        on_done: Callable[[MediaDetails], None],
        on_error: Callable[[Exception], None] | None = None,
    ) -> None:
        cached = self._details.get(item.key)
        if cached is not None:
            on_done(cached)
            return

        def _handle_done(details: MediaDetails) -> None:
            self._update_tiles_with_details(details)
            on_done(details)

        run_async(
            self.provider.details,
            item.media_type,
            item.id,
            on_done=_handle_done,
            on_error=on_error,
            owner=self,
        )

    def _open_details(self, item: MediaItem) -> None:
        self.preview.dismiss()
        self.detail.open(item)
        self._fetch_details(
            item,
            on_done=self.detail.set_details,
            on_error=lambda error: self.detail.set_error(friendly(error)),
        )

    def _on_preview_details_needed(self, item: MediaItem) -> None:
        def _apply_preview(details: MediaDetails) -> None:
            if self.preview.item and self.preview.item.key == item.key:
                self.preview.set_details(details)

        self._fetch_details(item, on_done=_apply_preview)

    def _close_player(self) -> None:
        if self.player_view.isVisible():
            self.player_view.stop()
            self.player_view.hide()

    def _open_player(self, item: MediaItem, details: MediaDetails, servers: list[dict]) -> None:
        def _show(episodes: list[dict]) -> None:
            self.player_view.setGeometry(self.rect())
            self.player_view.play(build_payload(item, details, servers, episodes))
            self.player_view.show()
            self.player_view.raise_()

        if item.media_type != "tv":
            _show([])
            return

        def _episodes(rows) -> None:
            _show([{"season": 1, "episode": ep.number, "title": ep.name} for ep in rows])

        run_async(
            self.provider.episodes,
            item.id,
            1,
            on_done=_episodes,
            on_error=lambda _error: _show([]),
            owner=self,
        )

    def _play(self, item: MediaItem) -> None:
        self.preview.dismiss()
        servers = configured_servers()
        if servers:
            if self.detail.isVisible():
                self.detail.close_overlay()
            self._fetch_details(
                item,
                on_done=lambda details: self._open_player(item, details, servers),
                on_error=lambda error: self.banner.show_message(friendly(error)),
            )
            return
        # No streaming servers configured: keep the existing trailer behaviour.
        self.detail.open(item, auto_play=True)
        cached = self._details.get(item.key)
        if cached is not None:
            self.detail.set_details(cached)
            return
        self.banner.clear()

        def _on_ready(details: MediaDetails) -> None:
            self.detail.set_details(details)

        def _on_fail(error: Exception) -> None:
            self.detail.set_error(friendly(error))

        self._fetch_details(item, on_done=_on_ready, on_error=_on_fail)
