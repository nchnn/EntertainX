"""A horizontally scrolling shelf of title tiles with a title and edge arrows."""

from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QSize, Qt, QVariantAnimation, Signal
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
from ui.components.icons import make_icon
from ui.components.motion import motion_enabled
from ui.components.skeleton import SkeletonTile
from ui.components.title_tile import TitleTile

GAP = 14
STEP = theme.TILE_WIDTH + GAP
SKELETON_COUNT = 8
TOP_TEN = 10


def _discard(widget: QWidget) -> None:
    widget.hide()
    widget.setParent(None)
    widget.deleteLater()


class _Viewport(QWidget):
    """Clips the moving track and forwards sideways wheel/trackpad scrolling."""

    scrolled_by = Signal(int)
    resized = Signal()

    def wheelEvent(self, event) -> None:  # noqa: N802
        delta = event.angleDelta()
        if delta.x() != 0 and abs(delta.x()) >= abs(delta.y()):
            self.scrolled_by.emit(-delta.x())
            event.accept()
        else:
            event.ignore()

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self.resized.emit()


class MediaRow(QWidget):
    tile_entered = Signal(object)
    tile_left = Signal(object)
    item_activated = Signal(object)
    scrolled = Signal()
    retry_requested = Signal()

    def __init__(
        self,
        title: str,
        badge: str = "",
        store: ImageStore | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.badge = badge
        self.items: list[MediaItem] = []
        self.tiles: list[TitleTile] = []
        self._store = store
        self._offset = 0.0
        self._hovering = False
        self._anim: QVariantAnimation | None = None
        self._placeholders: list[QWidget] = []
        self._notice: QWidget | None = None

        column = QVBoxLayout(self)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(theme.SPACE_MD)

        self.title_label = QLabel(title)
        self.title_label.setProperty("role", "sectionTitle")
        column.addWidget(self.title_label)

        self._viewport = _Viewport()
        self._viewport.setFixedHeight(theme.TILE_HEIGHT + 2)
        self._viewport.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._viewport.scrolled_by.connect(lambda dx: self.set_offset(self._offset + dx))
        self._viewport.resized.connect(self._on_resized)
        column.addWidget(self._viewport)

        self._track = QWidget(self._viewport)
        self._track.move(0, 0)

        self.left_arrow = self._make_arrow(rotate=180, name="Scroll left")
        self.right_arrow = self._make_arrow(rotate=0, name="Scroll right")
        self.left_arrow.clicked.connect(lambda: self.scroll_page(-1))
        self.right_arrow.clicked.connect(lambda: self.scroll_page(1))

        self.setMouseTracking(True)
        self._update_arrows()

    @property
    def title(self) -> str:
        return self.title_label.text()

    def minimumSizeHint(self) -> QSize:  # noqa: N802
        return QSize(theme.TILE_WIDTH, super().minimumSizeHint().height())

    # ── Content states ──────────────────────────────────────────────────────
    def _clear(self) -> None:
        self._stop_animation()
        for tile in self.tiles:
            _discard(tile)
        for widget in self._placeholders:
            _discard(widget)
        if self._notice is not None:
            _discard(self._notice)
        self.tiles = []
        self._placeholders = []
        self._notice = None
        self.items = []
        self._offset = 0.0
        self._track.move(0, 0)

    def set_loading(self) -> None:
        self._clear()
        for index in range(SKELETON_COUNT):
            tile = SkeletonTile(parent=self._track)
            tile.move(index * STEP, 0)
            tile.show()
            self._placeholders.append(tile)
        self._track.resize(SKELETON_COUNT * STEP - GAP, theme.TILE_HEIGHT)
        self._track.show()
        self._update_arrows()

    def set_items(self, items: list[MediaItem]) -> None:
        self._clear()
        self.items = list(items)
        if not items:
            self._show_notice("Nothing to show here right now.", retry=False)
            return
        for index, item in enumerate(items):
            label = ""
            if self.badge == "top10" and index < TOP_TEN:
                label = "TOP 10"
            elif self.badge == "new":
                label = "NEW"
            tile = TitleTile(item, label, parent=self._track)
            tile.move(index * STEP, 0)
            tile.entered.connect(self.tile_entered)
            tile.left.connect(self.tile_left)
            tile.activated.connect(self.item_activated)
            tile.focused.connect(self._reveal)
            tile.show()
            self.tiles.append(tile)
        self._track.resize(len(items) * STEP - GAP, theme.TILE_HEIGHT)
        self._track.show()
        self.ensure_images()
        self._update_arrows()

    def set_error(self, message: str) -> None:
        self._clear()
        self._show_notice(message, retry=True)

    def _show_notice(self, message: str, retry: bool) -> None:
        box = QWidget(self._viewport)
        row = QHBoxLayout(box)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(theme.SPACE_MD)
        text = QLabel(message)
        text.setProperty("role", "muted")
        text.setWordWrap(True)
        row.addWidget(text, 1)
        if retry:
            button = QPushButton("Try again")
            button.setProperty("variant", "subtle")
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(self.retry_requested)
            row.addWidget(button)
        box.setGeometry(0, 0, self._viewport.width(), theme.TILE_HEIGHT)
        box.show()
        self._notice = box
        self._update_arrows()

    # ── Artwork ─────────────────────────────────────────────────────────────
    def ensure_images(self) -> None:
        """Load artwork for tiles in (or next to) view; the rest wait."""
        store = self._store or get_store()
        low = self._offset - STEP
        high = self._offset + self._viewport.width() + STEP
        for index, tile in enumerate(self.tiles):
            if low <= index * STEP <= high:
                tile.load_image(store)

    # ── Scrolling ───────────────────────────────────────────────────────────
    def max_offset(self) -> float:
        return float(max(0, self._track.width() - self._viewport.width())) if self.tiles else 0.0

    def offset(self) -> float:
        return self._offset

    def set_offset(self, value: float) -> None:
        value = max(0.0, min(float(value), self.max_offset()))
        if value == self._offset:
            return
        self._offset = value
        self._track.move(-round(value), 0)
        self._update_arrows()
        self.ensure_images()
        self.scrolled.emit()

    def scroll_page(self, direction: int) -> None:
        columns = max(1, (self._viewport.width() + GAP) // STEP - 1)
        target = self._offset + direction * columns * STEP
        target = round(target / STEP) * STEP
        self._scroll_to(max(0.0, min(float(target), self.max_offset())))

    def _reveal(self, tile: TitleTile) -> None:
        """Keyboard focus moved to ``tile``; bring it fully into view."""
        left = tile.x()
        right = left + tile.width()
        if left < self._offset:
            self._scroll_to(float(left))
        elif right > self._offset + self._viewport.width():
            self._scroll_to(float(right - self._viewport.width()))

    def _stop_animation(self) -> None:
        if self._anim is not None:
            self._anim.stop()
            self._anim = None

    def _scroll_to(self, target: float) -> None:
        self._stop_animation()
        if not motion_enabled():
            self.set_offset(target)
            return
        animation = QVariantAnimation(self)
        animation.setStartValue(self._offset)
        animation.setEndValue(target)
        animation.setDuration(420)
        animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        animation.valueChanged.connect(lambda value: self.set_offset(float(value)))
        self._anim = animation
        animation.start()

    # ── Arrows ──────────────────────────────────────────────────────────────
    def _make_arrow(self, rotate: int, name: str) -> QPushButton:
        button = QPushButton(self._viewport)
        button.setProperty("variant", "rowArrow")
        button.setFixedSize(44, 44)
        button.setIcon(make_icon("chevron", theme.TEXT_PRIMARY, 20, rotate=rotate))
        button.setIconSize(QSize(20, 20))
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setAccessibleName(name)
        button.setToolTip(name)
        button.hide()
        return button

    def _on_resized(self) -> None:
        self._offset = max(0.0, min(self._offset, self.max_offset()))
        self._track.move(-round(self._offset), 0)
        if self._notice is not None:
            self._notice.setGeometry(0, 0, self._viewport.width(), theme.TILE_HEIGHT)
        self._update_arrows()
        self.ensure_images()

    def _update_arrows(self) -> None:
        y = (self._viewport.height() - 44) // 2
        self.left_arrow.move(8, y)
        self.right_arrow.move(self._viewport.width() - 52, y)
        self.left_arrow.setVisible(self._hovering and self._offset > 0)
        self.right_arrow.setVisible(
            self._hovering and self._offset < self.max_offset() - 0.5
        )
        self.left_arrow.raise_()
        self.right_arrow.raise_()

    def enterEvent(self, event) -> None:  # noqa: N802
        super().enterEvent(event)
        self._hovering = True
        self._update_arrows()

    def leaveEvent(self, event) -> None:  # noqa: N802
        super().leaveEvent(event)
        self._hovering = False
        self._update_arrows()
