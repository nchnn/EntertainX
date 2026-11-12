"""Mini music-player cards: painted album art, play disc, and progress."""

from __future__ import annotations

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QSizePolicy, QWidget

from theme import theme_manager as theme

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
