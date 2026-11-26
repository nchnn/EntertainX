"""GameCard: a clickable thumbnail card for one catalog entry.

Loads the cover image on a background thread via ImageStore and falls
back to the Lucide gamepad icon when the network is unavailable.
"""

from __future__ import annotations

from functools import lru_cache

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from api.games import GameEntry
from api.images import get_store
from theme import theme_manager as theme
from ui.components.icons import make_icon
from ui.components.layout import ElidedLabel

THUMB_W = 200
THUMB_H = 130


@lru_cache(maxsize=8)
def _placeholder_pixmap(color: str) -> QPixmap:
    """One shared placeholder per colour; 921 cards must not re-render the SVG."""
    return make_icon("gamepad", color, 32).pixmap(32, 32)


class GameCard(QFrame):
    """Clickable poster card for one GameEntry."""

    activated = Signal(object)  # emits GameEntry

    def __init__(self, entry: GameEntry, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._entry = entry
        self._tried_backup = False
        self._thumb_requested = False

        self.setProperty("role", "mediaCard")
        self.setFixedWidth(THUMB_W)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        col = QVBoxLayout(self)
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(0)

        # Thumbnail
        self._thumb = QLabel()
        self._thumb.setFixedSize(THUMB_W, THUMB_H)
        self._thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._thumb.setProperty("role", "thumb")
        self._set_placeholder()
        col.addWidget(self._thumb)

        # Text
        text_box = QVBoxLayout()
        text_box.setContentsMargins(
            theme.SPACE_SM, theme.SPACE_SM, theme.SPACE_SM, theme.SPACE_SM
        )
        text_box.setSpacing(2)

        self._title_lbl = ElidedLabel(entry.name)
        self._title_lbl.setProperty("role", "h3")
        text_box.addWidget(self._title_lbl)

        genre = ", ".join(entry.tags[:2]) if entry.tags else ""
        self._genre_lbl = ElidedLabel(genre)
        self._genre_lbl.setProperty("role", "muted")
        text_box.addWidget(self._genre_lbl)

        col.addLayout(text_box)

    # -- Thumbnail helpers -----------------------------------------------------

    @property
    def thumb_requested(self) -> bool:
        return self._thumb_requested

    def load_thumb(self) -> bool:
        """Request the cover once, when the card scrolls into view.

        Returns True when a request was actually started.
        """
        if self._thumb_requested:
            return False
        self._thumb_requested = True
        get_store().request(
            self._entry.thumbnail_url,
            THUMB_W,
            self._on_thumb,
            owner=self,
        )
        return True

    def _set_placeholder(self) -> None:
        self._thumb.setPixmap(_placeholder_pixmap(theme.TEXT_MUTED))

    def _on_thumb(self, pixmap: QPixmap | None) -> None:
        if pixmap is None:
            if self._tried_backup:
                return
            self._tried_backup = True
            get_store().request(
                self._entry.backup_thumbnail_url,
                THUMB_W,
                self._on_thumb,
                owner=self,
            )
            return

        scaled = pixmap.scaled(
            THUMB_W,
            THUMB_H,
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation,
        )
        # Centre-crop to exact size
        x = max(0, (scaled.width() - THUMB_W) // 2)
        y = max(0, (scaled.height() - THUMB_H) // 2)
        cropped = scaled.copy(x, y, THUMB_W, THUMB_H)
        self._thumb.setPixmap(cropped)
        self._thumb.setStyleSheet(
            f"border-radius: {theme.RADIUS_MD}px; background: transparent;"
        )

    # -- Queries used by filter ------------------------------------------------

    @property
    def entry(self) -> GameEntry:
        return self._entry

    def matches(self, query: str, tag: str = "") -> bool:
        q = query.strip().lower()
        t = tag.strip().lower()
        if t and t not in [x.lower() for x in self._entry.tags]:
            return False
        if not q:
            return True
        return q in self._entry.name.lower()

    # -- Interaction -----------------------------------------------------------

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self.activated.emit(self._entry)
        super().mousePressEvent(event)
