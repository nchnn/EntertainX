"""Lucide icon set.

Every UI icon is the unmodified Lucide SVG stored in ``assets/icons/``
(see AGENTS.md). Icons are tinted at render time so a single asset serves the
muted, accent, active, and disabled states, and so Phase 8 can re-tint the
whole UI without re-downloading anything.

``brand_pixmap`` is EntertainX's own mark and is painted in code; it is not a
third-party logo.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from PySide6.QtCore import QByteArray, QPointF, QRectF, Qt
from PySide6.QtGui import (
    QColor,
    QIcon,
    QLinearGradient,
    QPainter,
    QPixmap,
    QPolygonF,
)
from PySide6.QtSvg import QSvgRenderer

from theme import theme_manager as theme

ICON_DIR = Path(__file__).resolve().parents[2] / "assets" / "icons"

# Friendly alias used by widgets -> exact Lucide file name.
# https://lucide.dev/icons/<slug>
_SLUGS = {
    "user": "user",
    "lock": "lock",
    "mail": "mail",
    "eye": "eye",
    "eye-off": "eye-off",
    "search": "search",
    "play": "play",
    "pause": "pause",
    "star": "star",
    "plus": "plus",
    "chevron": "chevron-right",
    "list": "list",
    "film": "film",
    "music": "music",
    "gamepad": "gamepad-2",
    "gear": "settings",
    "logout": "log-out",
    "close": "x",
    "minimize": "minus",
    "maximize": "square",
    "restore": "copy",
    "check": "check",
    "shield": "shield",
}


@lru_cache(maxsize=None)
def _svg_source(slug: str) -> QByteArray:
    path = ICON_DIR / f"{slug}.svg"
    if not path.exists():
        raise FileNotFoundError(
            f"Missing Lucide icon '{slug}'. Download it from "
            f"https://unpkg.com/lucide-static@latest/icons/{slug}.svg "
            f"into {ICON_DIR}."
        )
    return QByteArray(path.read_bytes())


def _paint(name: str, color: str, px: int) -> QPixmap:
    renderer = QSvgRenderer(_svg_source(_SLUGS[name]))
    pixmap = QPixmap(px, px)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    renderer.render(painter, QRectF(0, 0, px, px))
    # SourceIn recolours the rendered strokes while preserving their alpha.
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
    painter.fillRect(pixmap.rect(), QColor(color))
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
    Raises ``KeyError`` for an unknown icon name.
    """
    if name not in _SLUGS:
        raise KeyError(f"Unknown icon: {name}")
    px = size * 2
    icon = QIcon()
    icon.addPixmap(_paint(name, color, px), QIcon.Mode.Normal, QIcon.State.Off)
    icon.addPixmap(
        _paint(name, active_color or color, px), QIcon.Mode.Normal, QIcon.State.On
    )
    icon.addPixmap(
        _paint(name, theme.TEXT_DISABLED, px), QIcon.Mode.Disabled, QIcon.State.Off
    )
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
