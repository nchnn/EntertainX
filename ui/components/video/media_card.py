"""Poster/video-style cards and the responsive grid that holds them."""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from theme import theme_manager as theme
from ui.components.icons import make_icon
from ui.components.layout import ElidedLabel


class MediaCard(QFrame):
    """A card with an icon "artwork" tile, title, subtitle, and meta line.

    Static sample content until Phases 3-6 attach real artwork.
    """

    def __init__(
        self,
        icon_name: str,
        title: str,
        subtitle: str,
        meta: str = "",
        thumb_height: int = theme.CARD_THUMB_HEIGHT,
        category: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.category = category
        self.setProperty("role", "mediaCard")
        self.setMinimumWidth(theme.CARD_MIN_WIDTH)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.setCursor(Qt.CursorShape.ArrowCursor)

        column = QVBoxLayout(self)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(0)

        thumb = QFrame()
        thumb.setProperty("role", "thumb")
        thumb.setFixedHeight(thumb_height)
        thumb_layout = QVBoxLayout(thumb)
        thumb_layout.setContentsMargins(0, 0, 0, 0)
        thumb_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        glyph = QLabel()
        glyph.setPixmap(make_icon(icon_name, theme.PRIMARY, 30).pixmap(30, 30))
        glyph.setAlignment(Qt.AlignmentFlag.AlignCenter)
        thumb_layout.addWidget(glyph)
        column.addWidget(thumb)

        text_box = QVBoxLayout()
        text_box.setContentsMargins(
            theme.SPACE_MD, theme.SPACE_MD, theme.SPACE_MD, theme.SPACE_MD
        )
        text_box.setSpacing(theme.SPACE_XS)

        self.title_label = ElidedLabel(title)
        self.title_label.setProperty("role", "h3")
        text_box.addWidget(self.title_label)

        self.subtitle_label = ElidedLabel(subtitle)
        self.subtitle_label.setProperty("role", "muted")
        text_box.addWidget(self.subtitle_label)

        self.meta_label = ElidedLabel(meta)
        self.meta_label.setProperty("role", "caption")
        self.meta_label.setVisible(bool(meta))
        text_box.addWidget(self.meta_label)

        column.addLayout(text_box)

    # ── Queries used by page filters ────────────────────────────────────────
    @property
    def title(self) -> str:
        return self.title_label.full_text()

    def matches(self, query: str) -> bool:
        needle = query.strip().lower()
        if not needle:
            return True
        haystack = " ".join(
            (
                self.title_label.full_text(),
                self.subtitle_label.full_text(),
                self.meta_label.full_text(),
            )
        ).lower()
        return needle in haystack


class CardGrid(QWidget):
    """Responsive grid: columns are derived from the widget's own width."""

    def __init__(
        self,
        cards: list[MediaCard] | None = None,
        min_width: int = theme.CARD_MIN_WIDTH,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._min_width = min_width
        self._columns = 0
        self.cards: list[MediaCard] = []
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )

        self._grid = QGridLayout(self)
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._grid.setHorizontalSpacing(theme.SPACE_LG)
        self._grid.setVerticalSpacing(theme.SPACE_LG)
        self._grid.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

        for card in cards or []:
            self.add_card(card)

    def add_card(self, card: MediaCard) -> None:
        self.cards.append(card)
        card.setParent(self)
        self._reflow(force=True)

    def clear(self) -> None:
        for card in self.cards:
            self._grid.removeWidget(card)
            card.setParent(None)
            card.deleteLater()
        self.cards.clear()
        self._columns = 0

    def visible_cards(self) -> list[MediaCard]:
        return [card for card in self.cards if not card.isHidden()]

    # ── Layout ──────────────────────────────────────────────────────────────
    def minimumSizeHint(self) -> QSize:  # noqa: N802 (Qt naming)
        """Never lock the grid wider than one card.

        The layout's minimum width grows with the current column count. If that
        propagated to the enclosing scroll area, the page could not shrink
        again and the last column would be clipped after resizing down.
        """
        return QSize(self._min_width, super().minimumSizeHint().height())

    def resizeEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        super().resizeEvent(event)
        self._reflow()

    def _reflow(self, force: bool = False) -> None:
        available = max(self.width(), self._min_width)
        spacing = self._grid.horizontalSpacing()
        columns = max(1, (available + spacing) // (self._min_width + spacing))
        if columns == self._columns and not force:
            return
        self._columns = columns

        # Equal column stretch keeps every card the same width and guarantees
        # the grid never grows wider than the viewport.
        for column in range(max(self._columns, 0) + 1):
            self._grid.setColumnStretch(column, 1 if column < columns else 0)

        for index, card in enumerate(self.cards):
            self._grid.addWidget(card, index // columns, index % columns)
