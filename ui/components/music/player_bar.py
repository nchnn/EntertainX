"""Persistent bottom playback bar with controls, scrubber, volume, and panel toggles."""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, QSize, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from api.images import ImageStore
from theme import theme_manager as theme
from ui.components.icons import make_icon
from ui.components.music.audio_engine import get_audio_engine
from ui.components.music.models import Track, format_time


class PlayerBar(QFrame):
    """Bottom playback controller bar showing active track, controls, and volume."""

    lyrics_toggled = Signal(bool)
    queue_toggled = Signal(bool)

    def __init__(
        self,
        store: ImageStore | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._store = store
        self._engine = get_audio_engine()
        self._slider_dragging = False
        self._lyrics_active = False
        self._queue_active = False
        self._is_liked = False

        self.setFixedHeight(76)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setStyleSheet(
            f"PlayerBar {{ background-color: {theme.BG_DARK}; "
            f"border-top: 1px solid {theme.BORDER}; }}"
        )

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(16, 8, 16, 8)
        main_layout.setSpacing(16)

        # ── Left Zone: Track Metadata & Heart (min 220px) ───────────────────
        left_box = QWidget()
        left_layout = QHBoxLayout(left_box)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(12)

        self.cover_label = QLabel()
        self.cover_label.setFixedSize(48, 48)
        self.cover_label.setStyleSheet(
            f"background-color: {theme.BG_CARD}; border-radius: 6px; border: 1px solid {theme.BORDER};"
        )
        self.cover_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_layout.addWidget(self.cover_label)

        meta_col = QVBoxLayout()
        meta_col.setContentsMargins(0, 0, 0, 0)
        meta_col.setSpacing(2)

        self.title_label = QLabel("No track playing")
        self.title_label.setStyleSheet(
            f"color: {theme.TEXT_PRIMARY}; font-size: {theme.FONT_SIZE_SM}px; font-weight: 600;"
        )
        meta_col.addWidget(self.title_label)

        self.artist_label = QLabel("EntertainX Music")
        self.artist_label.setStyleSheet(
            f"color: {theme.TEXT_MUTED}; font-size: {theme.FONT_SIZE_XS}px;"
        )
        meta_col.addWidget(self.artist_label)
        left_layout.addLayout(meta_col)

        self.btn_heart = QPushButton()
        self.btn_heart.setFixedSize(32, 32)
        self.btn_heart.setIcon(make_icon("heart", theme.TEXT_MUTED, 18))
        self.btn_heart.setToolTip("Like Track")
        self.btn_heart.setStyleSheet("background: transparent; border: none;")
        self.btn_heart.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_heart.clicked.connect(self._toggle_like)
        left_layout.addWidget(self.btn_heart)

        left_box.setMinimumWidth(220)
        left_box.setMaximumWidth(320)
        main_layout.addWidget(left_box, 0)

        # ── Center Zone: Transport & Scrubber Slider ────────────────────────
        center_box = QWidget()
        center_layout = QVBoxLayout(center_box)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(4)
        center_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Control Buttons row
        ctrl_row = QHBoxLayout()
        ctrl_row.setContentsMargins(0, 0, 0, 0)
        ctrl_row.setSpacing(16)
        ctrl_row.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.btn_shuffle = QPushButton()
        self.btn_shuffle.setFixedSize(28, 28)
        self.btn_shuffle.setIcon(make_icon("shuffle", theme.TEXT_MUTED, 16))
        self.btn_shuffle.setToolTip("Shuffle Queue")
        self.btn_shuffle.setStyleSheet("background: transparent; border: none;")
        self.btn_shuffle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_shuffle.clicked.connect(self._toggle_shuffle)
        ctrl_row.addWidget(self.btn_shuffle)

        self.btn_prev = QPushButton()
        self.btn_prev.setFixedSize(30, 30)
        self.btn_prev.setIcon(make_icon("skip-back", theme.TEXT_PRIMARY, 18))
        self.btn_prev.setToolTip("Previous Track")
        self.btn_prev.setStyleSheet("background: transparent; border: none;")
        self.btn_prev.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_prev.clicked.connect(self._engine.previous_track)
        ctrl_row.addWidget(self.btn_prev)

        self.btn_play = QPushButton()
        self.btn_play.setFixedSize(38, 38)
        self.btn_play.setIcon(make_icon("play", theme.TEXT_ON_ACCENT, 20))
        self.btn_play.setToolTip("Play / Pause")
        self.btn_play.setStyleSheet(
            f"QPushButton {{ background-color: {theme.PRIMARY}; border-radius: 19px; border: none; }} "
            f"QPushButton:hover {{ background-color: {theme.ACCENT_HOVER}; }} "
            f"QPushButton:pressed {{ background-color: {theme.ACCENT_PRESSED}; }}"
        )
        self.btn_play.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_play.clicked.connect(self._engine.toggle_play_pause)
        ctrl_row.addWidget(self.btn_play)

        self.btn_next = QPushButton()
        self.btn_next.setFixedSize(30, 30)
        self.btn_next.setIcon(make_icon("skip-forward", theme.TEXT_PRIMARY, 18))
        self.btn_next.setToolTip("Next Track")
        self.btn_next.setStyleSheet("background: transparent; border: none;")
        self.btn_next.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_next.clicked.connect(self._engine.next_track)
        ctrl_row.addWidget(self.btn_next)

        self.btn_repeat = QPushButton()
        self.btn_repeat.setFixedSize(28, 28)
        self.btn_repeat.setIcon(make_icon("repeat", theme.TEXT_MUTED, 16))
        self.btn_repeat.setToolTip("Repeat")
        self.btn_repeat.setStyleSheet("background: transparent; border: none;")
        self.btn_repeat.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_repeat.clicked.connect(self._toggle_repeat)
        ctrl_row.addWidget(self.btn_repeat)

        center_layout.addLayout(ctrl_row)

        # Scrubber row
        scrub_row = QHBoxLayout()
        scrub_row.setContentsMargins(0, 0, 0, 0)
        scrub_row.setSpacing(10)

        self.pos_label = QLabel("0:00")
        self.pos_label.setFixedWidth(36)
        self.pos_label.setStyleSheet(
            f"color: {theme.TEXT_MUTED}; font-size: {theme.FONT_SIZE_XS}px;"
        )
        self.pos_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        scrub_row.addWidget(self.pos_label)

        self.scrubber = QSlider(Qt.Orientation.Horizontal)
        self.scrubber.setRange(0, 1000)
        self.scrubber.setValue(0)
        self.scrubber.setCursor(Qt.CursorShape.PointingHandCursor)
        self.scrubber.setStyleSheet(
            f"QSlider::groove:horizontal {{ height: 4px; background: {theme.BORDER}; border-radius: 2px; }} "
            f"QSlider::sub-page:horizontal {{ background: {theme.PRIMARY}; border-radius: 2px; }} "
            f"QSlider::handle:horizontal {{ background: {theme.TEXT_PRIMARY}; width: 10px; margin: -3px 0; border-radius: 5px; }} "
            f"QSlider::handle:horizontal:hover {{ background: {theme.PRIMARY}; width: 12px; margin: -4px 0; border-radius: 6px; }}"
        )
        self.scrubber.sliderPressed.connect(self._on_slider_pressed)
        self.scrubber.sliderReleased.connect(self._on_slider_released)
        scrub_row.addWidget(self.scrubber, 1)

        self.dur_label = QLabel("0:00")
        self.dur_label.setFixedWidth(36)
        self.dur_label.setStyleSheet(
            f"color: {theme.TEXT_MUTED}; font-size: {theme.FONT_SIZE_XS}px;"
        )
        self.dur_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        scrub_row.addWidget(self.dur_label)

        center_layout.addLayout(scrub_row)
        main_layout.addWidget(center_box, 1)

        # ── Right Zone: Lyrics, Queue, Volume (min 220px) ───────────────────
        right_box = QWidget()
        right_layout = QHBoxLayout(right_box)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(12)
        right_layout.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        # Lyrics toggle button
        self.btn_lyrics = QPushButton()
        self.btn_lyrics.setFixedSize(32, 32)
        self.btn_lyrics.setIcon(make_icon("mic", theme.TEXT_MUTED, 18))
        self.btn_lyrics.setToolTip("Time-Synced Lyrics")
        self.btn_lyrics.setStyleSheet("background: transparent; border: none;")
        self.btn_lyrics.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_lyrics.clicked.connect(self._toggle_lyrics)
        right_layout.addWidget(self.btn_lyrics)

        # Queue toggle button
        self.btn_queue = QPushButton()
        self.btn_queue.setFixedSize(32, 32)
        self.btn_queue.setIcon(make_icon("queue", theme.TEXT_MUTED, 18))
        self.btn_queue.setToolTip("Playback Queue")
        self.btn_queue.setStyleSheet("background: transparent; border: none;")
        self.btn_queue.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_queue.clicked.connect(self._toggle_queue)
        right_layout.addWidget(self.btn_queue)

        # Volume icon
        self.vol_icon_label = QLabel()
        self.vol_icon_label.setFixedSize(20, 20)
        self.vol_icon_label.setPixmap(make_icon("volume-2", theme.TEXT_MUTED, 18).pixmap(18, 18))
        right_layout.addWidget(self.vol_icon_label)

        # Volume slider
        self.vol_slider = QSlider(Qt.Orientation.Horizontal)
        self.vol_slider.setRange(0, 100)
        self.vol_slider.setValue(int(self._engine.volume * 100))
        self.vol_slider.setFixedWidth(90)
        self.vol_slider.setCursor(Qt.CursorShape.PointingHandCursor)
        self.vol_slider.setStyleSheet(
            f"QSlider::groove:horizontal {{ height: 4px; background: {theme.BORDER}; border-radius: 2px; }} "
            f"QSlider::sub-page:horizontal {{ background: {theme.TEXT_PRIMARY}; border-radius: 2px; }} "
            f"QSlider::handle:horizontal {{ background: {theme.TEXT_PRIMARY}; width: 10px; margin: -3px 0; border-radius: 5px; }} "
            f"QSlider::handle:horizontal:hover {{ background: {theme.PRIMARY}; }}"
        )
        self.vol_slider.valueChanged.connect(self._on_volume_changed)
        right_layout.addWidget(self.vol_slider)

        right_box.setMinimumWidth(220)
        right_box.setMaximumWidth(280)
        main_layout.addWidget(right_box, 0)

        # Wire AudioEngine signals
        self._engine.track_changed.connect(self._on_track_changed)
        self._engine.playback_state_changed.connect(self._on_playback_state_changed)
        self._engine.position_changed.connect(self._on_position_changed)
        self._engine.duration_changed.connect(self._on_duration_changed)

    def _toggle_like(self) -> None:
        self._is_liked = not self._is_liked
        color = theme.PRIMARY if self._is_liked else theme.TEXT_MUTED
        self.btn_heart.setIcon(make_icon("heart", color, 18))

    def _toggle_shuffle(self) -> None:
        shuffled = self._engine.toggle_shuffle()
        color = theme.PRIMARY if shuffled else theme.TEXT_MUTED
        self.btn_shuffle.setIcon(make_icon("shuffle", color, 16))

    def _toggle_repeat(self) -> None:
        repeated = self._engine.toggle_repeat()
        color = theme.PRIMARY if repeated else theme.TEXT_MUTED
        self.btn_repeat.setIcon(make_icon("repeat", color, 16))

    def _toggle_lyrics(self) -> None:
        self._lyrics_active = not self._lyrics_active
        color = theme.PRIMARY if self._lyrics_active else theme.TEXT_MUTED
        self.btn_lyrics.setIcon(make_icon("mic", color, 18))
        self.lyrics_toggled.emit(self._lyrics_active)

    def _toggle_queue(self) -> None:
        self._queue_active = not self._queue_active
        color = theme.PRIMARY if self._queue_active else theme.TEXT_MUTED
        self.btn_queue.setIcon(make_icon("queue", color, 18))
        self.queue_toggled.emit(self._queue_active)

    def _on_slider_pressed(self) -> None:
        self._slider_dragging = True

    def _on_slider_released(self) -> None:
        self._slider_dragging = False
        val = self.scrubber.value()
        dur = self._engine.duration_ms
        if dur > 0:
            target_ms = int((val / 1000.0) * dur)
            self._engine.seek(target_ms)

    def _on_volume_changed(self, val: int) -> None:
        self._engine.set_volume(val / 100.0)
        icon_name = "volume-x" if val == 0 else "volume-2"
        self.vol_icon_label.setPixmap(make_icon(icon_name, theme.TEXT_MUTED, 18).pixmap(18, 18))

    def _on_track_changed(self, track: Track | None) -> None:
        if not track:
            self.title_label.setText("No track playing")
            self.artist_label.setText("EntertainX Music")
            self.pos_label.setText("0:00")
            self.dur_label.setText("0:00")
            self.scrubber.setValue(0)
            self.cover_label.clear()
            return

        self.title_label.setText(track.title)
        self.artist_label.setText(f"{track.artist} • {track.quality}")
        self.dur_label.setText(track.duration_formatted)

        if track.artwork_url and self._store:
            self._store.request(track.artwork_url, 96, self._on_cover_loaded, owner=self)
        else:
            self.cover_label.setPixmap(make_icon("music", theme.TEXT_MUTED, 24).pixmap(24, 24))

    def _on_cover_loaded(self, pixmap: QPixmap | None) -> None:
        if pixmap and not pixmap.isNull():
            scaled = pixmap.scaled(
                48,
                48,
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.cover_label.setPixmap(scaled)

    def _on_playback_state_changed(self, is_playing: bool) -> None:
        icon_name = "pause" if is_playing else "play"
        self.btn_play.setIcon(make_icon(icon_name, theme.TEXT_ON_ACCENT, 20))

    def _on_position_changed(self, pos: int) -> None:
        self.pos_label.setText(format_time(pos))
        if not self._slider_dragging:
            dur = self._engine.duration_ms
            if dur > 0:
                fraction = min(1.0, max(0.0, pos / dur))
                self.scrubber.setValue(int(fraction * 1000))

    def _on_duration_changed(self, dur: int) -> None:
        if dur > 0:
            self.dur_label.setText(format_time(dur))
