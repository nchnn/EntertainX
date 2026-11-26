"""Playback queue panel showing now-playing track and upcoming track list."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from api.images import ImageStore
from theme import theme_manager as theme
from ui.components.icons import make_icon
from ui.components.music.audio_engine import get_audio_engine
from ui.components.music.models import Track
from ui.components.music.track_row import TrackRow


class QueueDrawer(QFrame):
    """Side drawer panel displaying the active queue and up-next list."""

    close_requested = Signal()

    def __init__(
        self,
        store: ImageStore | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._store = store
        self._engine = get_audio_engine()

        self.setObjectName("QueueDrawer")
        self.setStyleSheet(
            f"QFrame#QueueDrawer {{ background-color: {theme.BG_DARK}; "
            f"border-left: 1px solid {theme.BORDER}; }}"
        )
        self.setMinimumWidth(340)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        # ── Header ──────────────────────────────────────────────────────────
        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        header_row.setSpacing(8)

        title_label = QLabel("Queue")
        title_label.setStyleSheet(
            f"color: {theme.TEXT_PRIMARY}; font-size: {theme.FONT_SIZE_LG}px; font-weight: 700;"
        )
        header_row.addWidget(title_label, 1)

        self.btn_clear = QPushButton("Clear")
        self.btn_clear.setStyleSheet(
            f"color: {theme.TEXT_MUTED}; background: transparent; border: none; font-size: 12px;"
        )
        self.btn_clear.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_clear.clicked.connect(self._engine.clear_queue)
        header_row.addWidget(self.btn_clear)

        self.btn_close = QPushButton()
        self.btn_close.setFixedSize(28, 28)
        self.btn_close.setIcon(make_icon("close", theme.TEXT_MUTED, 16))
        self.btn_close.setStyleSheet("background: transparent; border: none;")
        self.btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_close.clicked.connect(self.close_requested.emit)
        header_row.addWidget(self.btn_close)

        main_layout.addLayout(header_row)

        # ── Now Playing Section ─────────────────────────────────────────────
        now_header = QLabel("Now Playing")
        now_header.setStyleSheet(
            f"color: {theme.TEXT_MUTED}; font-size: {theme.FONT_SIZE_SM}px; font-weight: 600;"
        )
        main_layout.addWidget(now_header)

        self.now_box = QFrame()
        self.now_box.setStyleSheet(
            f"background-color: {theme.BG_CARD}; border-radius: 8px; border: 1px solid {theme.BORDER};"
        )
        now_layout = QHBoxLayout(self.now_box)
        now_layout.setContentsMargins(10, 10, 10, 10)
        now_layout.setSpacing(10)

        self.now_cover = QLabel()
        self.now_cover.setFixedSize(44, 44)
        self.now_cover.setStyleSheet("border-radius: 6px; background-color: rgba(255,255,255,0.05);")
        now_layout.addWidget(self.now_cover)

        now_meta = QVBoxLayout()
        now_meta.setContentsMargins(0, 0, 0, 0)
        now_meta.setSpacing(2)

        self.now_title = QLabel("No track playing")
        self.now_title.setStyleSheet(
            f"color: {theme.TEXT_PRIMARY}; font-size: {theme.FONT_SIZE_SM}px; font-weight: 600;"
        )
        now_meta.addWidget(self.now_title)

        self.now_artist = QLabel("Select a song to start")
        self.now_artist.setStyleSheet(
            f"color: {theme.TEXT_MUTED}; font-size: {theme.FONT_SIZE_XS}px;"
        )
        now_meta.addWidget(self.now_artist)
        now_layout.addLayout(now_meta, 1)

        main_layout.addWidget(self.now_box)

        # ── Up Next Section ─────────────────────────────────────────────────
        next_header = QLabel("Up Next")
        next_header.setStyleSheet(
            f"color: {theme.TEXT_MUTED}; font-size: {theme.FONT_SIZE_SM}px; font-weight: 600;"
        )
        main_layout.addWidget(next_header)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setStyleSheet(
            "QScrollArea { background: transparent; border: none; } "
            "QScrollBar:vertical { width: 6px; background: transparent; } "
            f"QScrollBar::handle:vertical {{ background: {theme.BORDER}; border-radius: 3px; }} "
            "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }"
        )

        self.queue_container = QWidget()
        self.queue_container.setStyleSheet("background: transparent;")
        self.queue_layout = QVBoxLayout(self.queue_container)
        self.queue_layout.setContentsMargins(0, 0, 0, 16)
        self.queue_layout.setSpacing(4)
        self.queue_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.scroll_area.setWidget(self.queue_container)
        main_layout.addWidget(self.scroll_area, 1)

        # Listen to audio engine
        self._engine.track_changed.connect(self._on_track_changed)
        self._engine.queue_updated.connect(self._refresh_queue)

        self._on_track_changed(self._engine.current_track)
        self._refresh_queue()

    def _on_track_changed(self, track: Track | None) -> None:
        if track:
            self.now_title.setText(track.title)
            self.now_artist.setText(track.artist)
            if track.artwork_url and self._store:
                self._store.request(track.artwork_url, 88, self._on_now_cover_loaded, owner=self)
            else:
                self.now_cover.setPixmap(make_icon("music", theme.TEXT_MUTED, 24).pixmap(24, 24))
        else:
            self.now_title.setText("No track playing")
            self.now_artist.setText("Select a song to start")
            self.now_cover.clear()

        self._refresh_queue()

    def _on_now_cover_loaded(self, pixmap: QPixmap | None) -> None:
        if pixmap and not pixmap.isNull():
            scaled = pixmap.scaled(
                44,
                44,
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.now_cover.setPixmap(scaled)

    def _refresh_queue(self) -> None:
        # Clear existing items
        while self.queue_layout.count() > 0:
            item = self.queue_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        queue = self._engine.queue
        current_idx = self._engine.current_index

        # Only list tracks after the current track in Up Next
        upcoming = queue[current_idx + 1 :] if current_idx >= 0 else queue

        if not upcoming:
            empty = QLabel("Queue is empty")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setStyleSheet(
                f"color: {theme.TEXT_MUTED}; font-size: {theme.FONT_SIZE_SM}px; padding: 30px 0;"
            )
            self.queue_layout.addWidget(empty)
            return

        for offset, track in enumerate(upcoming):
            actual_idx = current_idx + 1 + offset if current_idx >= 0 else offset
            row = TrackRow(
                track,
                index=offset + 1,
                is_queue_item=True,
                store=self._store,
                parent=self.queue_container,
            )
            row.play_requested.connect(lambda t, idx=actual_idx: self._play_at(idx))
            row.remove_requested.connect(lambda t, idx=actual_idx: self._engine.remove_from_queue(idx))
            self.queue_layout.addWidget(row)

    def _play_at(self, idx: int) -> None:
        queue = self._engine.queue
        if 0 <= idx < len(queue):
            self._engine.play_track(queue[idx])
