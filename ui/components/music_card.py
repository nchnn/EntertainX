"""Mini music-player cards: painted album art, play disc, and progress."""

from __future__ import annotations

from PySide6.QtCore import QRect, QRectF, QSize, Qt, QVariantAnimation, Signal
from PySide6.QtGui import (
    QColor,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
)
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from theme import theme_manager as theme
from ui.components.icons import make_icon
from ui.components.surfaces import ElidedLabel

DEFAULT_TRACK_MS = 180_000


def duration_ms(text: str) -> int:
    """Parse ``"m:ss"`` or ``"h:mm:ss"`` into milliseconds.

    Empty or malformed text falls back to three minutes so a bad sample entry
    can never stop the card from building.
    """
    parts = text.strip().split(":")
    if len(parts) not in (2, 3) or not all(part.isdigit() for part in parts):
        return DEFAULT_TRACK_MS
    numbers = [int(part) for part in parts]
    if any(value >= 60 for value in numbers[-2:]):
        return DEFAULT_TRACK_MS
    seconds = 0
    for number in numbers:
        seconds = seconds * 60 + number
    return seconds * 1000


def format_duration(ms: int) -> str:
    """Render milliseconds as ``"m:ss"``, clamped at zero."""
    total_seconds = max(0, ms) // 1000
    minutes, seconds = divmod(total_seconds, 60)
    return f"{minutes}:{seconds:02d}"


class PlayerProgress(QWidget):
    """Thin rounded bar showing preview progress from 0.0 to 1.0."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._value = 0.0
        self.setFixedHeight(4)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def value(self) -> float:
        return self._value

    def set_value(self, value: float) -> None:
        clamped = min(1.0, max(0.0, float(value)))
        if clamped != self._value:
            self._value = clamped
            self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setPen(Qt.PenStyle.NoPen)
        radius = self.height() / 2

        painter.setBrush(QColor(theme.BORDER))
        painter.drawRoundedRect(self.rect(), radius, radius)

        width = int(self.width() * self._value)
        if width > 0:
            painter.setBrush(QColor(theme.PRIMARY))
            painter.drawRoundedRect(QRect(0, 0, width, self.height()), radius, radius)
        painter.end()


class AlbumArt(QWidget):
    """Painted sleeve: a pink gradient with a dark vinyl disc peeking out."""

    def __init__(self, seed: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._side = 1 if sum(ord(char) for char in seed) % 2 == 0 else -1
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setMinimumHeight(170)

    def disc_side(self) -> int:
        """Deterministic disc side (``-1`` left, ``1`` right) for this sleeve."""
        return self._side

    def paintEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        bounds = QRectF(self.rect())
        radius = float(theme.RADIUS_MD)
        clip = QPainterPath()
        clip.addRoundedRect(bounds, radius, radius)
        painter.setClipPath(clip)

        sleeve = QLinearGradient(bounds.topLeft(), bounds.bottomRight())
        sleeve.setColorAt(0.0, QColor(theme.SECONDARY))
        sleeve.setColorAt(1.0, QColor(theme.ACCENT_PRESSED))
        painter.fillRect(bounds, sleeve)

        diameter = min(bounds.width(), bounds.height()) * 0.76
        center_x = bounds.width() * (0.5 + 0.22 * self._side)
        center = QRectF(
            center_x - diameter / 2,
            bounds.height() / 2 - diameter / 2,
            diameter,
            diameter,
        )

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(theme.TEXT_ON_ACCENT))
        painter.drawEllipse(center)

        groove = QColor(theme.SECONDARY)
        groove.setAlphaF(0.24)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(groove, 1.0))
        for factor in (0.86, 0.72, 0.58):
            inset = diameter * (1 - factor) / 2
            painter.drawEllipse(center.adjusted(inset, inset, -inset, -inset))

        label = diameter * 0.17
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(theme.PRIMARY))
        painter.drawEllipse(center.center(), label, label)

        hole = max(2.0, diameter * 0.026)
        painter.setBrush(QColor(theme.TEXT_ON_ACCENT))
        painter.drawEllipse(center.center(), hole, hole)
        painter.end()


class MusicPlayerCard(QFrame):
    """Album card with painted art, a play disc, and preview progress."""

    play_toggled = Signal(bool)

    def __init__(
        self,
        title: str,
        subtitle: str,
        meta: str = "",
        length: str = "",
        category: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.category = category
        self._title = title
        self._playing = False
        self._track_ms = duration_ms(length)
        self._progress = 0.0

        self.setProperty("role", "mediaCard")
        self.setMinimumWidth(theme.CARD_MIN_WIDTH)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.setCursor(Qt.CursorShape.ArrowCursor)

        column = QVBoxLayout(self)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(0)

        self._art = AlbumArt(title)
        column.addWidget(self._art)

        overlay = QGridLayout(self._art)
        overlay.setContentsMargins(
            theme.SPACE_MD, theme.SPACE_MD, theme.SPACE_MD, theme.SPACE_MD
        )
        self._button = QPushButton()
        self._button.setProperty("variant", "playDisc")
        self._button.setFixedSize(38, 38)
        self._button.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._button.setIconSize(QSize(16, 16))
        self._button.clicked.connect(self.toggle)
        overlay.addWidget(
            self._button,
            0,
            0,
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom,
        )

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

        for label in (self.title_label, self.subtitle_label, self.meta_label):
            label.setSizePolicy(
                QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred
            )

        self._progress_bar = PlayerProgress()
        text_box.addWidget(self._progress_bar)

        time_row = QHBoxLayout()
        time_row.setContentsMargins(0, 0, 0, 0)
        time_row.setSpacing(theme.SPACE_XS)
        self._elapsed_label = QLabel("0:00")
        self._elapsed_label.setProperty("role", "caption")
        self._total_label = QLabel(format_duration(self._track_ms))
        self._total_label.setProperty("role", "caption")
        time_row.addWidget(self._elapsed_label)
        time_row.addStretch(1)
        time_row.addWidget(self._total_label)
        text_box.addLayout(time_row)

        column.addLayout(text_box)

        self._animation = QVariantAnimation(self)
        self._animation.setStartValue(0.0)
        self._animation.setEndValue(1.0)
        self._animation.setDuration(self._track_ms)
        self._animation.valueChanged.connect(self._on_progress)
        self._animation.finished.connect(self._on_finished)

        self._set_playing(False)

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

    # ── Playback preview ────────────────────────────────────────────────────
    def is_playing(self) -> bool:
        return self._playing

    def play(self) -> None:
        if self._playing:
            return
        if self._progress >= 1.0:
            self._set_progress(0.0)
        self._animation.setStartValue(self._progress)
        self._animation.setEndValue(1.0)
        self._animation.setDuration(
            max(1, int(self._track_ms * (1.0 - self._progress)))
        )
        self._animation.start()
        self._set_playing(True)
        self.play_toggled.emit(True)

    def pause(self) -> None:
        if not self._playing:
            return
        self._animation.stop()
        self._set_playing(False)
        self.play_toggled.emit(False)

    def toggle(self) -> None:
        if self._playing:
            self.pause()
        else:
            self.play()

    def set_playing(self, playing: bool) -> None:
        if playing:
            self.play()
        else:
            self.pause()

    def _set_playing(self, playing: bool) -> None:
        self._playing = playing
        self._button.setIcon(
            make_icon(
                "pause" if playing else "play", theme.TEXT_ON_ACCENT, 16
            )
        )
        action = "Pause" if playing else "Play"
        self._button.setToolTip(f"{action} {self._title}")
        self._button.setAccessibleName(f"{action} {self._title}")

    def _set_progress(self, value: float) -> None:
        self._progress = value
        self._progress_bar.set_value(value)
        self._elapsed_label.setText(
            format_duration(int(self._track_ms * value))
        )

    def _on_progress(self, value) -> None:  # noqa: ANN001 (Qt signal)
        self._set_progress(float(value))

    def _on_finished(self) -> None:
        self._set_progress(0.0)
        self.set_playing(False)

    # ── Layout ──────────────────────────────────────────────────────────────
    def minimumSizeHint(self) -> QSize:  # noqa: N802 (Qt naming)
        """Keep the card at one grid column even with very long labels."""
        return QSize(
            theme.CARD_MIN_WIDTH, super().minimumSizeHint().height()
        )

    def resizeEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        super().resizeEvent(event)
        width = self.contentsRect().width()
        self._art.setFixedHeight(max(170, min(width, 280)))
