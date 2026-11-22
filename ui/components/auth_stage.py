"""Brand stage for the split auth screen.

The stage is the one expressive moment in an otherwise task-first surface: a
hero statement above a fan of three painted category posters. A slow ambient
glow drifts behind it, the posters float, and the hero's last word rotates
between film, album, and game while the matching poster lifts forward. Copy
below the headline follows the form's mode (sign in or create account).

Everything is drawn from theme tokens, so the stage re-tints with the rest of
the app and ships without raster assets.
"""

from __future__ import annotations

import math
import time

from PySide6.QtCore import (
    QEasingCurve,
    QPauseAnimation,
    QParallelAnimationGroup,
    QPointF,
    QRectF,
    QSequentialAnimationGroup,
    QSize,
    Qt,
    QTimer,
    QVariantAnimation,
    QAbstractAnimation,
    Signal,
)
from PySide6.QtGui import (
    QColor,
    QFontMetricsF,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPolygonF,
    QRadialGradient,
    QTransform,
)
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from theme import theme_manager as theme
from ui.components import motion
from ui.components.auth_controls import letter_spaced
from ui.components.icons import make_icon
from ui.components.surfaces import label

POSTER_ASPECT = 1.36  # height / width of a portrait cover
POSTER_RADIUS = 12.0  # album sleeve and game box
MOVIE_RADIUS = 7.0  # posters are cut square, not rounded like an app card
POSTER_MAX_WIDTH = 228.0
HOVER_LIFT = 16.0
HOVER_SPREAD = 20.0
HOVER_SCALE = 0.028
SPOT_STRENGTH = 0.9  # how far a spotlighted poster lifts, relative to hover
IDLE_FLOAT = 5.0  # px a poster drifts up and down while idle
IDLE_TILT = 0.45  # degrees of idle sway
INTRO_RISE = 64.0  # px a poster travels while entering
LEAD_MAX_WIDTH = 430.0  # keeps the hero lead to two even lines on wide stages
AMBIENT_PERIOD = 24.0  # seconds for the background glow to loop
TICK_MS = 40  # ambient redraw cadence (25 fps keeps idle CPU low)

WORDS = ("film.", "album.", "game.")
# The rotating word and the poster it spotlights: film -> movie poster (centre),
# album -> music sleeve (left), game -> games box (right).
WORD_TO_CARD = {0: 2, 1: 0, 2: 1}
INTRO_DELAY_MS = {2: 0, 0: 150, 1: 240}

LEADS = (
    "Sign in to pick up right where you left off. Your ratings, lists, "
    "and playlists are waiting.",
    "One free account for every film, album, and game you love, kept "
    "together and entirely yours.",
)

FEATURES = (
    ("star", "Rate everything", "Score what you finish."),
    ("list", "Keep your lists", "Favorites and watchlists."),
    ("shield", "Private by design", "Stays on this device."),
)


def _tint(color: str, alpha: float) -> QColor:
    """Return ``color`` at ``alpha`` opacity, clamped to the valid range."""
    value = QColor(color)
    value.setAlphaF(max(0.0, min(1.0, alpha)))
    return value


class RotatingWord(QWidget):
    """The hero's accent word; it slides up and cross-fades to the next one.

    Painted rather than laid out so the outgoing and incoming words can overlap
    without disturbing the layout around them.
    """

    changed = Signal(int)

    TRAVEL = 22.0

    def __init__(
        self,
        words: tuple[str, ...] = WORDS,
        parent: QWidget | None = None,
        interval_ms: int = 3400,
    ) -> None:
        super().__init__(parent)
        self._words = tuple(words)
        self._index = 0
        self._previous = 0
        self._progress = 1.0
        self._font = theme.display_font(theme.FONT_SIZE_AUTH_HEADLINE, italic=True)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        metrics = QFontMetricsF(self._font)
        self._text_width = max(metrics.horizontalAdvance(word) for word in self._words)
        self.setFixedHeight(int(metrics.height()) + 6)

        self._anim = QVariantAnimation(self)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.setDuration(640)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.valueChanged.connect(self._set_progress)

        self._timer = QTimer(self)
        self._timer.setInterval(interval_ms)
        self._timer.timeout.connect(self.advance)

    # ── State ───────────────────────────────────────────────────────────────
    @property
    def index(self) -> int:
        return self._index

    @property
    def word(self) -> str:
        return self._words[self._index]

    def advance(self) -> None:
        self.set_index((self._index + 1) % len(self._words))

    def set_index(self, index: int, animate: bool = True) -> None:
        index %= len(self._words)
        if index == self._index:
            return
        self._previous = self._index
        self._index = index
        self._anim.stop()
        if animate and motion.motion_enabled() and self.isVisible():
            self._progress = 0.0
            self._anim.start()
        else:
            self._progress = 1.0
            self.update()
        self.changed.emit(index)

    def _set_progress(self, value) -> None:
        self._progress = float(value)
        self.update()

    # ── Sizing ──────────────────────────────────────────────────────────────
    def sizeHint(self) -> QSize:  # noqa: N802 (Qt naming)
        return QSize(int(self._text_width) + 12, self.height())

    def minimumSizeHint(self) -> QSize:  # noqa: N802
        return self.sizeHint()

    # ── Rotation clock ──────────────────────────────────────────────────────
    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        if motion.motion_enabled():
            self._timer.start()

    def hideEvent(self, event) -> None:  # noqa: N802
        self._timer.stop()
        super().hideEvent(event)

    # ── Painting ────────────────────────────────────────────────────────────
    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        painter.setFont(self._font)
        metrics = painter.fontMetrics()
        baseline = (self.height() + metrics.ascent() - metrics.descent()) / 2.0
        color = QColor(theme.PRIMARY)
        t = self._progress

        if t < 1.0:
            painter.setOpacity(max(0.0, 1.0 - t * 1.6))
            painter.setPen(color)
            painter.drawText(
                QPointF(0, baseline - self.TRAVEL * t), self._words[self._previous]
            )

        painter.setOpacity(min(1.0, t * 1.3))
        painter.setPen(color)
        painter.drawText(
            QPointF(0, baseline + self.TRAVEL * (1.0 - t)), self._words[self._index]
        )
        painter.end()


class _Feature(QWidget):
    """Icon, one-line title, and a short caption."""

    def __init__(
        self, icon_name: str, title: str, caption: str, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        column = QVBoxLayout(self)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(3)

        head = QHBoxLayout()
        head.setContentsMargins(0, 0, 0, 0)
        head.setSpacing(theme.SPACE_SM)
        glyph = QLabel()
        glyph.setPixmap(make_icon(icon_name, theme.PRIMARY, 15).pixmap(15, 15))
        glyph.setFixedSize(15, 15)
        head.addWidget(glyph, 0, Qt.AlignmentFlag.AlignVCenter)
        head.addWidget(label(title, "featureTitle", wrap=False))
        head.addStretch(1)
        column.addLayout(head)
        column.addWidget(label(caption, "featureCaption"))


class MediaFan(QWidget):
    """Three overlapping covers: music and games flanking a movie poster.

    The side covers slide outward and lift on hover, while the centre poster
    only lifts - the fan opens like a hand instead of every card jumping. At
    rest the covers float gently, enter with a staggered rise, and the stage can
    spotlight one at a time to follow the hero's rotating word.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(200)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setMouseTracking(True)
        self._hover = -1
        self._spotlight = -1
        self._phase = 0.0
        self._progress = [0.0, 0.0, 0.0]
        self._spot = [0.0, 0.0, 0.0]
        # Covers wait offscreen until the stage plays its entrance.
        start = 0.0 if motion.motion_enabled() else 1.0
        self._intro = [start, start, start]
        self._intro_group: QParallelAnimationGroup | None = None

        self._animations: list[QVariantAnimation] = []
        self._spot_animations: list[QVariantAnimation] = []
        for index in range(3):
            animation = QVariantAnimation(self)
            animation.setDuration(180)
            animation.setEasingCurve(QEasingCurve.Type.OutCubic)
            animation.valueChanged.connect(
                lambda value, i=index: self._set_progress(i, value)
            )
            self._animations.append(animation)

            spot = QVariantAnimation(self)
            spot.setDuration(520)
            spot.setEasingCurve(QEasingCurve.Type.OutCubic)
            spot.valueChanged.connect(lambda value, i=index: self._set_spot(i, value))
            self._spot_animations.append(spot)

    # ── Geometry ────────────────────────────────────────────────────────────
    def _layout(self) -> tuple[tuple, float, float]:
        width, height = self.width(), self.height()
        card_w = min(width * 0.46, (height * 0.78) / POSTER_ASPECT, POSTER_MAX_WIDTH)
        card_h = card_w * POSTER_ASPECT
        offset = card_w * 0.42
        center = QPointF(width / 2, height / 2)

        cards = (
            (QPointF(center.x() - offset, center.y() + 12), -8.0, -1, self._paint_music),
            (QPointF(center.x() + offset, center.y() + 12), 8.0, 1, self._paint_games),
            (QPointF(center.x(), center.y() - 8), 0.0, 0, self._paint_movie),
        )
        return cards, card_w, card_h

    def _card_at(self, position: QPointF) -> int:
        """Topmost card under ``position``, using resting geometry.

        Hit testing ignores the hover offset on purpose: if the test followed
        the animation, a card sliding away from the cursor would drop the
        hover and snap back on the next frame.
        """
        cards, card_w, card_h = self._layout()
        for index in range(len(cards) - 1, -1, -1):
            origin, angle, _side, _artwork = cards[index]
            transform = QTransform()
            transform.translate(origin.x(), origin.y())
            transform.rotate(angle)
            transform.translate(-card_w / 2, -card_h / 2)
            inverted, ok = transform.inverted()
            if not ok:
                continue
            local = inverted.map(position)
            if 0 <= local.x() <= card_w and 0 <= local.y() <= card_h:
                return index
        return -1

    # ── Hover, spotlight, and entrance state ────────────────────────────────
    def _set_progress(self, index: int, value: float) -> None:
        self._progress[index] = float(value)
        self.update()

    def _set_spot(self, index: int, value: float) -> None:
        self._spot[index] = float(value)
        self.update()

    def _set_intro(self, index: int, value: float) -> None:
        self._intro[index] = float(value)
        self.update()

    def set_phase(self, phase: float) -> None:
        """Position in the idle-float loop, 0..1."""
        self._phase = float(phase)
        self.update()

    def _set_hover(self, index: int) -> None:
        if index == self._hover:
            return
        self._hover = index
        for i, animation in enumerate(self._animations):
            animation.stop()
            animation.setStartValue(self._progress[i])
            animation.setEndValue(1.0 if i == index else 0.0)
            animation.start()

    def set_spotlight(self, index: int) -> None:
        """Lift one cover forward (``-1`` for none), easing the others back."""
        if index == self._spotlight:
            return
        self._spotlight = index
        for i, animation in enumerate(self._spot_animations):
            animation.stop()
            animation.setStartValue(self._spot[i])
            animation.setEndValue(1.0 if i == index else 0.0)
            animation.start()

    def play_intro(self) -> None:
        """Raise the covers into place one after another."""
        if not motion.motion_enabled():
            self._intro = [1.0, 1.0, 1.0]
            self.update()
            return
        if self._intro_group is not None:
            try:
                self._intro_group.stop()
            except RuntimeError:
                pass

        group = QParallelAnimationGroup(self)
        for index in range(3):
            self._intro[index] = 0.0
            track = QSequentialAnimationGroup()
            track.addAnimation(QPauseAnimation(INTRO_DELAY_MS[index]))
            rise = QVariantAnimation()
            rise.setStartValue(0.0)
            rise.setEndValue(1.0)
            rise.setDuration(900)
            rise.setEasingCurve(QEasingCurve.Type.OutBack)
            rise.valueChanged.connect(lambda value, i=index: self._set_intro(i, value))
            track.addAnimation(rise)
            group.addAnimation(track)
        self._intro_group = group
        group.start(QAbstractAnimation.DeletionPolicy.DeleteWhenStopped)
        self.update()

    def mouseMoveEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        self._set_hover(self._card_at(event.position()))
        super().mouseMoveEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        self._set_hover(-1)
        super().leaveEvent(event)

    # ── Painting ────────────────────────────────────────────────────────────
    def paintEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        width, height = self.width(), self.height()
        if width < 80 or height < 80:
            painter.end()
            return

        cards, card_w, card_h = self._layout()
        for index, (origin, angle, side, artwork) in enumerate(cards):
            intro = self._intro[index]
            if intro <= 0.0:
                continue
            lift = max(self._progress[index], self._spot[index] * SPOT_STRENGTH)
            scale = (1.0 + HOVER_SCALE * lift) * (0.93 + 0.07 * min(1.0, intro))
            drift = math.sin(math.tau * (self._phase * 3 + index / 3)) * IDLE_FLOAT
            sway = math.sin(math.tau * (self._phase * 2 + index / 3)) * IDLE_TILT

            painter.save()
            painter.setOpacity(min(1.0, intro * 1.4))
            painter.translate(
                origin.x() + side * HOVER_SPREAD * lift,
                origin.y() - HOVER_LIFT * lift + drift + (1.0 - intro) * INTRO_RISE,
            )
            painter.rotate(angle + sway)
            painter.scale(scale, scale)
            painter.translate(-card_w / 2, -card_h / 2)
            radius = MOVIE_RADIUS if index == 2 else POSTER_RADIUS
            self._paint_shadow(painter, card_w, card_h, radius)
            artwork(painter, card_w, card_h)
            painter.restore()
        painter.end()

    @staticmethod
    def _paint_shadow(
        painter: QPainter, width: float, height: float, radius: float
    ) -> None:
        painter.setPen(Qt.PenStyle.NoPen)
        for step in range(12, 0, -1):
            painter.setBrush(_tint(theme.SHADOW, 0.05))
            grow = step * 1.2
            painter.drawRoundedRect(
                QRectF(-grow / 2, 6 - grow / 2, width + grow, height + grow),
                radius + grow / 2,
                radius + grow / 2,
            )

    @staticmethod
    def _card(
        painter: QPainter,
        width: float,
        height: float,
        top: str,
        bottom: str,
        radius: float = POSTER_RADIUS,
    ) -> QPainterPath:
        path = QPainterPath()
        path.addRoundedRect(QRectF(0, 0, width, height), radius, radius)
        gradient = QLinearGradient(0, 0, width, height)
        gradient.setColorAt(0.0, QColor(top))
        gradient.setColorAt(1.0, QColor(bottom))
        painter.setPen(QPen(_tint(theme.BORDER_STRONG, 0.85), 1))
        painter.setBrush(gradient)
        painter.drawPath(path)
        return path

    def _paint_movie(self, painter: QPainter, width: float, height: float) -> None:
        """A film frame: sprocket strips, a play mark, and a poster title block."""
        path = self._card(
            painter,
            width,
            height,
            theme.AUTH_POSTER_DARK,
            theme.AUTH_POSTER_DARK_END,
            MOVIE_RADIUS,
        )
        painter.setClipPath(path)

        glow = QRadialGradient(QPointF(width * 0.5, height * 0.14), width * 0.95)
        glow.setColorAt(0.0, _tint(theme.PRIMARY, 0.24))
        glow.setColorAt(0.55, _tint(theme.PRIMARY, 0.06))
        glow.setColorAt(1.0, _tint(theme.PRIMARY, 0.0))
        painter.fillRect(QRectF(0, 0, width, height), glow)

        strip = width * 0.13
        hole_w = strip * 0.42
        hole_h = hole_w * 0.82
        step = hole_h * 1.9
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(_tint(theme.TEXT_ON_ACCENT, 0.55))
        painter.drawRect(QRectF(0, 0, strip, height))
        painter.drawRect(QRectF(width - strip, 0, strip, height))

        painter.setBrush(_tint(theme.AUTH_POSTER_DARK, 0.92))
        y = step * 0.6
        while y + hole_h < height:
            for x in (0.0, width - strip):
                painter.drawRoundedRect(
                    QRectF(x + (strip - hole_w) / 2, y, hole_w, hole_h),
                    hole_w * 0.22,
                    hole_w * 0.22,
                )
            y += step

        center = QPointF(width / 2, height * 0.47)
        ring = width * 0.17
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(_tint(theme.PRIMARY, 0.8), 1.6))
        painter.drawEllipse(center, ring, ring)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(_tint(theme.PRIMARY, 0.95))
        size = ring * 1.05
        painter.drawPolygon(
            QPolygonF(
                [
                    QPointF(center.x() - size * 0.32, center.y() - size * 0.48),
                    QPointF(center.x() + size * 0.58, center.y()),
                    QPointF(center.x() - size * 0.32, center.y() + size * 0.48),
                ]
            )
        )

        painter.setBrush(_tint(theme.PRIMARY, 0.9))
        painter.drawRoundedRect(
            QRectF(width * 0.22, height * 0.75, width * 0.56, height * 0.026), 2, 2
        )
        painter.setBrush(_tint(theme.TEXT_SECONDARY, 0.3))
        painter.drawRoundedRect(
            QRectF(width * 0.32, height * 0.803, width * 0.36, height * 0.014), 2, 2
        )

    def _paint_music(self, painter: QPainter, width: float, height: float) -> None:
        path = self._card(painter, width, height, theme.SECONDARY, theme.ACCENT_PRESSED)
        painter.setClipPath(path)

        center = QPointF(width / 2, height / 2)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        for index, radius in enumerate(
            (width * 0.4, width * 0.31, width * 0.22, width * 0.13)
        ):
            painter.setPen(
                QPen(_tint(theme.TEXT_ON_ACCENT, 0.14 + index * 0.05), 1.2)
            )
            painter.drawEllipse(center, radius, radius)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(theme.TEXT_ON_ACCENT))
        painter.drawEllipse(center, width * 0.045, width * 0.045)

    def _paint_games(self, painter: QPainter, width: float, height: float) -> None:
        path = self._card(
            painter, width, height, theme.AUTH_POSTER_WARM, theme.AUTH_POSTER_WARM_END
        )
        painter.setClipPath(path)

        unit = width * 0.2
        gap = unit * 1.16
        left = (width - (gap * 2 + unit)) / 2
        top = (height - (gap + unit)) / 2
        cells = ((0, 0, 0.88), (1, 0, 0.62), (2, 0, 0.4), (1, 1, 0.72))

        painter.setPen(Qt.PenStyle.NoPen)
        for column, row, alpha in cells:
            painter.setBrush(_tint(theme.PRIMARY, alpha))
            painter.drawRoundedRect(
                QRectF(left + column * gap, top + row * gap, unit, unit),
                unit * 0.24,
                unit * 0.24,
            )


class AuthStage(QWidget):
    """Hero + poster fan shown beside the auth form on wide windows."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("AuthStage")
        self.setMinimumWidth(420)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setAccessibleName("EntertainX")

        self._mode = 0
        self._phase = 0.0
        self._entered = False
        self._started = time.monotonic()
        self._clock = QTimer(self)
        self._clock.setInterval(TICK_MS)
        self._clock.timeout.connect(self._tick)

        column = QVBoxLayout(self)
        column.setContentsMargins(
            theme.SPACE_XXL + 16,
            theme.SPACE_XXL + 12,
            theme.SPACE_XXL + 12,
            theme.SPACE_XL + 8,
        )
        column.setSpacing(0)

        column.addWidget(self._hero())

        self.fan = MediaFan()
        column.addWidget(self.fan, 1)
        column.addSpacing(theme.SPACE_SM)
        column.addWidget(self._features())

        self.word.changed.connect(self._on_word_changed)
        self.fan.set_spotlight(WORD_TO_CARD[self.word.index])

    # ── Construction ────────────────────────────────────────────────────────
    def _hero(self) -> QWidget:
        """Kicker, two-line headline with a rotating accent word, and the lead."""
        block = QWidget()
        stack = QVBoxLayout(block)
        # The bottom margin is travel room: the lead rises from below its rest
        # position and would otherwise be clipped by this block's edge.
        stack.setContentsMargins(0, 0, 0, 20)
        stack.setSpacing(0)

        kicker = QWidget()
        row = QHBoxLayout(kicker)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(theme.SPACE_MD)
        rule = QFrame()
        rule.setProperty("role", "accentRule")
        rule.setFixedSize(26, 2)
        row.addWidget(rule, 0, Qt.AlignmentFlag.AlignVCenter)
        row.addWidget(
            letter_spaced(label("MOVIES  \u00b7  MUSIC  \u00b7  GAMES", "authKicker", wrap=False), 2.2)
        )
        row.addStretch(1)
        self.kicker = kicker
        stack.addWidget(kicker)
        stack.addSpacing(theme.SPACE_LG + 2)

        self.headline = label("Your next favorite", "authHeadline", wrap=False)
        self.headline.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed
        )
        stack.addWidget(self.headline)

        self.word = RotatingWord()
        stack.addWidget(self.word, 0, Qt.AlignmentFlag.AlignLeft)
        stack.addSpacing(theme.SPACE_MD)

        self.lead = label(LEADS[0], "authLead")
        self.lead.setMaximumWidth(int(LEAD_MAX_WIDTH))
        self.lead.setMinimumHeight(self.lead.fontMetrics().lineSpacing() * 2 + 4)
        stack.addWidget(self.lead)
        return block

    def _features(self) -> QFrame:
        """Three one-line promises under a hairline, anchored to the bottom."""
        frame = QFrame()
        frame.setProperty("role", "authFooter")
        row = QHBoxLayout(frame)
        row.setContentsMargins(0, theme.SPACE_LG, 0, 0)
        row.setSpacing(theme.SPACE_XL)
        self.feature_items = []
        for icon_name, title, caption in FEATURES:
            item = _Feature(icon_name, title, caption)
            self.feature_items.append(item)
            row.addWidget(item)
        row.addStretch(1)
        self.features = frame
        return frame

    # ── Mode (sign in / create account) ─────────────────────────────────────
    @property
    def mode(self) -> int:
        return self._mode

    def current_lead(self) -> str:
        return self.lead.text()

    def set_mode(self, mode: int) -> None:
        """Swap the lead copy for ``mode`` (0 = sign in, 1 = create account)."""
        mode = 1 if mode else 0
        if mode == self._mode:
            return
        self._mode = mode
        motion.swap(
            self.lead,
            lambda: self.lead.setText(LEADS[mode]),
            out_ms=110,
            in_ms=280,
            rise_in=8.0,
        )

    def _on_word_changed(self, index: int) -> None:
        self.fan.set_spotlight(WORD_TO_CARD.get(index, -1))

    # ── Entrance and ambient clock ──────────────────────────────────────────
    def play_intro(self) -> None:
        """Bring the hero in line by line, then raise the posters."""
        self.fan.play_intro()
        if not motion.motion_enabled():
            return
        targets = [self.kicker, self.headline, self.word, self.lead]
        motion.cascade(targets, start=60, step=90, duration=620, rise=18)
        motion.cascade([self.features], start=520, duration=640, rise=14)

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        if not self._entered:
            self._entered = True
            self.play_intro()
        if motion.motion_enabled():
            self._clock.start()

    def hideEvent(self, event) -> None:  # noqa: N802
        self._clock.stop()
        super().hideEvent(event)

    def _tick(self) -> None:
        elapsed = time.monotonic() - self._started
        self._phase = (elapsed % AMBIENT_PERIOD) / AMBIENT_PERIOD
        self.fan.set_phase(self._phase)
        self.update()

    # ── Painting ────────────────────────────────────────────────────────────
    def paintEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        bounds = self.rect()
        width, height = float(bounds.width()), float(bounds.height())

        ground = QLinearGradient(bounds.topLeft(), bounds.bottomLeft())
        ground.setColorAt(0.0, QColor(theme.AUTH_STAGE_TOP))
        ground.setColorAt(1.0, QColor(theme.AUTH_STAGE_BOTTOM))
        painter.fillRect(bounds, ground)

        # Three soft glows orbit slowly. Whole-number multiples of the phase keep
        # the loop seamless when it wraps.
        glows = (
            (0.88, 0.04, 1.05, 0.17, 0.00, theme.PRIMARY),
            (0.06, 0.70, 0.85, 0.09, 0.33, theme.PRIMARY),
            (0.70, 1.02, 0.95, 0.10, 0.66, theme.SECONDARY),
        )
        for cx, cy, radius, alpha, offset, color in glows:
            angle = math.tau * (self._phase + offset)
            center = QPointF(
                (cx + 0.05 * math.sin(angle)) * width,
                (cy + 0.04 * math.cos(angle)) * height,
            )
            glow = QRadialGradient(center, width * radius)
            glow.setColorAt(0.0, _tint(color, alpha))
            glow.setColorAt(0.55, _tint(color, alpha * 0.3))
            glow.setColorAt(1.0, _tint(color, 0.0))
            painter.fillRect(bounds, glow)
        painter.end()
