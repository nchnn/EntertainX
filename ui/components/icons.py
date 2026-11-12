"""Painted icon set.

The project ships no binary assets, so every icon is drawn with ``QPainter``
into a pixmap at the requested size. Icons are tinted with theme colours at
construction time; ``make_icon`` can supply a second tint that Qt uses while a
checkable button is in the ``On`` state.
"""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QColor,
    QIcon,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QPolygonF,
)

from theme import theme_manager as theme

_STROKE_WIDTH = 1.8


def _pen(color: str, width: float = _STROKE_WIDTH) -> QPen:
    pen = QPen(QColor(color), width)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    return pen


def _fill(p: QPainter, color: str) -> None:
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(color))


def _stroke(p: QPainter, color: str, width: float = _STROKE_WIDTH) -> None:
    p.setPen(_pen(color, width))
    p.setBrush(Qt.BrushStyle.NoBrush)


# ── Individual glyphs, drawn on a 24x24 grid ───────────────────────────────
def _user(p: QPainter, c: str) -> None:
    _stroke(p, c)
    p.drawEllipse(QPointF(12, 8.2), 3.5, 3.5)
    p.drawArc(QRectF(4.5, 12.5, 15, 13), 0, 180 * 16)


def _lock(p: QPainter, c: str) -> None:
    _stroke(p, c)
    p.drawRoundedRect(QRectF(6, 10.5, 12, 9), 2.2, 2.2)
    p.drawArc(QRectF(8, 4.5, 8, 10), 0, 180 * 16)
    p.setBrush(QColor(c))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawEllipse(QPointF(12, 15), 1.2, 1.2)


def _eye_outline(p: QPainter, c: str) -> None:
    path = QPainterPath()
    path.moveTo(2.8, 12)
    path.quadTo(7.4, 5.3, 12, 5.3)
    path.quadTo(16.6, 5.3, 21.2, 12)
    path.quadTo(16.6, 18.7, 12, 18.7)
    path.quadTo(7.4, 18.7, 2.8, 12)
    path.closeSubpath()
    _stroke(p, c)
    p.drawPath(path)


def _eye(p: QPainter, c: str) -> None:
    _eye_outline(p, c)
    p.setBrush(QColor(c))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawEllipse(QPointF(12, 12), 2.6, 2.6)


def _eye_off(p: QPainter, c: str) -> None:
    _eye_outline(p, c)
    p.setBrush(QColor(c))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawEllipse(QPointF(12, 12), 2.4, 2.4)
    _stroke(p, c, 2.0)
    p.drawLine(QPointF(4.5, 19.5), QPointF(19.5, 4.5))


def _search(p: QPainter, c: str) -> None:
    _stroke(p, c)
    p.drawEllipse(QPointF(10.8, 10.8), 6.2, 6.2)
    p.drawLine(QPointF(15.4, 15.4), QPointF(20, 20))


def _play(p: QPainter, c: str) -> None:
    _fill(p, c)
    p.drawPolygon(QPolygonF([QPointF(8.5, 4.8), QPointF(19, 12), QPointF(8.5, 19.2)]))


def _star(p: QPainter, c: str) -> None:
    import math

    _fill(p, c)
    points = []
    for i in range(10):
        radius = 9.2 if i % 2 == 0 else 4.1
        angle = math.radians(-90 + i * 36)
        points.append(QPointF(12 + radius * math.cos(angle), 12.4 + radius * math.sin(angle)))
    p.drawPolygon(QPolygonF(points))


def _plus(p: QPainter, c: str) -> None:
    _stroke(p, c, 2.0)
    p.drawLine(QPointF(12, 5), QPointF(12, 19))
    p.drawLine(QPointF(5, 12), QPointF(19, 12))


def _chevron(p: QPainter, c: str) -> None:
    _stroke(p, c, 2.0)
    p.drawPolyline(QPolygonF([QPointF(9.5, 5.5), QPointF(16, 12), QPointF(9.5, 18.5)]))


def _list(p: QPainter, c: str) -> None:
    _stroke(p, c)
    for y in (7, 12, 17):
        p.drawLine(QPointF(4.5, y), QPointF(19.5, y))


def _film(p: QPainter, c: str) -> None:
    _stroke(p, c)
    p.drawRoundedRect(QRectF(3.5, 6, 17, 12), 2, 2)
    p.drawLine(QPointF(8.5, 6), QPointF(8.5, 18))
    p.drawLine(QPointF(15.5, 6), QPointF(15.5, 18))


def _music(p: QPainter, c: str) -> None:
    _stroke(p, c)
    p.drawEllipse(QPointF(8, 16.5), 3.2, 2.6)
    p.drawLine(QPointF(11.2, 16.5), QPointF(11.2, 5.5))
    p.drawLine(QPointF(11.2, 5.5), QPointF(18.5, 7.2))
    p.drawLine(QPointF(18.5, 7.2), QPointF(18.5, 13.5))


def _gamepad(p: QPainter, c: str) -> None:
    _stroke(p, c)
    p.drawRoundedRect(QRectF(3, 8, 18, 9.5), 4.5, 4.5)
    p.drawLine(QPointF(8, 11.5), QPointF(8, 14.5))
    p.drawLine(QPointF(6.5, 13), QPointF(9.5, 13))
    p.setBrush(QColor(c))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawEllipse(QPointF(16, 12.2), 1.05, 1.05)
    p.drawEllipse(QPointF(18, 14.2), 1.05, 1.05)


def _gear(p: QPainter, c: str) -> None:
    import math

    _stroke(p, c, 1.7)
    p.drawEllipse(QPointF(12, 12), 3.3, 3.3)
    for i in range(8):
        angle = math.radians(i * 45)
        p.drawLine(
            QPointF(12 + 5.6 * math.cos(angle), 12 + 5.6 * math.sin(angle)),
            QPointF(12 + 8.4 * math.cos(angle), 12 + 8.4 * math.sin(angle)),
        )


def _logout(p: QPainter, c: str) -> None:
    _stroke(p, c)
    p.drawPolyline(
        QPolygonF(
            [
                QPointF(10, 4.5),
                QPointF(4.5, 4.5),
                QPointF(4.5, 19.5),
                QPointF(10, 19.5),
            ]
        )
    )
    p.drawLine(QPointF(10, 12), QPointF(20, 12))
    p.drawPolyline(QPolygonF([QPointF(16.5, 8.5), QPointF(20, 12), QPointF(16.5, 15.5)]))


def _close(p: QPainter, c: str) -> None:
    _stroke(p, c, 1.7)
    p.drawLine(QPointF(6.5, 6.5), QPointF(17.5, 17.5))
    p.drawLine(QPointF(17.5, 6.5), QPointF(6.5, 17.5))


def _minimize(p: QPainter, c: str) -> None:
    _stroke(p, c, 1.5)
    p.drawLine(QPointF(6, 12.5), QPointF(18, 12.5))


def _maximize(p: QPainter, c: str) -> None:
    _stroke(p, c, 1.5)
    p.drawRoundedRect(QRectF(6.5, 6.5, 11, 11), 1.5, 1.5)


def _restore(p: QPainter, c: str) -> None:
    _stroke(p, c, 1.5)
    p.drawRoundedRect(QRectF(5.5, 8.5, 9.5, 9.5), 1.5, 1.5)
    p.drawPolyline(
        QPolygonF(
            [
                QPointF(9, 8.5),
                QPointF(9, 5.5),
                QPointF(18.5, 5.5),
                QPointF(18.5, 15),
                QPointF(15, 15),
            ]
        )
    )


def _mail(p: QPainter, c: str) -> None:
    _stroke(p, c)
    p.drawRoundedRect(QRectF(3.5, 6, 17, 12), 2.2, 2.2)
    p.drawPolyline(
        QPolygonF([QPointF(4.5, 7.5), QPointF(12, 13.2), QPointF(19.5, 7.5)])
    )


def _check(p: QPainter, c: str) -> None:
    _stroke(p, c, 2.2)
    p.drawPolyline(QPolygonF([QPointF(5, 12.5), QPointF(10, 17.5), QPointF(19, 6.5)]))


_GLYPHS = {
    "user": _user,
    "lock": _lock,
    "mail": _mail,
    "eye": _eye,
    "eye-off": _eye_off,
    "search": _search,
    "play": _play,
    "star": _star,
    "plus": _plus,
    "chevron": _chevron,
    "list": _list,
    "film": _film,
    "music": _music,
    "gamepad": _gamepad,
    "gear": _gear,
    "logout": _logout,
    "close": _close,
    "minimize": _minimize,
    "maximize": _maximize,
    "restore": _restore,
    "check": _check,
}


def _paint(name: str, color: str, px: int) -> QPixmap:
    pixmap = QPixmap(px, px)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.scale(px / 24.0, px / 24.0)
    _GLYPHS[name](painter, color)
    painter.end()
    return pixmap


def make_icon(
    name: str,
    color: str,
    size: int = 18,
    active_color: str | None = None,
) -> QIcon:
    """Return a crisp ``QIcon`` for ``name`` tinted with ``color``.

    ``active_color`` is used while a checkable button is in the ``On`` state.
    Raises ``KeyError`` for an unknown glyph name.
    """
    if name not in _GLYPHS:
        raise KeyError(f"Unknown icon: {name}")
    px = size * 2
    icon = QIcon()
    icon.addPixmap(_paint(name, color, px), QIcon.Mode.Normal, QIcon.State.Off)
    icon.addPixmap(
        _paint(name, active_color or color, px), QIcon.Mode.Normal, QIcon.State.On
    )
    icon.addPixmap(_paint(name, theme.TEXT_DISABLED, px), QIcon.Mode.Disabled, QIcon.State.Off)
    return icon


def brand_pixmap(size: int = 32) -> QPixmap:
    """The EntertainX mark: rounded pink tile with a dark play triangle."""
    px = size * 2
    pixmap = QPixmap(px, px)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.scale(px / 48.0, px / 48.0)

    gradient = QLinearGradient(0, 0, 48, 48)
    gradient.setColorAt(0.0, QColor(theme.SECONDARY))
    gradient.setColorAt(1.0, QColor(theme.ACCENT_PRESSED))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(gradient)
    painter.drawRoundedRect(QRectF(1, 1, 46, 46), 13, 13)

    painter.setBrush(QColor(theme.TEXT_ON_ACCENT))
    painter.drawPolygon(
        QPolygonF([QPointF(18.5, 14), QPointF(33.5, 24), QPointF(18.5, 34)])
    )
    painter.end()
    pixmap.setDevicePixelRatio(2.0)
    return pixmap


def app_icon() -> QIcon:
    """Window icon built from :func:`brand_pixmap` at common sizes."""
    icon = QIcon()
    for size in (16, 24, 32, 48, 64, 128):
        icon.addPixmap(brand_pixmap(size))
    return icon
