"""Horizontal track list row for search results, artist discography, and queue."""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, QSize, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QEnterEvent,
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


class TrackRow(QWidget):
    """Compact row displaying track number, art, title, artist, duration, and actions."""

    play_requested = Signal(object)  # Track
    like_toggled = Signal(object, bool)  # Track, is_liked
    queue_add_requested = Signal(object)  # Track
    remove_requested = Signal(object)  # Track

    def __init__(
        self,
        track: Track,
        index: int = 1,
        is_queue_item: bool = False,
        store: ImageStore | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.track = track
        self.index = index
        self._is_queue_item = is_queue_item
        self._store = store
        self._pixmap: QPixmap | None = None
        self._hovered = False
        self._is_liked = False

        self.setFixedHeight(54)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(12)

        # 1. Index / Play icon button
        self.index_label = QLabel(f"{index:02d}")
        self.index_label.setFixedWidth(28)
        self.index_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.index_label.setStyleSheet(
            f"color: {theme.TEXT_MUTED}; font-size: {theme.FONT_SIZE_SM}px; font-weight: 500;"
        )
        layout.addWidget(self.index_label)

        # 2. Thumbnail cover (40x40)
        self.thumb_label = QLabel()
        self.thumb_label.setFixedSize(40, 40)
        self.thumb_label.setStyleSheet(
            f"background-color: {theme.BG_CARD}; border-radius: 6px;"
        )
        layout.addWidget(self.thumb_label)

        if self.track.artwork_url and self._store:
            self._store.request(self.track.artwork_url, 80, self._on_thumb_loaded, owner=self)

        # 3. Title & Artist stack
        info_col = QVBoxLayout()
        info_col.setContentsMargins(0, 0, 0, 0)
        info_col.setSpacing(2)

        self.title_label = QLabel(self.track.title)
        self.title_label.setStyleSheet(
            f"color: {theme.TEXT_PRIMARY}; font-size: {theme.FONT_SIZE_SM}px; font-weight: 600;"
        )
        info_col.addWidget(self.title_label)

        self.sub_label = QLabel(f"{self.track.artist} • {self.track.album or 'Single'}")
        self.sub_label.setStyleSheet(
            f"color: {theme.TEXT_MUTED}; font-size: {theme.FONT_SIZE_XS}px;"
        )
        info_col.addWidget(self.sub_label)

        layout.addLayout(info_col, 1)

        # 4. Quality Badge
        if self.track.quality:
            self.badge_label = QLabel(self.track.quality)
            self.badge_label.setStyleSheet(
                f"color: {theme.PRIMARY}; background-color: rgba(255, 255, 255, 0.05); "
                f"border-radius: 4px; padding: 2px 6px; font-size: 9px; font-weight: 700;"
            )
            layout.addWidget(self.badge_label)

        # 5. Duration
        self.duration_label = QLabel(self.track.duration_formatted)
        self.duration_label.setStyleSheet(
            f"color: {theme.TEXT_MUTED}; font-size: {theme.FONT_SIZE_XS}px;"
        )
        layout.addWidget(self.duration_label)

        # 6. Action buttons
        if not self._is_queue_item:
            self.btn_queue = QPushButton()
            self.btn_queue.setFixedSize(30, 30)
            self.btn_queue.setIcon(make_icon("plus", theme.TEXT_MUTED, 16))
            self.btn_queue.setToolTip("Add to Queue")
            self.btn_queue.setStyleSheet("background: transparent; border: none;")
            self.btn_queue.setCursor(Qt.CursorShape.PointingHandCursor)
            self.btn_queue.clicked.connect(self._on_add_to_queue)
            layout.addWidget(self.btn_queue)

        self.btn_heart = QPushButton()
        self.btn_heart.setFixedSize(30, 30)
        self.btn_heart.setIcon(make_icon("heart", theme.TEXT_MUTED, 16))
        self.btn_heart.setToolTip("Favorite Track")
        self.btn_heart.setStyleSheet("background: transparent; border: none;")
        self.btn_heart.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_heart.clicked.connect(self._toggle_like)
        layout.addWidget(self.btn_heart)

        if self._is_queue_item:
            self.btn_remove = QPushButton()
            self.btn_remove.setFixedSize(30, 30)
            self.btn_remove.setIcon(make_icon("close", theme.TEXT_MUTED, 16))
            self.btn_remove.setToolTip("Remove from Queue")
            self.btn_remove.setStyleSheet("background: transparent; border: none;")
            self.btn_remove.setCursor(Qt.CursorShape.PointingHandCursor)
            self.btn_remove.clicked.connect(lambda: self.remove_requested.emit(self.track))
            layout.addWidget(self.btn_remove)

        # Listen to audio engine for active highlight
        engine = get_audio_engine()
        engine.track_changed.connect(self._update_playing_state)
        self._update_playing_state(engine.current_track)

    def _on_thumb_loaded(self, pixmap: QPixmap | None) -> None:
        if pixmap and not pixmap.isNull():
            self._pixmap = pixmap
            scaled = pixmap.scaled(
                40,
                40,
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.thumb_label.setPixmap(scaled)

    def _toggle_like(self) -> None:
        self._is_liked = not self._is_liked
        color = theme.PRIMARY if self._is_liked else theme.TEXT_MUTED
        self.btn_heart.setIcon(make_icon("heart", color, 16))
        self.like_toggled.emit(self.track, self._is_liked)

    def _on_add_to_queue(self) -> None:
        get_audio_engine().add_to_queue(self.track)
        self.queue_add_requested.emit(self.track)

    def _update_playing_state(self, current: Track | None) -> None:
        is_cur = current is not None and current.id == self.track.id
        if is_cur:
            self.title_label.setStyleSheet(
                f"color: {theme.PRIMARY}; font-size: {theme.FONT_SIZE_SM}px; font-weight: 700;"
            )
            self.index_label.setText("▶")
            self.index_label.setStyleSheet(
                f"color: {theme.PRIMARY}; font-size: {theme.FONT_SIZE_SM}px; font-weight: 700;"
            )
        else:
            self.title_label.setStyleSheet(
                f"color: {theme.TEXT_PRIMARY}; font-size: {theme.FONT_SIZE_SM}px; font-weight: 600;"
            )
            self.index_label.setText(f"{self.index:02d}")
            self.index_label.setStyleSheet(
                f"color: {theme.TEXT_MUTED}; font-size: {theme.FONT_SIZE_SM}px; font-weight: 500;"
            )

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
            self.play_requested.emit(self.track)
            get_audio_engine().play_track(self.track)
            event.accept()
            return
        super().mousePressEvent(event)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        rect = QRectF(0, 0, self.width(), self.height())

        if self._hovered:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(theme.BG_ELEVATED))
            painter.drawRoundedRect(rect, 8, 8)

        painter.end()
        super().paintEvent(event)
