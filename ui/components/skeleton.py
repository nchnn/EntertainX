"""Loading placeholders: a shared pulse clock and a pulsing tile."""

from __future__ import annotations

import math

from PySide6.QtCore import QObject, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QWidget

from theme import theme_manager as theme
from ui.components.artwork import rounded_path
from ui.components.motion import motion_enabled


class PulseClock(QObject):
    """One timer for every visible skeleton, running only while one is shown."""

    tick = Signal(float)

    def __init__(self) -> None:
        super().__init__()
        self._users = 0
        self._phase = 0.0
        self._timer = QTimer(self)
        self._timer.setInterval(40)
        self._timer.timeout.connect(self._advance)

    @property
    def phase(self) -> float:
        return self._phase

    def acquire(self) -> None:
        self._users += 1
        if self._users == 1 and motion_enabled():
            self._timer.start()

    def release(self) -> None:
        self._users = max(0, self._users - 1)
        if self._users == 0:
            self._timer.stop()

    def _advance(self) -> None:
        self._phase = (self._phase + 0.025) % 1.0
        self.tick.emit(self._phase)


_clock: PulseClock | None = None


def pulse_clock() -> PulseClock:
    global _clock
    if _clock is None:
        _clock = PulseClock()
    return _clock


def pulse_color(phase: float) -> QColor:
    """Card colour breathing towards the elevated surface and back."""
    wave = 0.5 + 0.5 * math.sin(phase * math.tau)
    return QColor(theme.mix_hex(theme.BG_CARD, theme.BG_ELEVATED, 0.25 + 0.6 * wave))


class SkeletonTile(QWidget):
    """A tile-sized placeholder that pulses while a shelf loads."""

    def __init__(
        self,
        width: int = theme.TILE_WIDTH,
        height: int = theme.TILE_HEIGHT,
        radius: float = theme.RADIUS_MD,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._radius = radius
        self.setFixedSize(width, height)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        pulse_clock().tick.connect(self._on_tick)

    def _on_tick(self, _phase: float) -> None:
        if self.isVisible():
            self.update()

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        pulse_clock().acquire()

    def hideEvent(self, event) -> None:  # noqa: N802
        super().hideEvent(event)
        pulse_clock().release()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.fillPath(
            rounded_path(QRectF(self.rect()), self._radius),
            pulse_color(pulse_clock().phase),
        )
        painter.end()
