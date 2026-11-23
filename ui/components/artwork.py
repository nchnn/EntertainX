"""Painting helpers shared by the tiles, hero, hover preview, and detail panel."""

from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPainterPath, QPixmap


def rounded_path(rect: QRectF, radius: float) -> QPainterPath:
    path = QPainterPath()
    path.addRoundedRect(rect, radius, radius)
    return path


def draw_cover(
    painter: QPainter,
    target: QRectF,
    pixmap: QPixmap,
    anchor_x: float = 0.5,
    anchor_y: float = 0.5,
) -> None:
    """Fill ``target`` with ``pixmap``, cropping the overflow (CSS cover).

    ``anchor_x``/``anchor_y`` (0..1) choose which part survives the crop.
    """
    if pixmap.isNull() or target.width() <= 0 or target.height() <= 0:
        return
    width, height = float(pixmap.width()), float(pixmap.height())
    wanted = target.width() / target.height()
    if width / height > wanted:
        crop_w = height * wanted
        source = QRectF((width - crop_w) * anchor_x, 0.0, crop_w, height)
    else:
        crop_h = width / wanted
        source = QRectF(0.0, (height - crop_h) * anchor_y, width, crop_h)
    painter.save()
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
    painter.drawPixmap(target, pixmap, source)
    painter.restore()


def fill_vertical_scrim(
    painter: QPainter,
    rect: QRectF,
    start: float,
    alpha: float,
    color: str = "#000000",
) -> None:
    """Darken the lower part of ``rect``: clear at ``start`` (0..1), ``alpha`` at base."""
    gradient = QLinearGradient(rect.topLeft(), rect.bottomLeft())
    clear = QColor(color)
    clear.setAlphaF(0.0)
    dark = QColor(color)
    dark.setAlphaF(alpha)
    gradient.setColorAt(0.0, clear)
    gradient.setColorAt(max(0.0, min(1.0, start)), clear)
    gradient.setColorAt(1.0, dark)
    painter.fillRect(rect, gradient)


def fill_horizontal_scrim(
    painter: QPainter,
    rect: QRectF,
    end: float,
    alpha: float,
    color: str = "#000000",
) -> None:
    """Darken the left edge of ``rect``: ``alpha`` at the left, clear at ``end`` (0..1)."""
    gradient = QLinearGradient(rect.topLeft(), rect.topRight())
    dark = QColor(color)
    dark.setAlphaF(alpha)
    clear = QColor(color)
    clear.setAlphaF(0.0)
    gradient.setColorAt(0.0, dark)
    gradient.setColorAt(max(0.0, min(1.0, end)), clear)
    gradient.setColorAt(1.0, clear)
    painter.fillRect(rect, gradient)


def pill(
    painter: QPainter,
    x: float,
    y: float,
    text: str,
    fill: QColor,
    ink: QColor,
    pixel_size: int = 10,
) -> float:
    """Draw a small rounded label at (x, y); returns its width."""
    font = painter.font()
    font.setPixelSize(pixel_size)
    font.setBold(True)
    painter.save()
    painter.setFont(font)
    metrics = painter.fontMetrics()
    width = metrics.horizontalAdvance(text) + 14
    height = metrics.height() + 4
    rect = QRectF(x, y, width, height)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(fill)
    painter.drawRoundedRect(rect, height / 2, height / 2)
    painter.setPen(ink)
    painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)
    painter.restore()
    return width
