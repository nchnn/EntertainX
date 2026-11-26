"""Top 10 Today panel: 10 ranked tiles with large rank numerals.

The rank number is painted directly onto the tile in an editorial serif font,
bleeding off the left edge the way Netflix's Top 10 row does it. The panel
sits between the hero banner and the first regular shelf.
"""

from __future__ import annotations

from PySide6.QtCore import QPoint, QRectF, QSize, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontMetricsF,
    QKeyEvent,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from api.images import ImageStore, get_store
from api.movies import MediaItem
from theme import theme_manager as theme
from ui.components.artwork import draw_cover, fill_vertical_scrim, rounded_path
from ui.components.icons import make_icon
from ui.components.motion import motion_enabled
from ui.components.skeleton import SkeletonTile

# Tile is taller than a shelf tile to give the numeral room below.
TILE_W = 210
TILE_H = 310
GAP = 12
NUMERAL_SIZE = 220
NUMERAL_OVERLAP = 80
NUMERAL_OVERLAP_10 = 100
SKELETON_COUNT = 10

RANK_FONT_FAMILIES = (
    "Impact",
    "Arial Black",
    "Segoe UI Black",
    "Haettenschweiler",
    "Trebuchet MS",
    "sans-serif",
)


def _rank_font(px: int) -> QFont:
    font = QFont()
    font.setFamilies(list(RANK_FONT_FAMILIES))
    font.setStyleHint(QFont.StyleHint.SansSerif)
    font.setPixelSize(px)
    font.setWeight(QFont.Weight.Black)
    font.setItalic(False)
    return font


class Top10Tile(QWidget):
    """A portrait-ish tile with the rank numeral overlaid at the bottom-left."""

    entered = Signal(object)
    left = Signal(object)
    focused = Signal(object)
    activated = Signal(object)   # MediaItem

    def __init__(
        self,
        rank: int,
        item: MediaItem,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.rank = rank
        self.item = item
        self.pixmap: QPixmap | None = None
        self._requested = False
        self._hover = False
        self.overlap = NUMERAL_OVERLAP_10 if rank == 10 else NUMERAL_OVERLAP

        # Total widget width = tile + room for the numeral on the left.
        self.setFixedSize(TILE_W + self.overlap, TILE_H)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAccessibleName(f"#{rank} {item.title}")

    # ── Artwork ─────────────────────────────────────────────────────────────
    def load_image(self, store: ImageStore | None = None) -> None:
        if self._requested:
            return
        self._requested = True
        url = self.item.poster_url("w500") or self.item.art_url("w780")
        (store or get_store()).request(
            url, TILE_W * 2, self._on_pixmap, owner=self
        )

    def _on_pixmap(self, pixmap: QPixmap | None) -> None:
        self.pixmap = pixmap
        self.update()

    # ── Events ───────────────────────────────────────────────────────────────
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
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
            self.activated.emit(self.item)
            return
        super().keyPressEvent(event)

    # ── Painting ─────────────────────────────────────────────────────────────
    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

        # 1. Rank numeral drawn in the background
        num_text = str(self.rank)
        font = _rank_font(NUMERAL_SIZE if self.rank < 10 else 200)
        metrics = QFontMetricsF(font)
        num_w = metrics.horizontalAdvance(num_text)
        num_x = max(6.0, float(self.overlap - num_w + 14))
        num_y = float(TILE_H - 12)

        path = QPainterPath()
        path.addText(num_x, num_y, font, num_text)

        # Outer dark glow
        glow_pen = QPen(
            QColor(0, 0, 0, 190),
            7,
            Qt.PenStyle.SolidLine,
            Qt.PenCapStyle.RoundCap,
            Qt.PenJoinStyle.RoundJoin,
        )
        painter.setPen(glow_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(path)

        # Metallic chrome gradient fill
        grad = QLinearGradient(num_x, num_y - 180, num_x, num_y)
        grad.setColorAt(0.0, QColor("#E6E9F0"))
        grad.setColorAt(0.35, QColor("#8E98A5"))
        grad.setColorAt(0.70, QColor("#3A3F4D"))
        grad.setColorAt(1.0, QColor("#1B1D24"))

        # Outline stroke with metallic sheen
        stroke_pen = QPen(
            QColor("#B0B9C6"),
            3.5,
            Qt.PenStyle.SolidLine,
            Qt.PenCapStyle.RoundCap,
            Qt.PenJoinStyle.RoundJoin,
        )
        painter.setPen(stroke_pen)
        painter.setBrush(grad)
        painter.drawPath(path)

        # 2. Foreground poster card
        tile = QRectF(self.overlap, 0, TILE_W, TILE_H)
        radius = float(theme.RADIUS_MD)

        # Soft cast shadow from card onto numeral
        for s in range(6, 0, -1):
            shadow = QColor(0, 0, 0, 22)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(shadow)
            painter.drawRoundedRect(
                tile.adjusted(-s * 1.2, -s * 0.4, s * 1.2, s * 0.8),
                radius + s,
                radius + s,
            )

        painter.setClipPath(rounded_path(tile, radius))

        if self.pixmap is not None and not self.pixmap.isNull():
            draw_cover(painter, tile, self.pixmap, 0.5, 0.0)
        else:
            ground = QLinearGradient(tile.topLeft(), tile.bottomRight())
            ground.setColorAt(0.0, QColor(theme.BG_ELEVATED))
            ground.setColorAt(1.0, QColor(theme.BG_CARD))
            painter.fillRect(tile, ground)

        if self._hover:
            painter.fillRect(tile, QColor(255, 255, 255, 18))

        painter.setClipping(False)

        # Hover / focus ring on the tile.
        if self._hover or self.hasFocus():
            ring = QColor(theme.PRIMARY if self.hasFocus() else theme.TEXT_PRIMARY)
            painter.setPen(QPen(ring, 2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(
                rounded_path(tile.adjusted(0.5, 0.5, -0.5, -0.5), radius)
            )

        painter.end()


class Top10Panel(QWidget):
    """Horizontally scrolling strip of 10 ranked tiles with a section heading."""

    tile_entered = Signal(object)   # Top10Tile
    tile_left = Signal(object)
    item_activated = Signal(object)  # MediaItem

    def __init__(
        self,
        label: str = "Top 10 Today",
        store: ImageStore | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._store = store
        self._tiles: list[Top10Tile] = []
        self._offset = 0.0
        self._hovering = False

        column = QVBoxLayout(self)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(theme.SPACE_MD)

        # Section header with accent rule.
        header_row = QHBoxLayout()
        header_row.setSpacing(theme.SPACE_MD)
        rule = QWidget()
        rule.setFixedSize(4, 22)
        rule.setProperty("role", "accentRule")
        self._title_label = QLabel(label)
        self._title_label.setProperty("role", "sectionTitle")
        sub = QLabel("Updated daily")
        sub.setProperty("role", "muted")
        header_row.addWidget(rule)
        header_row.addWidget(self._title_label)
        header_row.addWidget(sub)
        header_row.addStretch(1)
        column.addLayout(header_row)

        # Scrolling viewport.
        from ui.components.video.media_shelf import _Viewport  # reuse the clip+wheel forwarder
        self._viewport = _Viewport()
        self._viewport.setFixedHeight(TILE_H + 2)
        self._viewport.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        self._viewport.scrolled_by.connect(
            lambda dx: self._set_offset(self._offset + dx)
        )
        self._viewport.resized.connect(self._on_resized)
        column.addWidget(self._viewport)

        self._track = QWidget(self._viewport)
        self._track.move(0, 0)

        # Scroll arrows.
        self._left_arrow = self._make_arrow(180, "Scroll left")
        self._right_arrow = self._make_arrow(0, "Scroll right")
        self._left_arrow.clicked.connect(lambda: self._scroll_page(-1))
        self._right_arrow.clicked.connect(lambda: self._scroll_page(1))

        self._placeholders: list[QWidget] = []
        self._set_loading()

    # ── State ────────────────────────────────────────────────────────────────
    def _set_loading(self) -> None:
        for w in self._placeholders:
            w.hide(); w.setParent(None); w.deleteLater()
        self._placeholders = []
        step = TILE_W + NUMERAL_OVERLAP + GAP
        for i in range(SKELETON_COUNT):
            sk = SkeletonTile(
                TILE_W + NUMERAL_OVERLAP,
                TILE_H,
                rank=i + 1,
                overlap=NUMERAL_OVERLAP,
                parent=self._track,
            )
            sk.move(i * step, 0)
            sk.show()
            self._placeholders.append(sk)
        self._track.resize(SKELETON_COUNT * step - GAP, TILE_H)
        self._track.show()
        self._update_arrows()

    def set_items(self, items: list[MediaItem]) -> None:
        for w in self._placeholders:
            w.hide(); w.setParent(None); w.deleteLater()
        self._placeholders = []
        for tile in self._tiles:
            tile.hide(); tile.setParent(None); tile.deleteLater()
        self._tiles = []
        self._offset = 0.0
        self._track.move(0, 0)

        limited = items[:10]
        store = self._store or get_store()
        x = 0
        for rank, item in enumerate(limited, start=1):
            tile = Top10Tile(rank, item, parent=self._track)
            tile.move(x, 0)
            x += tile.width() + GAP
            tile.entered.connect(self.tile_entered)
            tile.left.connect(self.tile_left)
            tile.activated.connect(self.item_activated)
            tile.load_image(store)
            tile.show()
            self._tiles.append(tile)
        self._track.resize(max(1, x - GAP), TILE_H)
        self._track.show()
        self._update_arrows()

    def set_error(self, _message: str) -> None:
        """On error silently hide the panel; the main shelf still shows."""
        self.setVisible(False)

    # ── Scrolling ────────────────────────────────────────────────────────────
    def _max_offset(self) -> float:
        return float(max(0, self._track.width() - self._viewport.width()))

    def _set_offset(self, value: float) -> None:
        value = max(0.0, min(float(value), self._max_offset()))
        if value == self._offset:
            return
        self._offset = value
        self._track.move(-round(value), 0)
        self._update_arrows()

    def _scroll_page(self, direction: int) -> None:
        avg_step = TILE_W + NUMERAL_OVERLAP + GAP
        cols = max(1, (self._viewport.width() + GAP) // avg_step - 1)
        target = self._offset + direction * cols * avg_step
        self._set_offset(max(0.0, min(float(target), self._max_offset())))

    def _on_resized(self) -> None:
        self._offset = max(0.0, min(self._offset, self._max_offset()))
        self._track.move(-round(self._offset), 0)
        self._update_arrows()

    # ── Arrows ───────────────────────────────────────────────────────────────
    def _make_arrow(self, rotate: int, name: str) -> QPushButton:
        btn = QPushButton(self._viewport)
        btn.setProperty("variant", "rowArrow")
        btn.setFixedSize(44, 44)
        btn.setIcon(make_icon("chevron", theme.TEXT_PRIMARY, 20, rotate=rotate))
        btn.setIconSize(QSize(20, 20))
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setAccessibleName(name)
        btn.hide()
        return btn

    def _update_arrows(self) -> None:
        y = (self._viewport.height() - 44) // 2
        self._left_arrow.move(8, y)
        self._right_arrow.move(self._viewport.width() - 52, y)
        self._left_arrow.setVisible(self._hovering and self._offset > 0)
        self._right_arrow.setVisible(
            self._hovering and self._offset < self._max_offset() - 0.5
        )
        self._left_arrow.raise_()
        self._right_arrow.raise_()

    def enterEvent(self, event) -> None:  # noqa: N802
        super().enterEvent(event)
        self._hovering = True
        self._update_arrows()

    def leaveEvent(self, event) -> None:  # noqa: N802
        super().leaveEvent(event)
        self._hovering = False
        self._update_arrows()
