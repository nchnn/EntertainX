"""Loading placeholders: a shared pulse clock and a pulsing tile."""

from __future__ import annotations

import math

from PySide6.QtCore import QObject, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontMetricsF,
    QPainter,
    QPainterPath,
    QPen,
)
from PySide6.QtWidgets import QWidget

from theme import theme_manager as theme
from ui.components.artwork import rounded_path
from ui.components.motion import motion_enabled

RANK_FONT_FAMILIES = (
    "Impact",
    "Arial Black",
    "Segoe UI Black",
    "Haettenschweiler",
    "sans-serif",
)


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
    """A tile-sized placeholder with a circular spinner and optional rank numeral."""

    def __init__(
        self,
        width: int = theme.TILE_WIDTH,
        height: int = theme.TILE_HEIGHT,
        radius: float = theme.RADIUS_MD,
        rank: int | None = None,
        overlap: int = 0,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._radius = radius
        self.rank = rank
        self.overlap = overlap
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
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

        if self.rank is not None:
            num_text = str(self.rank)
            font = QFont()
            font.setFamilies(list(RANK_FONT_FAMILIES))
            font.setStyleHint(QFont.StyleHint.SansSerif)
            font.setPixelSize(220 if self.rank < 10 else 200)
            font.setWeight(QFont.Weight.Black)
            metrics = QFontMetricsF(font)
            num_w = metrics.horizontalAdvance(num_text)
            num_x = max(6.0, float(self.overlap - num_w + 14))
            num_y = float(self.height() - 12)

            path = QPainterPath()
            path.addText(num_x, num_y, font, num_text)

            painter.setPen(
                QPen(
                    QColor(0, 0, 0, 180),
                    6,
                    Qt.PenStyle.SolidLine,
                    Qt.PenCapStyle.RoundCap,
                    Qt.PenJoinStyle.RoundJoin,
                )
            )
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(path)

            painter.setPen(
                QPen(
                    QColor("#6A717E"),
                    3,
                    Qt.PenStyle.SolidLine,
                    Qt.PenCapStyle.RoundCap,
                    Qt.PenJoinStyle.RoundJoin,
                )
            )
            painter.drawPath(path)

            card_rect = QRectF(float(self.overlap), 0.0, float(self.width() - self.overlap), float(self.height()))
        else:
            card_rect = QRectF(0.0, 0.0, float(self.width()), float(self.height()))

        card_path = rounded_path(card_rect, self._radius)
        painter.fillPath(card_path, QColor("#141519"))
        painter.setPen(QPen(QColor(255, 255, 255, 14), 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(card_path)

        cx = card_rect.left() + card_rect.width() / 2.0
        cy = card_rect.top() + card_rect.height() / 2.0
        r = 17.0
        spinner_rect = QRectF(cx - r, cy - r, r * 2.0, r * 2.0)

        painter.setPen(QPen(QColor(255, 255, 255, 16), 2.5))
        painter.drawEllipse(spinner_rect)

        phase = pulse_clock().phase
        start_angle = int((-phase * 360.0) * 16.0)
        span_angle = int(270.0 * 16.0)
        painter.setPen(
            QPen(
                QColor(theme.PRIMARY),
                2.8,
                Qt.PenStyle.SolidLine,
                Qt.PenCapStyle.RoundCap,
            )
        )
        painter.drawArc(spinner_rect, start_angle, span_angle)

        painter.end()
