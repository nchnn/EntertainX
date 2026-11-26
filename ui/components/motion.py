"""Motion primitives shared by the auth screens.

A widget inside a layout cannot be moved by animating its ``pos``: the layout
puts it straight back. Every motion here is instead drawn by a
``QGraphicsEffect`` that fades and offsets the widget's rendered pixmap, which
leaves layout geometry untouched. The effect is removed the moment a motion
ends, so resting text is painted by Qt directly and stays crisp.

Set ``ENTERTAINX_REDUCE_MOTION=1`` to skip every animation. Each helper then
applies its end state immediately, so callers never need a second code path.
"""

from __future__ import annotations

import math
import os
from collections.abc import Callable, Iterable

from PySide6.QtCore import (
    QAbstractAnimation,
    QEasingCurve,
    QPauseAnimation,
    QPoint,
    QPointF,
    QSequentialAnimationGroup,
    Qt,
    QVariantAnimation,
)
from PySide6.QtWidgets import QGraphicsEffect, QWidget

REDUCE_MOTION_ENV = "ENTERTAINX_REDUCE_MOTION"
_OFF_VALUES = {"1", "true", "yes", "on"}

Callback = Callable[[], None]


def motion_enabled() -> bool:
    """False when the user (or a test run) asked for no animation."""
    return os.environ.get(REDUCE_MOTION_ENV, "").strip().lower() not in _OFF_VALUES


class MotionEffect(QGraphicsEffect):
    """Draws its source faded and offset; ``progress`` 1.0 is the resting state.

    ``dx``/``dy`` are how far the widget travels from rest at ``progress`` 0.
    ``set_shift`` adds an absolute offset on top, used by :func:`shake`.
    """

    PAD = 40

    def __init__(self, dx: float = 0.0, dy: float = 0.0, parent=None) -> None:
        super().__init__(parent)
        self._dx = float(dx)
        self._dy = float(dy)
        self._progress = 1.0
        self._shift = QPointF()

    @property
    def progress(self) -> float:
        return self._progress

    def set_progress(self, value: float) -> None:
        value = max(0.0, min(1.0, float(value)))
        if value != self._progress:
            self._progress = value
            self.update()

    def set_shift(self, x: float, y: float = 0.0) -> None:
        self._shift = QPointF(x, y)
        self.update()

    def boundingRectFor(self, rect):  # noqa: N802 (Qt naming)
        # Room for the offset so a moving widget is not clipped to its resting box.
        return rect.adjusted(-self.PAD, -self.PAD, self.PAD, self.PAD)

    def draw(self, painter) -> None:
        if self._progress <= 0.0:
            return
        offset = QPoint()
        pixmap = self.sourcePixmap(
            Qt.CoordinateSystem.LogicalCoordinates,
            offset,
            QGraphicsEffect.PixmapPadMode.NoPad,
        )
        if pixmap.isNull():
            return
        travel = 1.0 - self._progress
        target = QPointF(offset) + QPointF(
            self._dx * travel + self._shift.x(),
            self._dy * travel + self._shift.y(),
        )
        painter.save()
        painter.setOpacity(painter.opacity() * self._progress)
        painter.drawPixmap(target, pixmap)
        painter.restore()


class ScaleFadeEffect(QGraphicsEffect):
    """Draws the widget scaled about ``anchor`` and faded; ``progress`` 1 is rest."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._progress = 1.0
        self._anchor = QPointF(0.5, 0.5)

    def set_anchor(self, fx: float, fy: float) -> None:
        self._anchor = QPointF(fx, fy)

    def set_progress(self, value: float) -> None:
        value = max(0.0, min(1.0, float(value)))
        if value != self._progress:
            self._progress = value
            self.update()

    def draw(self, painter) -> None:
        if self._progress <= 0.0:
            return
        offset = QPoint()
        pixmap = self.sourcePixmap(
            Qt.CoordinateSystem.LogicalCoordinates,
            offset,
            QGraphicsEffect.PixmapPadMode.NoPad,
        )
        if pixmap.isNull():
            return
        ratio = pixmap.devicePixelRatio() or 1.0
        width, height = pixmap.width() / ratio, pixmap.height() / ratio
        scale = 0.84 + 0.16 * self._progress
        center = QPointF(offset) + QPointF(
            width * self._anchor.x(), height * self._anchor.y()
        )
        painter.save()
        painter.setOpacity(painter.opacity() * self._progress)
        painter.translate(center)
        painter.scale(scale, scale)
        painter.translate(-center)
        painter.drawPixmap(QPointF(offset), pixmap)
        painter.restore()


# ── Internals ───────────────────────────────────────────────────────────────
def _set_progress(effect: MotionEffect, value) -> None:
    try:
        effect.set_progress(float(value))
    except RuntimeError:  # the widget (and its effect) was deleted mid-motion
        pass


def _attach(widget: QWidget, dx: float, dy: float) -> MotionEffect:
    """Replace any running motion on ``widget`` with a fresh effect."""
    clear(widget)
    return _install(widget, MotionEffect(dx, dy, widget))


def _install(widget: QWidget, effect: MotionEffect) -> MotionEffect:
    widget.setGraphicsEffect(effect)
    # PySide does not keep the wrapper alive once the animation lambdas are
    # gone, and a collected wrapper deletes the effect mid-motion.
    widget._motion_effect = effect
    return effect


def _run(
    widget: QWidget,
    effect: MotionEffect,
    start: float,
    end: float,
    duration: int,
    delay: int,
    easing: QEasingCurve.Type,
    finished: Callback,
) -> None:
    animation = QVariantAnimation()
    animation.setStartValue(float(start))
    animation.setEndValue(float(end))
    animation.setDuration(max(1, int(duration)))
    animation.setEasingCurve(easing)
    animation.valueChanged.connect(lambda value: _set_progress(effect, value))

    group = QSequentialAnimationGroup(widget)
    if delay > 0:
        group.addAnimation(QPauseAnimation(int(delay)))
    group.addAnimation(animation)

    # A stopped group can still report ``finished`` from the event loop, after a
    # newer motion has taken over. The token lets only the current motion act.
    token = object()
    widget._motion_token = token

    def on_finished() -> None:
        if getattr(widget, "_motion_token", None) is token:
            finished()

    group.finished.connect(on_finished)
    widget._motion_group = group
    group.start(QAbstractAnimation.DeletionPolicy.DeleteWhenStopped)


# ── Public helpers ──────────────────────────────────────────────────────────
def clear(widget: QWidget) -> None:
    """Stop any motion on ``widget`` and drop its effect."""
    widget._motion_token = None
    group = getattr(widget, "_motion_group", None)
    if group is not None:
        try:
            group.stop()
        except RuntimeError:
            pass
        widget._motion_group = None
    if isinstance(widget.graphicsEffect(), MotionEffect):
        widget.setGraphicsEffect(None)
    widget._motion_effect = None


def reveal(
    widget: QWidget,
    *,
    delay: int = 0,
    duration: int = 440,
    rise: float = 14.0,
    dx: float = 0.0,
    easing: QEasingCurve.Type = QEasingCurve.Type.OutCubic,
    on_finished: Callback | None = None,
) -> None:
    """Fade ``widget`` in while it drifts up ``rise`` px (and across by ``dx``)."""
    if not motion_enabled():
        clear(widget)
        if on_finished is not None:
            on_finished()
        return

    effect = _attach(widget, dx, rise)
    effect.set_progress(0.0)

    def done() -> None:
        clear(widget)
        if on_finished is not None:
            on_finished()

    _run(widget, effect, 0.0, 1.0, duration, delay, easing, done)


def conceal(
    widget: QWidget,
    *,
    duration: int = 140,
    drop: float = -8.0,
    dx: float = 0.0,
    on_finished: Callback | None = None,
) -> None:
    """Fade ``widget`` out while it drifts away. The effect stays at zero.

    The caller decides what replaces it; :func:`reveal` or :func:`clear` ends
    the hold.
    """
    if not motion_enabled():
        if on_finished is not None:
            on_finished()
        return

    effect = _attach(widget, dx, drop)

    def done() -> None:
        if on_finished is not None:
            on_finished()

    _run(widget, effect, 1.0, 0.0, duration, 0, QEasingCurve.Type.InCubic, done)


def swap(
    widget: QWidget,
    apply: Callback,
    *,
    out_ms: int = 130,
    in_ms: int = 300,
    dx_out: float = 0.0,
    dx_in: float = 0.0,
    rise_in: float = 10.0,
) -> None:
    """Fade ``widget`` out, run ``apply`` while it is invisible, fade it back in.

    Used for page switches and copy changes: the change itself never shows as a
    jump. With motion off, or while hidden, ``apply`` simply runs.
    """
    if not motion_enabled() or not widget.isVisible():
        clear(widget)
        apply()
        return

    def after_out() -> None:
        apply()
        reveal(widget, duration=in_ms, rise=rise_in, dx=dx_in)

    conceal(widget, duration=out_ms, drop=-6.0, dx=dx_out, on_finished=after_out)


def cascade(
    widgets: Iterable[QWidget],
    *,
    start: int = 0,
    step: int = 60,
    duration: int = 480,
    rise: float = 16.0,
) -> None:
    """Reveal ``widgets`` one after another, ``step`` ms apart."""
    for index, widget in enumerate(widgets):
        reveal(widget, delay=start + index * step, duration=duration, rise=rise)


def shake(widget: QWidget, amplitude: float = 9.0, duration: int = 420) -> None:
    """A short decaying horizontal shake, for a rejected submit."""
    if not motion_enabled() or not widget.isVisible():
        return

    clear(widget)
    effect = _install(widget, MotionEffect(parent=widget))

    animation = QVariantAnimation(widget)
    animation.setStartValue(0.0)
    animation.setEndValue(1.0)
    animation.setDuration(duration)
    animation.setEasingCurve(QEasingCurve.Type.Linear)

    def step(value) -> None:
        offset = math.sin(float(value) * math.pi * 7) * amplitude * (1 - float(value)) ** 1.5
        try:
            effect.set_shift(offset)
        except RuntimeError:
            pass

    animation.valueChanged.connect(step)
    token = object()
    widget._motion_token = token

    def on_finished() -> None:
        if getattr(widget, "_motion_token", None) is token:
            clear(widget)

    animation.finished.connect(on_finished)
    widget._motion_group = animation
    animation.start(QAbstractAnimation.DeletionPolicy.DeleteWhenStopped)
