"""Square album cover card with hover play action and quality badges."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QPointF, QRectF, QSize, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QCursor,
    QEnterEvent,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from api.images import ImageStore
from theme import theme_manager as theme
from ui.components.icons import make_icon
from ui.components.music.audio_engine import get_audio_engine
from ui.components.music.models import Track

CARD_WIDTH = 176
ARTWORK_SIZE = 176


class AlbumCover(QWidget):
    """Painted rounded square cover art with hover play button."""

    play_requested = Signal()

    def __init__(
        self,
        artwork_url: str = "",
        quality: str = "",
        store: ImageStore | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setFixedSize(ARTWORK_SIZE, ARTWORK_SIZE)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._url = artwork_url
        self._quality = quality
        self._store = store
        self._pixmap: QPixmap | None = None
        self._hovered = False

        if self._url and self._store:
            self._store.request(self._url, ARTWORK_SIZE * 2, self._on_pixmap_loaded, owner=self)

    def _on_pixmap_loaded(self, pixmap: QPixmap | None) -> None:
        if pixmap and not pixmap.isNull():
            self._pixmap = pixmap
            self.update()

    def enterEvent(self, event: QEnterEvent) -> None:
        self._hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._hovered = False
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.play_requested.emit()
            event.accept()
            return
        super().mousePressEvent(event)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        rect = QRectF(0, 0, self.width(), self.height())
        radius = float(theme.RADIUS_MD)

        # Clip path for rounded cover
        path = QPainterPath()
        path.addRoundedRect(rect, radius, radius)
        painter.setClipPath(path)

        if self._pixmap and not self._pixmap.isNull():
            # Draw cover scaled to fill
            painter.drawPixmap(
                0,
                0,
                self.width(),
                self.height(),
                self._pixmap.scaled(
                    self.size() * 2,
                    Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                    Qt.TransformationMode.SmoothTransformation,
                ),
            )
        else:
            # Fallback rich gradient
            gradient = QLinearGradient(0, 0, rect.width(), rect.height())
            gradient.setColorAt(0.0, QColor(theme.BG_CARD))
            gradient.setColorAt(1.0, QColor(theme.BG_ELEVATED))
            painter.fillRect(rect, gradient)

            # Center music icon
            icon_px = 44
            icon_pix = make_icon("music", theme.TEXT_MUTED, icon_px).pixmap(icon_px, icon_px)
            cx = (rect.width() - icon_px) / 2
            cy = (rect.height() - icon_px) / 2
            painter.drawPixmap(int(cx), int(cy), icon_pix)

        # Quality badge pill
        if self._quality:
            badge_rect = QRectF(rect.width() - 56, 8, 48, 18)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(0, 0, 0, 180))
            painter.drawRoundedRect(badge_rect, 4, 4)

            painter.setPen(QColor(theme.PRIMARY))
            font = painter.font()
            font.setPixelSize(9)
            font.setBold(True)
            painter.setFont(font)
            painter.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, self._quality)

        # Hover overlay and play button
        if self._hovered:
            painter.fillRect(rect, QColor(0, 0, 0, 90))

            # Floating circle play button
            btn_size = 46.0
            bx = rect.width() - btn_size - 10
            by = rect.height() - btn_size - 10
            btn_rect = QRectF(bx, by, btn_size, btn_size)

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(theme.PRIMARY))
            painter.drawEllipse(btn_rect)

            play_icon = make_icon("play", theme.TEXT_ON_ACCENT, 20).pixmap(20, 20)
            painter.drawPixmap(int(bx + 14), int(by + 13), play_icon)

        # Border outline
        painter.setClipping(False)
        painter.setPen(QPen(QColor(theme.BORDER), 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(rect.adjusted(0.5, 0.5, -0.5, -0.5), radius, radius)
        painter.end()


class TrackCard(QWidget):
    """Individual music track card displaying cover art, title, and artist."""

    play_clicked = Signal(object)  # Track
    card_clicked = Signal(object)  # Track

    def __init__(
        self,
        track: Track,
        store: ImageStore | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.track = track
        self.setFixedWidth(CARD_WIDTH)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Minimum)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # Cover
        self.cover = AlbumCover(
            artwork_url=track.artwork_url,
            quality=track.quality,
            store=store,
            parent=self,
        )
        self.cover.play_requested.connect(self._on_play)
        layout.addWidget(self.cover)

        # Title Label
        self.title_label = QLabel(track.title)
        self.title_label.setObjectName("MusicCardTitle")
        self.title_label.setWordWrap(False)
        font = self.title_label.font()
        font.setPixelSize(theme.FONT_SIZE_SM)
        font.setBold(True)
        self.title_label.setFont(font)
        self.title_label.setStyleSheet(
            f"color: {theme.TEXT_PRIMARY}; font-weight: 600; background: transparent;"
        )
        layout.addWidget(self.title_label)

        # Artist Label
        self.artist_label = QLabel(track.artist)
        self.artist_label.setObjectName("MusicCardArtist")
        self.artist_label.setWordWrap(False)
        art_font = self.artist_label.font()
        art_font.setPixelSize(theme.FONT_SIZE_XS)
        self.artist_label.setFont(art_font)
        self.artist_label.setStyleSheet(
            f"color: {theme.TEXT_MUTED}; background: transparent;"
        )
        layout.addWidget(self.artist_label)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._on_play()
            event.accept()
            return
        super().mousePressEvent(event)

    def _on_play(self) -> None:
        self.play_clicked.emit(self.track)
        get_audio_engine().play_track(self.track)
