"""Artist profile banner with image, listener stats, play button, and biography."""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPixmap,
)
from PySide6.QtWidgets import (
    QFrame,
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
from ui.components.music.models import ArtistProfile, Track


class ArtistHeader(QFrame):
    """Hero header banner for artist profiles matching streaming service layouts."""

    play_artist_clicked = Signal(object)  # ArtistProfile

    def __init__(
        self,
        profile: ArtistProfile,
        store: ImageStore | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.profile = profile
        self._store = store
        self._pixmap: QPixmap | None = None

        self.setFixedHeight(240)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setStyleSheet(
            f"QFrame {{ background-color: {theme.BG_CARD}; border-radius: 12px; "
            f"border: 1px solid {theme.BORDER}; }}"
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(24)

        # 1. Circular / Rounded Artist Avatar (160x160)
        self.avatar_label = QLabel()
        self.avatar_label.setFixedSize(160, 160)
        self.avatar_label.setStyleSheet(
            f"background-color: {theme.BG_ELEVATED}; border-radius: 80px; "
            f"border: 2px solid {theme.BORDER_STRONG};"
        )
        self.avatar_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.avatar_label)

        if self.profile.image_url and self._store:
            self._store.request(self.profile.image_url, 320, self._on_avatar_loaded, owner=self)
        else:
            self.avatar_label.setPixmap(make_icon("user", theme.TEXT_MUTED, 64).pixmap(64, 64))

        # 2. Artist Details Column
        info_col = QVBoxLayout()
        info_col.setContentsMargins(0, 0, 0, 0)
        info_col.setSpacing(6)
        info_col.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        badge_label = QLabel("VERIFIED ARTIST")
        badge_label.setStyleSheet(
            f"color: {theme.PRIMARY}; font-size: 10px; font-weight: 700; "
            f"letter-spacing: 1px; background: transparent;"
        )
        info_col.addWidget(badge_label)

        self.name_label = QLabel(self.profile.name)
        self.name_label.setStyleSheet(
            f"color: {theme.TEXT_PRIMARY}; font-size: 32px; font-weight: 800; "
            f"background: transparent;"
        )
        info_col.addWidget(self.name_label)

        self.stats_label = QLabel(
            f"{self.profile.monthly_listeners} • {self.profile.subscribers or 'Verified'}"
        )
        self.stats_label.setStyleSheet(
            f"color: {theme.TEXT_MUTED}; font-size: {theme.FONT_SIZE_SM}px; "
            f"background: transparent;"
        )
        info_col.addWidget(self.stats_label)

        if self.profile.bio:
            self.bio_label = QLabel(self.profile.bio)
            self.bio_label.setWordWrap(True)
            self.bio_label.setStyleSheet(
                f"color: {theme.TEXT_SECONDARY}; font-size: {theme.FONT_SIZE_XS}px; "
                f"background: transparent;"
            )
            info_col.addWidget(self.bio_label)

        # 3. Play All button
        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(0, 8, 0, 0)
        btn_row.setSpacing(12)

        self.btn_play_all = QPushButton("  Play Popular")
        self.btn_play_all.setIcon(make_icon("play", theme.TEXT_ON_ACCENT, 18))
        self.btn_play_all.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_play_all.setFixedHeight(38)
        self.btn_play_all.setStyleSheet(
            f"QPushButton {{ background-color: {theme.PRIMARY}; color: {theme.TEXT_ON_ACCENT}; "
            f"border-radius: 19px; padding: 0 20px; font-size: 13px; font-weight: 700; border: none; }} "
            f"QPushButton:hover {{ background-color: {theme.ACCENT_HOVER}; }} "
            f"QPushButton:pressed {{ background-color: {theme.ACCENT_PRESSED}; }}"
        )
        self.btn_play_all.clicked.connect(self._on_play_all)
        btn_row.addWidget(self.btn_play_all)
        btn_row.addStretch(1)

        info_col.addLayout(btn_row)
        layout.addLayout(info_col, 1)

    def _on_avatar_loaded(self, pixmap: QPixmap | None) -> None:
        if pixmap and not pixmap.isNull():
            self._pixmap = pixmap
            scaled = pixmap.scaled(
                160,
                160,
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.avatar_label.setPixmap(scaled)

    def _on_play_all(self) -> None:
        if self.profile.top_tracks:
            get_audio_engine().play_queue(self.profile.top_tracks, start_index=0)
            self.play_artist_clicked.emit(self.profile)
