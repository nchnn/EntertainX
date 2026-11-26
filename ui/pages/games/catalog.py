"""CatalogPage: browsable grid of all Selenite games.

Fetches the catalog on construction, renders game cards in a responsive
grid in small batches (so 921 cards never freeze the UI), and supports
live search + genre filter.

Thumbnails are loaded lazily: only cards near the viewport request their
cover, and at most ``_THUMB_BATCH`` requests start per event-loop tick.
That keeps the shared image cache/worker pool from being flooded.
"""

from __future__ import annotations

from PySide6.QtCore import QPoint, QRect, Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from api.games import GameEntry, GamesCatalog
from api.tasks import run_async
from theme import theme_manager as theme
from ui.components.form_fields import IconLineEdit
from ui.components.icons import make_icon
from ui.components.layout import EmptyState
from ui.pages.games.game_card import GameCard, THUMB_W

_GRID_GAP = 16
_BUILD_BATCH = 48   # cards created per event-loop tick
_THUMB_BATCH = 24   # thumbnails started per event-loop tick
_THUMB_MARGIN = 240  # px above/below the viewport that still preloads

_catalog = GamesCatalog()


class _CardGrid(QWidget):
    """Responsive grid that reflows on resize."""

    reflowed = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._cols = 0
        self.cards: list[GameCard] = []
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self._layout = QGridLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setHorizontalSpacing(_GRID_GAP)
        self._layout.setVerticalSpacing(_GRID_GAP)
        self._layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

    def add_card(self, card: GameCard) -> None:
        self.add_cards([card])

    def add_cards(self, cards: list[GameCard]) -> None:
        """Append many cards, placing only the new ones.

        Re-adding every existing card on each batch would make the 921-card
        build quadratic, so a known column count is reused as-is.
        """
        start = len(self.cards)
        for card in cards:
            self.cards.append(card)
            card.setParent(self)
        if self._cols <= 0:
            self._reflow(force=True)
            return
        for offset, card in enumerate(cards):
            index = start + offset
            self._layout.addWidget(card, index // self._cols, index % self._cols)

    def clear(self) -> None:
        for card in self.cards:
            self._layout.removeWidget(card)
            card.setParent(None)
            card.deleteLater()
        self.cards.clear()
        self._cols = 0

    def visible_cards(self) -> list[GameCard]:
        return [c for c in self.cards if not c.isHidden()]

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._reflow()

    def _reflow(self, force: bool = False) -> None:
        available = max(self.width(), THUMB_W)
        cols = max(1, (available + _GRID_GAP) // (THUMB_W + _GRID_GAP))
        if cols == self._cols and not force:
            return
        self._cols = cols
        for col in range(cols + 1):
            self._layout.setColumnStretch(col, 1 if col < cols else 0)
        for i, card in enumerate(self.cards):
            self._layout.addWidget(card, i // cols, i % cols)
        self.reflowed.emit()


class CatalogPage(QWidget):
    """The 'Browse Games' sub-page: header, search, genre filter, card grid."""

    game_selected = Signal(object)  # emits GameEntry

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._loaded = False
        self._fetch_started = False
        self._scroll: QScrollArea | None = None
        self._pending_entries: list[GameEntry] = []

        # 0 ms single-shot timers: one tick of the event loop between chunks,
        # so painting and input stay responsive while the grid fills in.
        self._build_timer = QTimer(self)
        self._build_timer.setSingleShot(True)
        self._build_timer.setInterval(0)
        self._build_timer.timeout.connect(self._build_next_batch)

        self._thumb_timer = QTimer(self)
        self._thumb_timer.setSingleShot(True)
        self._thumb_timer.setInterval(0)
        self._thumb_timer.timeout.connect(self._load_visible_thumbs)

        self._setup_ui()

    # -- Build -----------------------------------------------------------------

    def _setup_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.verticalScrollBar().valueChanged.connect(self._schedule_thumb_load)
        outer.addWidget(scroll)
        self._scroll = scroll

        canvas = QWidget()
        self._content = QVBoxLayout(canvas)
        self._content.setContentsMargins(
            theme.SPACE_XXL, theme.SPACE_XL, theme.SPACE_XXL, theme.SPACE_XXL
        )
        self._content.setSpacing(theme.SPACE_XL)

        # Page header
        hdr_row = QHBoxLayout()
        hdr_row.setContentsMargins(0, 0, 0, 0)
        hdr_row.setSpacing(theme.SPACE_LG)

        icon_lbl = QLabel()
        icon_lbl.setPixmap(make_icon("gamepad", theme.PRIMARY, 28).pixmap(28, 28))
        hdr_row.addWidget(icon_lbl, 0, Qt.AlignmentFlag.AlignVCenter)

        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        title_lbl = QLabel("Browse Games")
        title_lbl.setProperty("role", "h1")
        title_col.addWidget(title_lbl)
        self._count_lbl = QLabel("Loading catalog...")
        self._count_lbl.setProperty("role", "muted")
        title_col.addWidget(self._count_lbl)
        hdr_row.addLayout(title_col, 1)
        self._content.addLayout(hdr_row)

        # Toolbar: search + genre filter
        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(0, 0, 0, 0)
        toolbar.setSpacing(theme.SPACE_MD)

        self._search = IconLineEdit("search", "Search games...")
        self._search.setMaximumWidth(320)
        self._search.setMinimumWidth(180)
        self._search.textChanged.connect(self._apply_filter)
        toolbar.addWidget(self._search)

        self._genre_combo = QComboBox()
        self._genre_combo.addItem("All genres")
        self._genre_combo.setMinimumWidth(140)
        self._genre_combo.currentTextChanged.connect(self._apply_filter)
        toolbar.addWidget(self._genre_combo)
        toolbar.addStretch(1)
        self._content.addLayout(toolbar)

        # Card grid
        self._grid = _CardGrid()
        self._grid.reflowed.connect(self._schedule_thumb_load)
        self._content.addWidget(self._grid)

        # Empty state (shown when nothing matches)
        self._empty = EmptyState(
            "search",
            "No games found",
            "Try a different title or genre.",
            hint="Clear the search field to see all games.",
        )
        self._empty.setVisible(False)
        self._content.addWidget(self._empty)

        # Loading placeholder
        self._loading_lbl = QLabel("Fetching catalog from Selenite...")
        self._loading_lbl.setProperty("role", "muted")
        self._loading_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._content.addWidget(self._loading_lbl)

        self._content.addStretch(1)
        scroll.setWidget(canvas)

    # -- Lifecycle -------------------------------------------------------------

    def _fetch_catalog(self) -> None:
        run_async(
            _catalog.fetch_catalog,
            on_done=self._on_catalog_loaded,
            on_error=self._on_catalog_error,
            owner=self,
        )

    def _on_catalog_loaded(self, entries: list[GameEntry]) -> None:
        self._loaded = True
        self._loading_lbl.setVisible(False)

        # Populate genre combo from the entries we actually rendered
        tags = sorted({tag.lower() for entry in entries for tag in entry.tags})
        self._genre_combo.blockSignals(True)
        self._genre_combo.clear()
        self._genre_combo.addItem("All genres")
        for tag in tags:
            self._genre_combo.addItem(tag.capitalize(), tag)
        self._genre_combo.blockSignals(False)

        self._count_lbl.setText(f"{len(entries)} games available")

        # Build the grid in chunks so the first paint is immediate. The grid
        # stays hidden while it fills: showing each new card would force a
        # layout pass over the whole growing grid on every batch.
        self._grid.hide()
        self._pending_entries = list(entries)
        self._build_next_batch()

    def _build_next_batch(self) -> None:
        batch = self._pending_entries[:_BUILD_BATCH]
        del self._pending_entries[:_BUILD_BATCH]
        if batch:
            cards = [GameCard(entry) for entry in batch]
            for card in cards:
                card.activated.connect(self._on_card_activated)
            self._grid.add_cards(cards)

            # Filter only the new cards; a full pass over every built card on
            # each batch would dominate the build time.
            query = self._search.text()
            tag_data = self._genre_combo.currentData()
            tag = tag_data if isinstance(tag_data, str) else ""
            for card in cards:
                card.setVisible(card.matches(query, tag))

        if self._pending_entries:
            self._build_timer.start()
        else:
            self._grid.show()
            self._apply_filter()

    def _on_catalog_error(self, error: Exception) -> None:
        self._loading_lbl.setText(f"Could not load catalog: {error}")

    def showEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        super().showEvent(event)
        # Fetch only when the Games tab is first opened; the page is built at
        # startup with every other page, and loading 921 cards then would make
        # the whole app feel slow.
        if not self._fetch_started:
            self._fetch_started = True
            self._fetch_catalog()
        self._schedule_thumb_load()

    # -- Thumbnail limiter -----------------------------------------------------

    def _schedule_thumb_load(self, *_args) -> None:
        if self._loaded:
            self._thumb_timer.start()

    def _load_visible_thumbs(self) -> None:
        """Start at most ``_THUMB_BATCH`` cover requests for on-screen cards."""
        if not self._loaded or not self.isVisible() or self._scroll is None:
            return

        # Make sure the grid has laid the cards out before measuring them.
        layout = self._grid.layout()
        if layout is not None:
            layout.activate()

        viewport = self._scroll.viewport()
        area = viewport.rect().adjusted(0, -_THUMB_MARGIN, 0, _THUMB_MARGIN)
        budget = _THUMB_BATCH
        more_waiting = False

        for card in self._grid.cards:
            if card.thumb_requested or card.isHidden():
                continue
            top_left = card.mapTo(viewport, QPoint(0, 0))
            if not area.intersects(QRect(top_left, card.size())):
                continue
            if budget <= 0:
                more_waiting = True
                break
            if card.load_thumb():
                budget -= 1

        if more_waiting:
            self._thumb_timer.start()

    # -- Filter ----------------------------------------------------------------

    def _apply_filter(self) -> None:
        query = self._search.text()
        tag_data = self._genre_combo.currentData()
        tag = tag_data if isinstance(tag_data, str) else ""

        any_visible = False
        for card in self._grid.cards:
            vis = card.matches(query, tag)
            card.setVisible(vis)
            any_visible = any_visible or vis

        self._empty.setVisible(not any_visible and self._loaded)
        self._schedule_thumb_load()

    # -- Card click ------------------------------------------------------------

    def _on_card_activated(self, entry: GameEntry) -> None:
        self.game_selected.emit(entry)
