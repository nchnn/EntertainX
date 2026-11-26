"""A landscape title tile: artwork, title, year/rating, and an optional badge."""

from __future__ import annotations

from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QColor, QKeyEvent, QLinearGradient, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QWidget

from api.images import ImageStore, get_store
from api.movies import MediaItem
from theme import theme_manager as theme
from ui.components.artwork import (
    draw_cover,
    fill_vertical_scrim,
    pill,
    rounded_path,
)
from ui.components.icons import make_icon


def meta_line(item: MediaItem) -> str:
    """``"2026  |  7.8"``, skipping whatever TMDB did not provide."""
    parts = []
    if item.year:
        parts.append(item.year)
    if item.rating > 0:
        parts.append(f"\u2605 {item.rating:.1f}")
    return "  \xb7  ".join(parts)


class TitleTile(QWidget):
    entered = Signal(object)   # the tile, after the pointer enters
    left = Signal(object)
    focused = Signal(object)
    activated = Signal(object)  # the MediaItem

    def __init__(
        self,
        item: MediaItem,
        badge: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.item = item
        self.badge = badge
        self.pixmap: QPixmap | None = None
        self._requested = False
        self._hover = False

        self.setFixedSize(theme.TILE_WIDTH, theme.TILE_HEIGHT)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAccessibleName(item.title)

    # ── Artwork ─────────────────────────────────────────────────────────────
    def load_image(self, store: ImageStore | None = None) -> None:
        if self._requested:
            return
        self._requested = True
        (store or get_store()).request(
            self.item.art_url("w780"),
            theme.TILE_WIDTH * 2,
            self._on_pixmap,
            owner=self,
        )

    def _on_pixmap(self, pixmap: QPixmap | None) -> None:
        self.pixmap = pixmap
        self.update()

    def update_item(self, item: MediaItem, store: ImageStore | None = None) -> None:
        """Update tile with refreshed MediaItem (e.g. English backdrop) and reload artwork."""
        if (
            item.backdrop_path != self.item.backdrop_path
            or item.poster_path != self.item.poster_path
        ):
            self.item = item
            self._requested = False
            self.load_image(store)

    # ── Pointer and keyboard ────────────────────────────────────────────────
    def enterEvent(self, event) -> None:  # noqa: N802
        super().enterEvent(event)
        self._hover = True
        self.update()
        self.entered.emit(self)

    def leaveEvent(self, event) -> None:  # noqa: N802
        super().leaveEvent(event)
        self._hover = False
        self.update()
        self.left.emit(self)

    def focusInEvent(self, event) -> None:  # noqa: N802
        super().focusInEvent(event)
        self.update()
        self.focused.emit(self)

    def focusOutEvent(self, event) -> None:  # noqa: N802
        super().focusOutEvent(event)
        self.update()

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if (
            event.button() == Qt.MouseButton.LeftButton
            and self.rect().contains(event.position().toPoint())
        ):
            self.activated.emit(self.item)
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802
        if event.key() in (
            Qt.Key.Key_Return,
            Qt.Key.Key_Enter,
            Qt.Key.Key_Space,
        ):
            self.activated.emit(self.item)
            return
        super().keyPressEvent(event)

    # ── Painting ────────────────────────────────────────────────────────────
    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        bounds = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        radius = float(theme.RADIUS_MD)
        painter.setClipPath(rounded_path(bounds, radius))

        if self.pixmap is not None and not self.pixmap.isNull():
            draw_cover(painter, bounds, self.pixmap)
        else:
            ground = QLinearGradient(bounds.topLeft(), bounds.bottomRight())
            ground.setColorAt(0.0, QColor(theme.BG_ELEVATED))
            ground.setColorAt(1.0, QColor(theme.BG_CARD))
            painter.fillRect(bounds, ground)
            glyph = make_icon("film", theme.TEXT_DISABLED, 30).pixmap(30, 30)
            painter.drawPixmap(
                int(bounds.center().x() - 15), int(bounds.center().y() - 26), glyph
            )

        if self.badge:
            pill(
                painter,
                bounds.left() + 10,
                bounds.top() + 10,
                self.badge,
                QColor(theme.PRIMARY),
                QColor(theme.TEXT_ON_ACCENT),
            )

        if self._hover:
            painter.fillRect(bounds, QColor(255, 255, 255, 14))

        painter.setClipping(False)
        if self._hover or self.hasFocus():
            ring = QColor(theme.PRIMARY if self.hasFocus() else theme.TEXT_PRIMARY)
            painter.setPen(QPen(ring, 2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(rounded_path(bounds, radius))
        painter.end()
