"""EntertainX Music page with streaming playback, search, shelves, and lyrics."""

from __future__ import annotations

from PySide6.QtCore import QPoint, QSize, Qt, QTimer
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from api.images import ImageStore
from api.music import MusicClient
from api.tasks import run_async
from theme import theme_manager as theme
from ui.components.form_fields import IconLineEdit
from ui.components.icons import make_icon
from ui.components.layout import EmptyState
from ui.components.music.artist_header import ArtistHeader
from ui.components.music.audio_engine import AudioEngine, get_audio_engine
from ui.components.music.lyrics_view import LyricsView
from ui.components.music.models import ArtistProfile, Track
from ui.components.music.player_bar import PlayerBar
from ui.components.music.queue_drawer import QueueDrawer
from ui.components.music.track_card import TrackCard
from ui.components.music.track_row import TrackRow
from ui.pages.page_shell import PageShell

SEARCH_DEBOUNCE_MS = 350


class MusicShelf(QWidget):
    """Horizontal scrolling shelf displaying track cards."""

    def __init__(
        self,
        title: str,
        subtitle: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # Header
        head_row = QHBoxLayout()
        head_row.setContentsMargins(0, 0, 0, 0)

        self.title_label = QLabel(title)
        self.title_label.setStyleSheet(
            f"color: {theme.TEXT_PRIMARY}; font-size: {theme.FONT_SIZE_LG}px; font-weight: 700;"
        )
        head_row.addWidget(self.title_label)
        head_row.addStretch(1)

        layout.addLayout(head_row)

        # Horizontal scroll area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFixedHeight(256)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet(
            "QScrollArea { background: transparent; border: none; } "
            "QScrollBar:horizontal { height: 6px; background: transparent; } "
            f"QScrollBar::handle:horizontal {{ background: {theme.BORDER}; border-radius: 3px; }} "
            "QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }"
        )

        self.cards_container = QWidget()
        self.cards_container.setStyleSheet("background: transparent;")
        self.cards_layout = QHBoxLayout(self.cards_container)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        self.cards_layout.setSpacing(16)
        self.cards_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        self.scroll_area.setWidget(self.cards_container)
        layout.addWidget(self.scroll_area)

    def set_tracks(self, tracks: list[Track], store: ImageStore | None = None) -> None:
        while self.cards_layout.count() > 0:
            item = self.cards_layout.takeAt(0)
            if item is not None and item.widget() is not None:
                w = item.widget()
                if w is not None:
                    w.deleteLater()

        for track in tracks:
            card = TrackCard(track, store=store, parent=self.cards_container)
            self.cards_layout.addWidget(card)


class MusicPage(PageShell):
    """Main Music streaming section with search, shelves, player, lyrics, and queue."""

    def __init__(
        self,
        client: MusicClient | None = None,
        store: ImageStore | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(
            "Music",
            "Stream millions of full-length songs in 320kbps high quality with synced lyrics.",
            parent=parent,
        )
        self.client = client or MusicClient()
        self._store = store or ImageStore()
        self._engine = get_audio_engine()
        self._engine.set_client(self.client)

        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(SEARCH_DEBOUNCE_MS)
        self._search_timer.timeout.connect(self._perform_search)

        # ── Restructure Layout into Split: [Content | Side Panel] + Bottom Player ──
        # Detach scroll_area from PageShell's default outer layout
        outer = self.layout()
        assert isinstance(outer, QVBoxLayout)
        outer.removeWidget(self.scroll_area)

        # Body split layout (Scroll area + Side Panel)
        body_split = QHBoxLayout()
        body_split.setContentsMargins(0, 0, 0, 0)
        body_split.setSpacing(0)
        body_split.addWidget(self.scroll_area, 1)

        # Side panel stack (Lyrics and Queue)
        self.side_panel = QStackedWidget()
        self.side_panel.setFixedWidth(360)
        self.side_panel.hide()

        self.lyrics_view = LyricsView()
        self.lyrics_view.close_requested.connect(self._close_side_panel)
        self.side_panel.addWidget(self.lyrics_view)

        self.queue_drawer = QueueDrawer(store=self._store)
        self.queue_drawer.close_requested.connect(self._close_side_panel)
        self.side_panel.addWidget(self.queue_drawer)

        body_split.addWidget(self.side_panel, 0)
        outer.addLayout(body_split, 1)

        # Fixed Bottom Playback Bar
        self.player_bar = PlayerBar(store=self._store, parent=self)
        self.player_bar.lyrics_toggled.connect(self._on_lyrics_toggled)
        self.player_bar.queue_toggled.connect(self._on_queue_toggled)
        outer.addWidget(self.player_bar, 0)

        # ── Toolbar: Search & Quick Filters ─────────────────────────────────
        toolbar_row = QHBoxLayout()
        toolbar_row.setContentsMargins(0, 0, 0, theme.SPACE_MD)
        toolbar_row.setSpacing(12)

        self.search = IconLineEdit(
            "search",
            "Search songs, artists, or albums... (e.g. Multo, Justin Bieber)",
        )
        self.search.setClearButtonEnabled(True)
        self.search.setMinimumWidth(320)
        self.search.setMaximumWidth(480)
        self.search.textChanged.connect(self._on_search_text_changed)
        toolbar_row.addWidget(self.search)

        # Quick preset pills
        for label, query in [
            ("Trending", "Top Hits 2026"),
            ("OPM Hits", "Cup of Joe"),
            ("Pop", "Justin Bieber"),
            ("R&B", "The Weeknd"),
        ]:
            btn = QPushButton(label)
            btn.setProperty("variant", "chip")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(
                f"QPushButton {{ background-color: {theme.BG_CARD}; color: {theme.TEXT_SECONDARY}; "
                f"border: 1px solid {theme.BORDER}; border-radius: 14px; padding: 4px 14px; font-size: 12px; }} "
                f"QPushButton:hover {{ background-color: {theme.BG_ELEVATED}; color: {theme.TEXT_PRIMARY}; }}"
            )
            btn.clicked.connect(lambda _, q=query: self._set_query_and_search(q))
            toolbar_row.addWidget(btn)

        toolbar_row.addStretch(1)
        self.content.insertLayout(1, toolbar_row)

        # ── Dynamic Views Stack inside Content ──────────────────────────────
        self.view_stack = QStackedWidget()
        self.content.insertWidget(2, self.view_stack)

        # 1. Browse View
        self.browse_widget = QWidget()
        self.browse_layout = QVBoxLayout(self.browse_widget)
        self.browse_layout.setContentsMargins(0, 0, 0, 0)
        self.browse_layout.setSpacing(24)

        self.shelf_albums = MusicShelf("Albums & singles", "Fresh and popular releases")
        self.browse_layout.addWidget(self.shelf_albums)

        self.shelf_trending = MusicShelf("Trending", "Top streamed tracks today")
        self.browse_layout.addWidget(self.shelf_trending)

        # Top Songs Two-Column Grid
        songs_header = QLabel("Top Songs")
        songs_header.setStyleSheet(
            f"color: {theme.TEXT_PRIMARY}; font-size: {theme.FONT_SIZE_LG}px; font-weight: 700;"
        )
        self.browse_layout.addWidget(songs_header)

        self.top_songs_container = QWidget()
        self.top_songs_layout = QVBoxLayout(self.top_songs_container)
        self.top_songs_layout.setContentsMargins(0, 0, 0, 0)
        self.top_songs_layout.setSpacing(4)
        self.browse_layout.addWidget(self.top_songs_container)

        self.view_stack.addWidget(self.browse_widget)

        # 2. Search & Artist Results View
        self.search_widget = QWidget()
        self.search_layout = QVBoxLayout(self.search_widget)
        self.search_layout.setContentsMargins(0, 0, 0, 0)
        self.search_layout.setSpacing(20)

        self.artist_header_box = QWidget()
        self.artist_header_layout = QVBoxLayout(self.artist_header_box)
        self.artist_header_layout.setContentsMargins(0, 0, 0, 0)
        self.search_layout.addWidget(self.artist_header_box)

        self.search_results_title = QLabel("Search Results")
        self.search_results_title.setStyleSheet(
            f"color: {theme.TEXT_PRIMARY}; font-size: {theme.FONT_SIZE_LG}px; font-weight: 700;"
        )
        self.search_layout.addWidget(self.search_results_title)

        self.search_results_container = QWidget()
        self.search_results_layout = QVBoxLayout(self.search_results_container)
        self.search_results_layout.setContentsMargins(0, 0, 0, 0)
        self.search_results_layout.setSpacing(4)
        self.search_layout.addWidget(self.search_results_container)

        self.shelf_search_releases = MusicShelf("Releases & Singles")
        self.search_layout.addWidget(self.shelf_search_releases)

        self.view_stack.addWidget(self.search_widget)

        # Initial data load
        self._load_initial_shelves()

    # ── Initial Data Loading ────────────────────────────────────────────────
    def _load_initial_shelves(self) -> None:
        def fetch_data() -> dict:
            trending = self.client.get_trending(limit=15)
            # Default OPM / Popular albums
            albums = self.client.search("Cup of Joe", limit=10)
            top_songs = self.client.search("Top Hits", limit=8)
            return {
                "trending": trending,
                "albums": albums,
                "top_songs": top_songs,
            }

        def on_done(data: dict) -> None:
            trending = data.get("trending", [])
            albums = data.get("albums", [])
            top_songs = data.get("top_songs", [])

            self.shelf_trending.set_tracks(trending, store=self._store)
            self.shelf_albums.set_tracks(albums, store=self._store)

            # Populate top songs list
            while self.top_songs_layout.count() > 0:
                item = self.top_songs_layout.takeAt(0)
                if item is not None and item.widget() is not None:
                    w = item.widget()
                    if w is not None:
                        w.deleteLater()

            for i, track in enumerate(top_songs):
                row = TrackRow(track, index=i + 1, store=self._store, parent=self.top_songs_container)
                self.top_songs_layout.addWidget(row)

        run_async(fetch_data, on_done=on_done, owner=self)

    # ── Search & Filter Logic ───────────────────────────────────────────────
    def _on_search_text_changed(self, text: str) -> None:
        query = text.strip()
        if not query:
            self._search_timer.stop()
            self.view_stack.setCurrentIndex(0)
            return
        self._search_timer.start()

    def _set_query_and_search(self, query: str) -> None:
        self.search.setText(query)
        self._perform_search()

    def _perform_search(self) -> None:
        query = self.search.text().strip()
        if not query:
            self.view_stack.setCurrentIndex(0)
            return

        def fetch_results() -> dict:
            tracks = self.client.search(query, limit=16)
            # Fetch artist profile if query looks like an artist name
            artist = self.client.get_artist(query) if len(query) > 3 else None
            return {"tracks": tracks, "artist": artist}

        def on_done(data: dict) -> None:
            tracks = data.get("tracks", [])
            artist = data.get("artist")

            # Show search results view
            self.view_stack.setCurrentIndex(1)
            self.search_results_title.setText(f"Top results for '{query}'")

            # Artist banner
            while self.artist_header_layout.count() > 0:
                item = self.artist_header_layout.takeAt(0)
                if item is not None and item.widget() is not None:
                    w = item.widget()
                    if w is not None:
                        w.deleteLater()

            if artist and (artist.image_url or len(artist.top_tracks) >= 3):
                header = ArtistHeader(artist, store=self._store, parent=self.artist_header_box)
                self.artist_header_layout.addWidget(header)
                self.artist_header_box.show()
            else:
                self.artist_header_box.hide()

            # Tracks list
            while self.search_results_layout.count() > 0:
                item = self.search_results_layout.takeAt(0)
                if item is not None and item.widget() is not None:
                    w = item.widget()
                    if w is not None:
                        w.deleteLater()

            for i, track in enumerate(tracks[:10]):
                row = TrackRow(
                    track,
                    index=i + 1,
                    store=self._store,
                    parent=self.search_results_container,
                )
                self.search_results_layout.addWidget(row)

            # Shelf for remaining tracks / releases
            if len(tracks) > 5:
                self.shelf_search_releases.set_tracks(tracks[5:], store=self._store)
                self.shelf_search_releases.show()
            else:
                self.shelf_search_releases.hide()

        run_async(fetch_results, on_done=on_done, owner=self)

    # ── Side Panel Toggles ──────────────────────────────────────────────────
    def _on_lyrics_toggled(self, active: bool) -> None:
        if active:
            self.side_panel.setCurrentWidget(self.lyrics_view)
            self.side_panel.show()
            if self.player_bar._queue_active:
                self.player_bar._queue_active = False
                self.player_bar.btn_queue.setIcon(make_icon("queue", theme.TEXT_MUTED, 18))
        else:
            if self.side_panel.currentWidget() == self.lyrics_view:
                self.side_panel.hide()

    def _on_queue_toggled(self, active: bool) -> None:
        if active:
            self.side_panel.setCurrentWidget(self.queue_drawer)
            self.side_panel.show()
            if self.player_bar._lyrics_active:
                self.player_bar._lyrics_active = False
                self.player_bar.btn_lyrics.setIcon(make_icon("mic", theme.TEXT_MUTED, 18))
        else:
            if self.side_panel.currentWidget() == self.queue_drawer:
                self.side_panel.hide()

    def _close_side_panel(self) -> None:
        self.side_panel.hide()
        if self.player_bar._lyrics_active:
            self.player_bar._lyrics_active = False
            self.player_bar.btn_lyrics.setIcon(make_icon("mic", theme.TEXT_MUTED, 18))
        if self.player_bar._queue_active:
            self.player_bar._queue_active = False
            self.player_bar.btn_queue.setIcon(make_icon("queue", theme.TEXT_MUTED, 18))

