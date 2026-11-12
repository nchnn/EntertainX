"""Brand stage for the split auth screen.

The stage is the one expressive moment in an otherwise task-first surface: a
short statement of what an account unlocks above a fan of three painted
category posters. Everything is drawn from theme tokens, so the stage re-tints
with the rest of the app and ships without raster assets.
"""

from __future__ import annotations

from PySide6.QtCore import (
    QEasingCurve,
    QPointF,
    QRectF,
    Qt,
    QVariantAnimation,
)
from PySide6.QtGui import (
    QColor,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPolygonF,
    QRadialGradient,
    QTransform,
)
from PySide6.QtWidgets import QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget

from theme import theme_manager as theme
from ui.components.icons import make_icon
from ui.components.surfaces import label

POSTER_ASPECT = 1.36  # height / width of a portrait cover
POSTER_RADIUS = 12.0  # album sleeve and game box
MOVIE_RADIUS = 7.0  # posters are cut square, not rounded like an app card
POSTER_MAX_WIDTH = 196.0
HOVER_LIFT = 16.0
HOVER_SPREAD = 20.0
HOVER_SCALE = 0.028
LEAD_MAX_WIDTH = 430.0  # keeps the hero lead to two even lines on wide stages


def _tint(color: str, alpha: float) -> QColor:
    """Return ``color`` at ``alpha`` opacity, clamped to the valid range."""
    value = QColor(color)
    value.setAlphaF(max(0.0, min(1.0, alpha)))
    return value


class _CategoryCaption(QWidget):
    """Icon + name for one part of the library, sitting under the posters."""

    def __init__(
        self, icon_name: str, text: str, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(theme.SPACE_SM)

        glyph = QLabel()
        glyph.setPixmap(make_icon(icon_name, theme.PRIMARY, 14).pixmap(14, 14))
        glyph.setFixedSize(14, 14)
        row.addWidget(glyph, 0, Qt.AlignmentFlag.AlignVCenter)
        row.addWidget(label(text, "caption", wrap=False))


class MediaFan(QWidget):
    """Three overlapping covers: music and games flanking a movie poster.

    The side covers slide outward and lift on hover, while the centre poster
    only lifts - the fan opens like a hand instead of every card jumping.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(220)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setMouseTracking(True)
        self._hover = -1
        self._progress = [0.0, 0.0, 0.0]
        self._animations: list[QVariantAnimation] = []
        for index in range(3):
            animation = QVariantAnimation(self)
            animation.setDuration(180)
            animation.setEasingCurve(QEasingCurve.Type.OutCubic)
            animation.valueChanged.connect(
                lambda value, i=index: self._set_progress(i, value)
            )
            self._animations.append(animation)

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

    # ── Hover state ─────────────────────────────────────────────────────────
    def _set_progress(self, index: int, value: float) -> None:
        self._progress[index] = float(value)
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
            progress = self._progress[index]
            scale = 1.0 + HOVER_SCALE * progress
            painter.save()
            painter.translate(
                origin.x() + side * HOVER_SPREAD * progress,
                origin.y() - HOVER_LIFT * progress,
            )
            painter.rotate(angle)
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
    """Statement + poster fan shown beside the auth form on wide windows."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("AuthStage")
        self.setMinimumWidth(420)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setAccessibleName("EntertainX")

        column = QVBoxLayout(self)
        column.setContentsMargins(
            theme.SPACE_XXL + 16, theme.SPACE_XXL + 20, theme.SPACE_XXL + 12, theme.SPACE_XXL + 12
        )
        column.setSpacing(theme.SPACE_MD)

        column.addWidget(self._hero())
        column.addSpacing(theme.SPACE_LG)

        self.fan = MediaFan()
        column.addWidget(self.fan, 1)

        captions = QHBoxLayout()
        captions.setContentsMargins(0, 0, 0, 0)
        captions.setSpacing(theme.SPACE_XL)
        for icon_name, text in (
            ("film", "Movies & TV"),
            ("music", "Music"),
            ("gamepad", "Games"),
        ):
            captions.addWidget(_CategoryCaption(icon_name, text))
        captions.addStretch(1)
        column.addLayout(captions)

    def _hero(self) -> QWidget:
        """Eyebrow, two-line headline, and the account promise.

        The second headline line carries the accent colour so the promise reads
        as the hook while the three verbs stay neutral above it.
        """
        block = QWidget()
        stack = QVBoxLayout(block)
        stack.setContentsMargins(0, 0, 0, 0)
        stack.setSpacing(0)

        stack.addWidget(label("MOVIES \u00b7 MUSIC \u00b7 GAMES", "authKicker", wrap=False))
        stack.addSpacing(theme.SPACE_MD)

        stack.addWidget(label("Watch. Listen. Play.", "authDisplay"))
        stack.addWidget(label("All in one place.", "authDisplayAccent"))
        stack.addSpacing(theme.SPACE_MD + 2)

        lead = label(
            "Rate what you finish, replay what you love, and keep every "
            "game, album, and film in one account.",
            "authLead",
        )
        lead.setMaximumWidth(int(LEAD_MAX_WIDTH))
        stack.addWidget(lead)
        return block

    # ── Painting ────────────────────────────────────────────────────────────
    def paintEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        bounds = self.rect()

        ground = QLinearGradient(bounds.topLeft(), bounds.bottomLeft())
        ground.setColorAt(0.0, QColor(theme.AUTH_STAGE_TOP))
        ground.setColorAt(1.0, QColor(theme.AUTH_STAGE_BOTTOM))
        painter.fillRect(bounds, ground)

        glow = QRadialGradient(
            QPointF(bounds.width() * 0.9, bounds.height() * 0.04),
            bounds.width() * 1.05,
        )
        glow.setColorAt(0.0, _tint(theme.PRIMARY, 0.16))
        glow.setColorAt(0.55, _tint(theme.PRIMARY, 0.05))
        glow.setColorAt(1.0, _tint(theme.PRIMARY, 0.0))
        painter.fillRect(bounds, glow)
        painter.end()
