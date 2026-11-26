"""Controls made for the auth screens: mode switch, checkbox, submit button.

Each one paints its own animated state instead of leaning on QSS, because a
stylesheet can change a colour but cannot ease towards it.
"""

from __future__ import annotations

from PySide6.QtCore import (
    QEasingCurve,
    QPointF,
    QRectF,
    QSize,
    Qt,
    QPropertyAnimation,
    QVariantAnimation,
)
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QWidget,
)

from theme import theme_manager as theme
from ui.components import motion


def letter_spaced(widget: QLabel, spacing: float) -> QLabel:
    """Add tracking to a label; QSS has no reliable ``letter-spacing``."""
    font = QFont(widget.font())
    font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, spacing)
    widget.setFont(font)
    return widget


class SegmentSwitch(QFrame):
    """Two-state switch whose indicator glides to the active segment."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setProperty("role", "segmented")
        self._buttons: list[QPushButton] = []
        self._index = 0

        self._indicator = QFrame(self)
        self._indicator.setProperty("role", "segmentIndicator")
        self._indicator.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents, True
        )

        self._row = QHBoxLayout(self)
        inset = theme.SPACE_XS - 1
        self._row.setContentsMargins(inset, inset, inset, inset)
        self._row.setSpacing(theme.SPACE_XS - 2)

        self._slide = QPropertyAnimation(self._indicator, b"geometry", self)
        self._slide.setDuration(260)
        self._slide.setEasingCurve(QEasingCurve.Type.OutCubic)

    def add_segment(self, text: str, handler) -> QPushButton:
        button = QPushButton(text)
        button.setProperty("variant", "segment")
        button.setProperty("active", False)
        button.setMinimumHeight(34)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.clicked.connect(handler)
        self._buttons.append(button)
        self._row.addWidget(button, 1)
        return button

    def set_active(self, index: int, animate: bool = False) -> None:
        self._index = index
        for position, button in enumerate(self._buttons):
            button.setProperty("active", position == index)
            theme.restyle(button)

        target = self._segment_rect(index)
        self._slide.stop()
        if animate and motion.motion_enabled() and self.isVisible() and target.isValid():
            self._slide.setStartValue(self._indicator.geometry())
            self._slide.setEndValue(target)
            self._slide.start()
        else:
            self._indicator.setGeometry(target)

    def _segment_rect(self, index: int):
        if not 0 <= index < len(self._buttons):
            return self._indicator.geometry()
        return self._buttons[index].geometry()

    def resizeEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        super().resizeEvent(event)
        self._slide.stop()
        self._indicator.setGeometry(self._segment_rect(self._index))


class AnimatedCheckBox(QCheckBox):
    """Checkbox that fills with the accent and draws its tick on toggle.

    Behaves exactly like ``QCheckBox`` (``toggled``, ``isChecked``...); only
    the painting is custom.
    """

    BOX = 18
    GAP = 10

    def __init__(self, text: str = "", parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._hover = False
        self._progress = 1.0 if self.isChecked() else 0.0
        self._anim = QVariantAnimation(self)
        self._anim.setDuration(220)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.valueChanged.connect(self._set_progress)
        self.toggled.connect(self._animate)

    # ── Sizing ──────────────────────────────────────────────────────────────
    def sizeHint(self) -> QSize:  # noqa: N802 (Qt naming)
        metrics = self.fontMetrics()
        width = self.BOX + self.GAP + metrics.horizontalAdvance(self.text()) + 6
        return QSize(width, max(self.BOX + 10, metrics.height() + 8))

    def minimumSizeHint(self) -> QSize:  # noqa: N802
        return self.sizeHint()

    def hitButton(self, pos) -> bool:  # noqa: N802
        return self.rect().contains(pos)

    # ── Animation ───────────────────────────────────────────────────────────
    @property
    def progress(self) -> float:
        return self._progress

    def _set_progress(self, value) -> None:
        self._progress = float(value)
        self.update()

    def _animate(self, checked: bool) -> None:
        target = 1.0 if checked else 0.0
        self._anim.stop()
        if not motion.motion_enabled() or not self.isVisible():
            self._set_progress(target)
            return
        self._anim.setStartValue(self._progress)
        self._anim.setEndValue(target)
        self._anim.start()

    def enterEvent(self, event) -> None:  # noqa: N802
        self._hover = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802
        self._hover = False
        self.update()
        super().leaveEvent(event)

    # ── Painting ────────────────────────────────────────────────────────────
    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        t = self._progress
        box = QRectF(1.5, (self.height() - self.BOX) / 2, self.BOX, self.BOX)

        fill = QColor(theme.mix_hex(theme.BG_INPUT, theme.PRIMARY, t))
        edge_idle = theme.BORDER_STRONG if not self._hover else theme.TEXT_MUTED
        border = QColor(theme.mix_hex(edge_idle, theme.PRIMARY, t))
        painter.setPen(QPen(border, 1.2))
        painter.setBrush(fill)
        painter.drawRoundedRect(box, 5.5, 5.5)

        if t > 0.02:
            self._paint_tick(painter, box, t)

        if self.hasFocus():
            ring = QColor(theme.PRIMARY)
            ring.setAlphaF(0.55)
            painter.setPen(QPen(ring, 1.5))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(box.adjusted(-2.5, -2.5, 2.5, 2.5), 8, 8)

        painter.setFont(self.font())
        painter.setPen(QColor(theme.TEXT_PRIMARY if (self._hover or t > 0.5) else theme.TEXT_SECONDARY))
        text_rect = QRectF(
            box.right() + self.GAP, 0, self.width() - box.right() - self.GAP, self.height()
        )
        painter.drawText(
            text_rect,
            int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft),
            self.text(),
        )
        painter.end()

    @staticmethod
    def _paint_tick(painter: QPainter, box: QRectF, t: float) -> None:
        """Draw the tick as two strokes that grow one after the other."""
        w, h = box.width(), box.height()
        start = QPointF(box.left() + w * 0.27, box.top() + h * 0.52)
        mid = QPointF(box.left() + w * 0.44, box.top() + h * 0.69)
        end = QPointF(box.left() + w * 0.75, box.top() + h * 0.33)

        pen = QPen(QColor(theme.TEXT_ON_ACCENT), 2.0)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        first = min(1.0, t * 2.0)
        painter.drawLine(start, start + (mid - start) * first)
        if t > 0.5:
            second = (t - 0.5) * 2.0
            painter.drawLine(mid, mid + (end - mid) * second)


class LoadingButton(QPushButton):
    """Primary button with idle, loading, and success states.

    The button stays enabled while loading so QSS keeps its accent look; the
    caller guards against double submits.
    """

    IDLE, LOADING, SUCCESS = range(3)

    def __init__(self, text: str = "", parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self._state = self.IDLE
        self._angle = 0.0
        self._check = 0.0

        self._spin = QVariantAnimation(self)
        self._spin.setStartValue(0.0)
        self._spin.setEndValue(360.0)
        self._spin.setDuration(900)
        self._spin.setLoopCount(-1)
        self._spin.setEasingCurve(QEasingCurve.Type.Linear)
        self._spin.valueChanged.connect(self._on_spin)

        self._draw_check = QVariantAnimation(self)
        self._draw_check.setStartValue(0.0)
        self._draw_check.setEndValue(1.0)
        self._draw_check.setDuration(320)
        self._draw_check.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._draw_check.valueChanged.connect(self._on_check)

    @property
    def state(self) -> int:
        return self._state

    def set_state(self, state: int, text: str | None = None) -> None:
        self._state = state
        if text is not None:
            self.setText(text)
        self._spin.stop()
        self._draw_check.stop()
        self._angle = 0.0
        self._check = 1.0 if state == self.SUCCESS else 0.0
        if state == self.LOADING and motion.motion_enabled():
            self._spin.start()
        elif state == self.SUCCESS and motion.motion_enabled():
            self._check = 0.0
            self._draw_check.start()
        self.update()

    def _on_spin(self, value) -> None:
        self._angle = float(value)
        self.update()

    def _on_check(self, value) -> None:
        self._check = float(value)
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        super().paintEvent(event)
        if self._state == self.IDLE:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        text_width = self.fontMetrics().horizontalAdvance(self.text())
        size = 16.0
        left = (self.width() - text_width) / 2 - size - 10
        top = (self.height() - size) / 2
        rect = QRectF(left, top, size, size)
        color = QColor(theme.TEXT_ON_ACCENT)

        if self._state == self.LOADING:
            track = QColor(color)
            track.setAlphaF(0.22)
            painter.setPen(QPen(track, 2.2))
            painter.drawEllipse(rect)
            pen = QPen(color, 2.2)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            painter.drawArc(rect, int(-self._angle * 16), 100 * 16)
        else:
            pen = QPen(color, 2.2)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            start = QPointF(rect.left() + size * 0.14, rect.top() + size * 0.54)
            mid = QPointF(rect.left() + size * 0.40, rect.top() + size * 0.78)
            end = QPointF(rect.left() + size * 0.88, rect.top() + size * 0.24)
            t = self._check
            painter.drawLine(start, start + (mid - start) * min(1.0, t * 2.0))
            if t > 0.5:
                painter.drawLine(mid, mid + (end - mid) * ((t - 0.5) * 2.0))
        painter.end()
