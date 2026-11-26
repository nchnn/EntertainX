"""The large rotating feature banner at the top of the Movies / TV pages."""

from __future__ import annotations

from PySide6.QtCore import (
    QEasingCurve,
    QRectF,
    QSize,
    Qt,
    QTimer,
    QVariantAnimation,
    Signal,
)
from PySide6.QtGui import QColor, QPainter, QPixmap
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
from ui.components import motion
from ui.components.artwork import (
    draw_cover,
    fill_horizontal_scrim,
    fill_vertical_scrim,
    rounded_path,
)
from ui.components.icons import make_icon
from ui.components.skeleton import pulse_clock, pulse_color

ROTATE_MS = 9000
FADE_MS = 700
MAX_SLIDES = 6
OVERVIEW_CHARS = 230


def trim(text: str, limit: int = OVERVIEW_CHARS) -> str:
    """Shorten ``text`` at a word boundary, adding an ellipsis."""
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0].rstrip(",.;:- ") + "\u2026"


class _Dots(QWidget):
    """Clickable page indicator."""

    selected = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._count = 0
        self._current = 0
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def configure(self, count: int, current: int) -> None:
        self._count = count
        self._current = current
        self.setFixedSize(max(1, count) * 22 + 4, 22)
        self.setVisible(count > 1)
        self.update()

    def set_current(self, index: int) -> None:
        self._current = index
        self.update()

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton and self._count:
            self.selected.emit(min(self._count - 1, int(event.position().x() // 22)))
        super().mouseReleaseEvent(event)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setPen(Qt.PenStyle.NoPen)
        for index in range(self._count):
            active = index == self._current
            if active:
                painter.setBrush(QColor(theme.PRIMARY))
            else:
                color = QColor("#FFFFFF")
                color.setAlphaF(0.4)
                painter.setBrush(color)
            width = 16.0 if active else 7.0
            painter.drawRoundedRect(
                QRectF(2 + index * 22 + (16 - width) / 2 + 3, 8, width, 6), 3, 3
            )
        painter.end()


class HeroBanner(QWidget):
    play_clicked = Signal(object)   # MediaItem
    info_clicked = Signal(object)

    def __init__(self, store: ImageStore | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._store = store
        self._items: list[MediaItem] = []
        self._index = 0
        self._art: dict[int, QPixmap] = {}
        self._shown: QPixmap | None = None
        self._previous: QPixmap | None = None
        self._blend = 1.0
        self._loading = True
        self._fade: QVariantAnimation | None = None
        self._pulse_held = False

        self.setMinimumHeight(360)
        self.setFixedHeight(theme.HERO_HEIGHT)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setMouseTracking(True)

        # Text block, anchored bottom-left.
        self._info = QWidget(self)
        self._info.setFixedWidth(580)
        info = QVBoxLayout(self._info)
        info.setContentsMargins(0, 0, 0, 0)
        info.setSpacing(theme.SPACE_MD)

        self._chips = QHBoxLayout()
        self._chips.setSpacing(theme.SPACE_SM)
        self.kind_chip = self._chip()
        self.rank_chip = self._chip()
        self._chips.addWidget(self.kind_chip)
        self._chips.addWidget(self.rank_chip)
        self._chips.addStretch(1)
        info.addLayout(self._chips)

        self.title_label = QLabel("")
        self.title_label.setProperty("role", "heroTitle")
        self.title_label.setWordWrap(True)
        info.addWidget(self.title_label)

        self.meta_label = QLabel("")
        self.meta_label.setProperty("role", "heroMeta")
        info.addWidget(self.meta_label)

        self.overview_label = QLabel("")
        self.overview_label.setProperty("role", "heroOverview")
        self.overview_label.setWordWrap(True)
        info.addWidget(self.overview_label)

        info.addSpacing(theme.SPACE_SM)
        buttons = QHBoxLayout()
        buttons.setSpacing(theme.SPACE_MD)
        self.play_button = QPushButton("  Play")
        self.play_button.setProperty("variant", "hero")
        self.play_button.setIcon(make_icon("play", theme.TEXT_ON_ACCENT, 18))
        self.play_button.setIconSize(QSize(18, 18))
        self.play_button.setMinimumWidth(130)
        self.play_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.play_button.clicked.connect(lambda: self._emit(self.play_clicked))
        buttons.addWidget(self.play_button)

        self.info_button = QPushButton("More Info")
        self.info_button.setProperty("variant", "glass")
        self.info_button.setMinimumWidth(132)
        self.info_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.info_button.clicked.connect(lambda: self._emit(self.info_clicked))
        buttons.addWidget(self.info_button)
        buttons.addStretch(1)
        info.addLayout(buttons)

        self.dots = _Dots(self)
        self.dots.selected.connect(self.show_index)

        self._timer = QTimer(self)
        self._timer.setInterval(ROTATE_MS)
        self._timer.timeout.connect(self._advance)

        pulse_clock().tick.connect(self._on_tick)
        self._info.hide()
        self.dots.hide()

    # ── Public API ──────────────────────────────────────────────────────────
    @property
    def current_item(self) -> MediaItem | None:
        return self._items[self._index] if self._items else None

    @property
    def items(self) -> list[MediaItem]:
        return list(self._items)

    def set_loading(self) -> None:
        self._items = []
        self._art = {}
        self._shown = self._previous = None
        self._loading = True
        self._timer.stop()
        self._info.hide()
        self.dots.hide()
        self._sync_pulse()
        self.update()

    def set_items(self, items: list[MediaItem]) -> None:
        """Feature up to six titles; ones without any artwork are skipped."""
        slides = [item for item in items if item.art_url()][:MAX_SLIDES]
        self._items = slides
        self._art = {}
        self._loading = True
        self._index = 0
        self._shown = self._previous = None
        self.dots.configure(len(slides), 0)
        if not slides:
            self._info.hide()
            self._sync_pulse()
            self.update()
            return
        self._apply_text(slides[0], 0)
        self._info.show()
        self._layout_overlay()
        self._request_art(0)
        if len(slides) > 1:
            self._request_art(1)
        self._restart_timer()

    def show_index(self, index: int) -> None:
        if not self._items or (index == self._index and self._shown is not None):
            return
        index %= len(self._items)
        self._index = index
        self.dots.set_current(index)
        item = self._items[index]
        motion.swap(self._info, lambda: self._apply_text(item, index))
        self._start_fade(self._art.get(index))
        self._request_art(index)
        nxt = (index + 1) % len(self._items)
        if nxt != index:
            self._request_art(nxt)
        self._restart_timer()

    # ── Slides ──────────────────────────────────────────────────────────────
    def _chip(self) -> QLabel:
        chip = QLabel("")
        chip.setProperty("role", "heroChip")
        chip.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        return chip

    def _apply_text(self, item: MediaItem, index: int) -> None:
        self.kind_chip.setText(item.kind_label.upper())
        self.rank_chip.setText(f"#{index + 1} TRENDING")
        self.title_label.setText(item.title)
        parts = []
        if item.rating > 0:
            parts.append(f"\u2605 {item.rating:.1f}")
        if item.year:
            parts.append(item.year)
        genres = "  \xb7  ".join(item.genre_names[:3])
        if genres:
            parts.append(genres)
        self.meta_label.setText("   \xb7   ".join(parts))
        self.overview_label.setText(trim(item.overview))
        self.overview_label.setVisible(bool(item.overview))
        self.play_button.setAccessibleName(f"Play trailer for {item.title}")
        self.info_button.setAccessibleName(f"More info about {item.title}")
        self._layout_overlay()

    def _emit(self, signal: Signal) -> None:
        if self.current_item is not None:
            signal.emit(self.current_item)

    def _request_art(self, index: int) -> None:
        if index in self._art or index >= len(self._items):
            return
        url = self._items[index].backdrop_url("w1280") or self._items[index].poster_url("w780")
        (self._store or get_store()).request(
            url, 1280, lambda pixmap, i=index: self._on_art(i, pixmap), owner=self
        )

    def _on_art(self, index: int, pixmap: QPixmap | None) -> None:
        if pixmap is None or pixmap.isNull():
            return
        self._art[index] = pixmap
        if index == self._index:
            self._start_fade(pixmap)

    def _start_fade(self, pixmap: QPixmap | None) -> None:
        if pixmap is None:
            return
        if self._fade is not None:
            self._fade.stop()
            self._fade = None
        self._previous = self._shown
        self._shown = pixmap
        self._loading = False
        self._sync_pulse()
        if self._previous is None or not motion.motion_enabled():
            self._previous = None
            self._blend = 1.0
            self.update()
            return
        self._blend = 0.0
        fade = QVariantAnimation(self)
        fade.setStartValue(0.0)
        fade.setEndValue(1.0)
        fade.setDuration(FADE_MS)
        fade.setEasingCurve(QEasingCurve.Type.InOutCubic)
        fade.valueChanged.connect(self._on_fade)
        fade.finished.connect(self._on_fade_done)
        self._fade = fade
        fade.start()

    def _on_fade(self, value) -> None:
        self._blend = float(value)
        self.update()

    def _on_fade_done(self) -> None:
        self._previous = None
        self._blend = 1.0
        self._fade = None
        self.update()

    # ── Rotation ────────────────────────────────────────────────────────────
    def _restart_timer(self) -> None:
        self._timer.stop()
        if len(self._items) > 1 and motion.motion_enabled() and self.isVisible():
            self._timer.start()

    def _advance(self) -> None:
        if self._items:
            self.show_index((self._index + 1) % len(self._items))

    def _sync_pulse(self) -> None:
        """Hold the shared pulse clock exactly while the placeholder is showing."""
        wanted = self._loading and self.isVisible()
        if wanted and not self._pulse_held:
            pulse_clock().acquire()
            self._pulse_held = True
        elif not wanted and self._pulse_held:
            pulse_clock().release()
            self._pulse_held = False

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        self._sync_pulse()
        self._restart_timer()

    def hideEvent(self, event) -> None:  # noqa: N802
        super().hideEvent(event)
        self._sync_pulse()
        self._timer.stop()

    def enterEvent(self, event) -> None:  # noqa: N802
        super().enterEvent(event)
        self._timer.stop()

    def leaveEvent(self, event) -> None:  # noqa: N802
        super().leaveEvent(event)
        self._restart_timer()

    def _on_tick(self, _phase: float) -> None:
        if self._loading and self.isVisible():
            self.update()

    # ── Layout and painting ─────────────────────────────────────────────────
    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._layout_overlay()

    def _layout_overlay(self) -> None:
        layout = self._info.layout()
        width = self._info.width()
        height = (
            layout.heightForWidth(width)
            if layout is not None and layout.hasHeightForWidth()
            else (layout.sizeHint().height() if layout is not None else 0)
        )
        self._info.setFixedHeight(max(1, height))
        self._info.move(44, max(24, self.height() - self._info.height() - 40))
        self.dots.move(
            self.width() - self.dots.width() - 32, self.height() - self.dots.height() - 30
        )

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        bounds = QRectF(self.rect())
        painter.setClipPath(rounded_path(bounds, float(theme.RADIUS_XL)))
        painter.fillRect(bounds, QColor(theme.BG_CARD))

        if self._shown is None:
            painter.fillRect(bounds, pulse_color(pulse_clock().phase))
        else:
            if self._previous is not None:
                draw_cover(painter, bounds, self._previous, 0.7, 0.3)
            painter.setOpacity(self._blend)
            draw_cover(painter, bounds, self._shown, 0.7, 0.3)
            painter.setOpacity(1.0)

        fill_horizontal_scrim(painter, bounds, 0.78, 0.92, theme.BG)
        fill_vertical_scrim(painter, bounds, 0.55, 0.62, theme.BG)
        painter.end()
