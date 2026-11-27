"""In-app movie and TV player.

The picture is a ``QGraphicsVideoItem`` in a ``QGraphicsScene`` driven by Qt
Multimedia, which uses the system's FFmpeg backend and can decode the H.264/AAC
streams the providers serve. (Qt WebEngine's bundled Chromium has no H.264/AAC
support, so an HTML ``<video>`` cannot play them.) The scene keeps the video
surface behind ordinary widgets, so the controls always stack above it.

Streams are resolved by :mod:`api.streaming` and fetched through the loopback
proxy in :mod:`api.stream_proxy`, which adds the provider headers and keeps a
token extension FFmpeg accepts for each resource.

Everything stays inside the main window: this widget is an overlay, and its
``closed`` signal returns the shell to the browse view.
"""

from __future__ import annotations

import logging
from typing import Any

from PySide6.QtCore import QEvent, QSize, QSizeF, Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QColor, QPainter
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtMultimediaWidgets import QGraphicsVideoItem
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFrame,
    QGraphicsScene,
    QGraphicsView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from api import streaming
from api.movies import MediaDetails, MediaItem, TmdbClient
from api.stream_proxy import get_proxy
from api.tasks import run_async
from ui.components.icons import make_icon

log = logging.getLogger(__name__)

#: A provider API that has not answered in this long is treated as dead.
FAIL_TIMEOUT_MS = 8000
#: A resolved source gets longer: VixSrc has to fetch its master, renditions
#: and first segments before FFmpeg reports a picture.
START_TIMEOUT_MS = 15000
HIDE_DELAY_MS = 3000
SEEK_SECONDS = 10
TEXT = "#F2EFE9"
MUTED = "#B8B2B5"
ACCENT = "#E50914"


# ── Provider resolution ─────────────────────────────────────────────────────
def _resolve_sources(
    server_id: str,
    media_type: str,
    tmdb_id: int,
    season: int | None,
    episode: int | None,
) -> list[dict[str, str]]:
    """Resolve a server and register every candidate with the local proxy."""
    proxy = get_proxy()
    sources = streaming.resolve(server_id, media_type, tmdb_id, season, episode)
    candidates: list[dict[str, str]] = []
    for source in sources:
        suffix = ".m3u8" if source.kind == "hls" else ".mp4"
        candidates.append(
            {
                "url": proxy.register(source.url, source.header_dict()) + suffix,
                "label": source.label,
                "language": source.language,
                "kind": source.kind,
            }
        )
    return candidates


def _fmt(ms: float) -> str:
    total = max(0, int(ms // 1000))
    hours, rest = divmod(total, 3600)
    minutes, seconds = divmod(rest, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes}:{seconds:02d}"


def _track_label(track: Any) -> str:
    for attribute in ("language", "description", "title"):
        value = getattr(track, attribute, None)
        if value:
            return str(value)
    try:
        from PySide6.QtMultimedia import QMediaMetaData

        language = track.stringValue(QMediaMetaData.Key.Language)
        if language:
            return language
    except Exception:  # noqa: BLE001 - track metadata is best effort
        pass
    return "Track"


_QSS = """
QWidget#PlaybackPage { background: #050506; }
QWidget#PlayerTop, QWidget#PlayerCard, QWidget#PlayerBottom { background: transparent; }
QWidget#PlayerPanel {
    background: rgba(12, 12, 16, 0.95);
    border: 1px solid rgba(255, 255, 255, 0.14);
    border-radius: 16px;
}
QWidget#PlayerError {
    background: rgba(8, 8, 10, 0.97);
    border: 1px solid rgba(255, 255, 255, 0.14);
    border-radius: 18px;
}
QWidget#PlayerLoading {
    background: rgba(8, 8, 10, 0.86);
    border: 1px solid rgba(255, 255, 255, 0.10);
    border-radius: 14px;
}
QLabel { color: #D6D3CC; }
QLabel#PlayerEyebrow {
    color: #B8B2B5;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 2px;
}
QLabel#PlayerTitle {
    color: #F2EFE9;
    font-size: 34px;
    font-weight: 800;
}
QLabel#PlayerChips { color: #F2EFE9; font-size: 13px; font-weight: 600; }
QLabel#PlayerSynopsis { color: #D6D3CC; font-size: 14px; }
QLabel#PlayerTopTitle { color: #B8B2B5; font-size: 13px; }
QLabel#PlayerTime { color: #D6D3CC; font-size: 12px; }
QLabel#PlayerToast {
    background: rgba(0, 0, 0, 0.82);
    border: 1px solid rgba(255, 255, 255, 0.18);
    border-radius: 16px;
    color: #F2EFE9;
    font-size: 12px;
    font-weight: 600;
    padding: 6px 14px;
}
QLabel#PlayerSection { color: #B8B2B5; font-size: 11px; font-weight: 700; letter-spacing: 1px; }
QLabel#PlayerErrorTitle { color: #F2EFE9; font-size: 22px; font-weight: 800; }
QPushButton#PlayerIcon {
    background: rgba(0, 0, 0, 0.45);
    border: 1px solid rgba(255, 255, 255, 0.18);
    border-radius: 20px;
}
QPushButton#PlayerIcon:hover { background: rgba(255, 255, 255, 0.16); }
QPushButton#PlayerIcon:focus { border-color: #F2EFE9; }
QPushButton#PlayerIcon:disabled { border-color: rgba(255, 255, 255, 0.06); }
QPushButton#PlayerIcon[active="true"] { color: #E50914; border-color: #E50914; }
QPushButton#PlayerRetry {
    background: #E50914;
    color: #FFFFFF;
    border: 0;
    border-radius: 8px;
    padding: 10px 26px;
    font-weight: 700;
}
QPushButton#PlayerRetry:hover { background: #F6121D; }
QPushButton#PlayerRetry:focus { border: 2px solid #F2EFE9; }
QComboBox {
    background: rgba(0, 0, 0, 0.55);
    border: 1px solid rgba(255, 255, 255, 0.20);
    border-radius: 8px;
    color: #F2EFE9;
    padding: 7px 10px;
    min-height: 20px;
}
QComboBox:focus { border-color: #F2EFE9; }
QComboBox QAbstractItemView {
    background: #111116;
    color: #F2EFE9;
    selection-background-color: #E50914;
    border: 1px solid rgba(255, 255, 255, 0.18);
}
QSlider#PlayerProgress::groove:horizontal {
    height: 4px;
    background: rgba(255, 255, 255, 0.18);
    border-radius: 2px;
}
QSlider#PlayerProgress::sub-page:horizontal { background: #E50914; border-radius: 2px; }
QSlider#PlayerProgress::handle:horizontal {
    width: 12px; height: 12px; margin: -4px 0;
    border-radius: 6px; background: #E50914;
}
QSlider#PlayerVolume::groove:horizontal {
    height: 3px;
    background: rgba(255, 255, 255, 0.28);
    border-radius: 2px;
}
QSlider#PlayerVolume::sub-page:horizontal { background: #F2EFE9; border-radius: 2px; }
QSlider#PlayerVolume::handle:horizontal {
    width: 10px; height: 10px; margin: -4px 0;
    border-radius: 5px; background: #F2EFE9;
}
QListWidget {
    background: transparent;
    border: 0;
    color: #D6D3CC;
    outline: 0;
}
QListWidget::item { padding: 8px 6px; border-radius: 8px; }
QListWidget::item:hover { background: rgba(255, 255, 255, 0.08); }
QListWidget::item:selected { background: rgba(229, 9, 20, 0.22); color: #F2EFE9; }
"""


class PlaybackPage(QWidget):
    """Full-window player surface; created once and reused for every title."""

    closed = Signal()

    def __init__(
        self,
        parent: QWidget | None = None,
        provider: TmdbClient | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("PlaybackPage")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(_QSS)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMouseTracking(True)

        self._provider = provider if provider is not None else TmdbClient()
        self._item: MediaItem | None = None
        self._details: MediaDetails | None = None
        self._servers: list[dict[str, str]] = []
        self._server_index = 0
        self._candidates: list[dict[str, str]] = []
        self._candidate_index = 0
        self._phase = "idle"
        self._active = False
        self._request_id = 0
        self._season = 1
        self._episode = 1
        self._episode_cache: dict[int, list[Any]] = {}
        self._seeking = False
        self._syncing = False
        self._cc_index = 0
        self._subtitle_tracks: list[Any] = []
        self._was_maximized = False

        self._player = QMediaPlayer(self)
        self._audio = QAudioOutput(self)
        self._player.setAudioOutput(self._audio)
        self._player.errorOccurred.connect(self._on_media_error)
        self._player.mediaStatusChanged.connect(self._on_media_status)
        self._player.playbackStateChanged.connect(self._on_playback_state)
        self._player.positionChanged.connect(self._on_position)
        self._player.durationChanged.connect(self._on_duration)
        self._player.tracksChanged.connect(self._refresh_subtitles)

        self._build_ui()

        self._resolve_timer = QTimer(self)
        self._resolve_timer.setSingleShot(True)
        self._resolve_timer.timeout.connect(self._on_resolve_timeout)
        self._candidate_timer = QTimer(self)
        self._candidate_timer.setSingleShot(True)
        self._candidate_timer.timeout.connect(self._on_candidate_timeout)
        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self._hide_chrome)
        self._toast_timer = QTimer(self)
        self._toast_timer.setSingleShot(True)
        self._toast_timer.timeout.connect(self._toast.hide)

        self._sync_play_icon()
        self._update_volume_ui()

    # ── Public API ──────────────────────────────────────────────────────────
    @property
    def player(self) -> QMediaPlayer:
        return self._player

    def open(self, item: MediaItem, details: MediaDetails) -> None:
        self._item = item
        self._details = details
        self._season = 1
        self._episode = 1
        self._episode_cache.clear()
        self._servers = streaming.servers_payload()
        self._request_id += 1
        self._active = True
        self._phase = "idle"
        self._error.hide()
        self._hide_loading()
        self._panel.hide()
        self._toast.hide()
        self._card.show()
        self._populate_servers()
        self._populate_seasons()
        self._render_metadata()
        self._update_top_title()

        self.show()
        self.raise_()
        self.setFocus()
        app = QApplication.instance()
        if app is not None:
            app.installEventFilter(self)
        self.start_server(0, announce=False)

    def close_player(self) -> None:
        if not self._active:
            return
        self._active = False
        self._request_id += 1
        self._phase = "idle"
        self._stop_timers()
        self._player.stop()
        self._player.setSource(QUrl())
        self._hide_timer.stop()
        self._error.hide()
        self._hide_loading()
        self._panel.hide()
        self._toast.hide()
        app = QApplication.instance()
        if app is not None:
            app.removeEventFilter(self)
        self.unsetCursor()
        self._view.unsetCursor()
        self.hide()
        self.closed.emit()

    # ── UI construction ─────────────────────────────────────────────────────
    def _icon_button(self, icon: str, tooltip: str, parent: QWidget | None = None) -> QPushButton:
        button = QPushButton(parent if parent is not None else self)
        button.setObjectName("PlayerIcon")
        button.setIcon(make_icon(icon, TEXT, 18))
        button.setIconSize(QSize(20, 20))
        button.setFixedSize(40, 40)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setToolTip(tooltip)
        button.setAccessibleName(tooltip)
        return button

    def _build_ui(self) -> None:
        # The video lives in a QGraphicsScene so the controls can be normal
        # widgets stacked above it (a QVideoWidget can be a native surface).
        self._scene = QGraphicsScene(self)
        self._video_item = QGraphicsVideoItem()
        self._video_item.setAspectRatioMode(Qt.AspectRatioMode.KeepAspectRatio)
        self._scene.addItem(self._video_item)
        self._view = QGraphicsView(self._scene, self)
        self._view.setFrameShape(QFrame.Shape.NoFrame)
        self._view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._view.setBackgroundBrush(QColor("#050506"))
        self._view.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        self._view.setMouseTracking(True)
        self._view.installEventFilter(self)
        self._player.setVideoOutput(self._video_item)

        # Top bar: back + now-playing title.
        self._top = QWidget(self)
        top_row = QHBoxLayout(self._top)
        top_row.setContentsMargins(20, 12, 20, 12)
        top_row.setSpacing(12)
        self._back = self._icon_button("back", "Back to browse", self._top)
        self._back.clicked.connect(self.close_player)
        top_row.addWidget(self._back)
        self._top_title = QLabel("", self._top)
        self._top_title.setObjectName("PlayerTopTitle")
        top_row.addWidget(self._top_title)
        top_row.addStretch(1)

        # Title card (hidden while the picture is playing).
        self._card = QWidget(self)
        card = QVBoxLayout(self._card)
        card.setContentsMargins(28, 0, 28, 0)
        card.setSpacing(10)
        eyebrow = QLabel("YOU'RE WATCHING", self._card)
        eyebrow.setObjectName("PlayerEyebrow")
        self._title = QLabel("", self._card)
        self._title.setObjectName("PlayerTitle")
        self._title.setWordWrap(True)
        self._chips = QLabel("", self._card)
        self._chips.setObjectName("PlayerChips")
        self._synopsis = QLabel("", self._card)
        self._synopsis.setObjectName("PlayerSynopsis")
        self._synopsis.setWordWrap(True)
        self._synopsis.setMaximumHeight(96)
        card.addWidget(eyebrow)
        card.addWidget(self._title)
        card.addWidget(self._chips)
        card.addWidget(self._synopsis)
        card.addStretch(1)

        # Bottom controls.
        self._bottom = QWidget(self)
        bottom = QVBoxLayout(self._bottom)
        bottom.setContentsMargins(24, 0, 24, 14)
        bottom.setSpacing(6)
        self._progress = QSlider(Qt.Orientation.Horizontal, self._bottom)
        self._progress.setObjectName("PlayerProgress")
        self._progress.setRange(0, 1000)
        self._progress.setAccessibleName("Seek")
        self._progress.sliderPressed.connect(self._on_seek_start)
        self._progress.sliderReleased.connect(self._on_seek_end)
        self._progress.sliderMoved.connect(self._on_seek_move)
        bottom.addWidget(self._progress)

        row = QHBoxLayout()
        row.setSpacing(6)
        self._play = self._icon_button("play", "Play", self._bottom)
        self._play.clicked.connect(self.toggle_play)
        self._rew = self._icon_button("rewind", "Rewind 10 seconds", self._bottom)
        self._rew.clicked.connect(lambda: self.seek_by(-SEEK_SECONDS))
        self._fwd = self._icon_button("forward", "Forward 10 seconds", self._bottom)
        self._fwd.clicked.connect(lambda: self.seek_by(SEEK_SECONDS))
        self._mute = self._icon_button("volume-2", "Mute", self._bottom)
        self._mute.clicked.connect(self.toggle_mute)
        self._volume = QSlider(Qt.Orientation.Horizontal, self._bottom)
        self._volume.setObjectName("PlayerVolume")
        self._volume.setRange(0, 100)
        self._volume.setValue(100)
        self._volume.setFixedWidth(88)
        self._volume.setAccessibleName("Volume")
        self._volume.valueChanged.connect(self._set_volume)
        self._time = QLabel("0:00 / 0:00", self._bottom)
        self._time.setObjectName("PlayerTime")
        for widget in (self._play, self._rew, self._fwd, self._mute, self._volume, self._time):
            row.addWidget(widget)
        row.addStretch(1)
        self._cc = self._icon_button("captions", "Subtitles", self._bottom)
        self._cc.clicked.connect(self.cycle_subtitles)
        self._panel_button = self._icon_button("episodes", "Servers and episodes", self._bottom)
        self._panel_button.clicked.connect(self.toggle_panel)
        self._fullscreen = self._icon_button("maximize", "Fullscreen", self._bottom)
        self._fullscreen.clicked.connect(self.toggle_fullscreen)
        for widget in (self._cc, self._panel_button, self._fullscreen):
            row.addWidget(widget)
        bottom.addLayout(row)

        # Right-side servers / episodes panel.
        self._panel = QWidget(self)
        self._panel.setObjectName("PlayerPanel")
        self._panel.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        panel = QVBoxLayout(self._panel)
        panel.setContentsMargins(16, 16, 16, 16)
        panel.setSpacing(10)
        panel_head = QHBoxLayout()
        heading = QLabel("Servers & episodes", self._panel)
        heading.setObjectName("PlayerSection")
        panel_head.addWidget(heading)
        panel_head.addStretch(1)
        close = self._icon_button("close", "Close panel", self._panel)
        close.setFixedSize(30, 30)
        close.clicked.connect(self.toggle_panel)
        panel_head.addWidget(close)
        panel.addLayout(panel_head)

        server_label = QLabel("SERVER", self._panel)
        server_label.setObjectName("PlayerSection")
        panel.addWidget(server_label)
        self._panel_server = QComboBox(self._panel)
        self._panel_server.setAccessibleName("Streaming server")
        self._panel_server.currentIndexChanged.connect(self._on_server_picked)
        panel.addWidget(self._panel_server)

        self._season_label = QLabel("SEASON", self._panel)
        self._season_label.setObjectName("PlayerSection")
        panel.addWidget(self._season_label)
        self._season_combo = QComboBox(self._panel)
        self._season_combo.setAccessibleName("Season")
        self._season_combo.currentIndexChanged.connect(self._on_season_picked)
        panel.addWidget(self._season_combo)

        self._episodes = QListWidget(self._panel)
        self._episodes.setAccessibleName("Episodes")
        self._episodes.itemClicked.connect(self._on_episode_picked)
        panel.addWidget(self._episodes, 1)

        # Loading + error states.
        self._loading = QWidget(self)
        self._loading.setObjectName("PlayerLoading")
        self._loading.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        loading = QVBoxLayout(self._loading)
        loading.setContentsMargins(24, 20, 24, 20)
        self._loading_label = QLabel("Finding a stream\u2026", self._loading)
        self._loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        loading.addWidget(self._loading_label)
        self._loading.hide()

        self._error = QWidget(self)
        self._error.setObjectName("PlayerError")
        self._error.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        error = QVBoxLayout(self._error)
        error.setContentsMargins(28, 26, 28, 26)
        error.setSpacing(12)
        error_title = QLabel("No video source found for this title.", self._error)
        error_title.setObjectName("PlayerErrorTitle")
        error_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        error_title.setWordWrap(True)
        error_text = QLabel("Try another server or check back later.", self._error)
        error_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        error.addWidget(error_title)
        error.addWidget(error_text)
        actions = QHBoxLayout()
        actions.setSpacing(10)
        self._error_server = QComboBox(self._error)
        self._error_server.setAccessibleName("Choose a streaming server")
        self._error_server.currentIndexChanged.connect(self._on_server_picked)
        actions.addWidget(self._error_server, 1)
        self._retry = QPushButton("Retry", self._error)
        self._retry.setObjectName("PlayerRetry")
        self._retry.setCursor(Qt.CursorShape.PointingHandCursor)
        self._retry.clicked.connect(
            lambda: self.start_server(self._error_server.currentIndex(), announce=False)
        )
        actions.addWidget(self._retry)
        error.addLayout(actions)
        self._error.hide()

        self._toast = QLabel("", self)
        self._toast.setObjectName("PlayerToast")
        self._toast.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._toast.hide()

        for widget in (self._top, self._card, self._bottom, self._panel):
            widget.installEventFilter(self)
            widget.setMouseTracking(True)
        self._raise_layers()

    def _raise_layers(self) -> None:
        self._view.lower()
        for widget in (self._top, self._card, self._bottom, self._panel, self._loading, self._error):
            widget.raise_()
        self._toast.raise_()

    # ── Layout ──────────────────────────────────────────────────────────────
    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        width, height = self.width(), self.height()
        self._view.setGeometry(self.rect())
        self._scene.setSceneRect(0, 0, width, height)
        self._video_item.setSize(QSizeF(width, height))
        self._video_item.setPos(0, 0)
        self._top.setGeometry(0, 0, width, 64)
        card_width = min(620, max(340, int(width * 0.52)))
        self._card.setGeometry(28, max(84, height // 2 - 170), card_width, 330)
        self._bottom.setGeometry(0, height - 104, width, 104)
        panel_width = min(380, max(300, int(width * 0.30)))
        self._panel.setGeometry(
            width - panel_width - 16, 76, panel_width, max(240, height - 196)
        )
        self._loading.setGeometry((width - 340) // 2, (height - 110) // 2, 340, 110)
        self._error.setGeometry((width - 520) // 2, (height - 250) // 2, 520, 250)
        self._toast.setGeometry((width - 320) // 2, 76, 320, 34)

    # ── Metadata ────────────────────────────────────────────────────────────
    def _render_metadata(self) -> None:
        item = self._item
        details = self._details
        if item is None or details is None:
            return
        self._title.setText(item.title)
        chips = [value for value in (details.certification, details.runtime_text) if value]
        if item.rating:
            chips.append(f"\u2605 {item.rating:.1f}")
        self._chips.setText("   \u00b7   ".join(chips))
        self._synopsis.setText(
            item.overview or "No synopsis is available for this title yet."
        )

    def _update_top_title(self) -> None:
        item = self._item
        if item is None:
            return
        text = item.title
        if item.year:
            text += f"  \u00b7  {item.year}"
        if item.media_type == "tv":
            text += f"  \u00b7  S{self._season} E{self._episode}"
        self._top_title.setText(text)

    # ── Servers ─────────────────────────────────────────────────────────────
    def _populate_servers(self) -> None:
        self._syncing = True
        try:
            for combo in (self._panel_server, self._error_server):
                combo.clear()
                for server in self._servers:
                    label = server.get("name", "Server")
                    if server.get("quality"):
                        label += f" \u00b7 {server['quality']}"
                    combo.addItem(label, server.get("id"))
        finally:
            self._syncing = False
        self._sync_server_selection()

    def _sync_server_selection(self) -> None:
        self._syncing = True
        try:
            self._panel_server.setCurrentIndex(self._server_index)
            self._error_server.setCurrentIndex(self._server_index)
        finally:
            self._syncing = False

    def _on_server_picked(self, index: int) -> None:
        if self._syncing or not self._active or index < 0:
            return
        self.start_server(index, announce=False)

    def start_server(self, index: int, announce: bool = True) -> None:
        if not self._active:
            return
        if index < 0 or index >= len(self._servers):
            self._fail_all()
            return
        self._request_id += 1
        request_id = self._request_id
        self._server_index = index
        self._candidates = []
        self._candidate_index = 0
        self._phase = "resolving"
        self._sync_server_selection()
        self._stop_timers()
        self._player.stop()
        self._player.setSource(QUrl())
        server = self._servers[index]
        self._show_loading(f"Connecting to {server.get('name', 'server')}\u2026")
        if announce:
            self.toast(f"Switching to {server.get('name', 'server')}\u2026")
        self._resolve_timer.start(FAIL_TIMEOUT_MS)

        item = self._item
        if item is None:
            self._fail_all()
            return
        is_tv = item.media_type == "tv"
        run_async(
            _resolve_sources,
            str(server.get("id")),
            item.media_type,
            item.id,
            self._season if is_tv else None,
            self._episode if is_tv else None,
            on_done=lambda candidates: self._deliver_sources(
                request_id, index, candidates
            ),
            on_error=lambda error: self._resolve_failed(request_id, index, error),
            owner=self,
        )

    # ── Provider resolution ─────────────────────────────────────────────────
    def _stop_timers(self) -> None:
        self._resolve_timer.stop()
        self._candidate_timer.stop()

    def _deliver_sources(
        self, request_id: int, server_index: int, candidates: list[dict[str, str]]
    ) -> None:
        if request_id != self._request_id or not self._active:
            return
        if self._phase != "resolving":
            return
        self._resolve_timer.stop()
        if server_index != self._server_index:
            return
        if not candidates:
            self._next_server()
            return
        self._candidates = candidates
        self._try_candidate(0)

    def _resolve_failed(self, request_id: int, server_index: int, error: Exception) -> None:
        log.info("Server %s could not resolve a stream: %s", server_index, error)
        if request_id != self._request_id or not self._active:
            return
        if self._phase == "resolving" and server_index == self._server_index:
            self._next_server()

    def _on_resolve_timeout(self) -> None:
        if self._phase != "resolving":
            return
        log.info("Server %s timed out while resolving", self._server_index)
        self._next_server()

    def _try_candidate(self, index: int) -> None:
        if index >= len(self._candidates):
            self._next_server()
            return
        self._candidate_index = index
        self._phase = "buffering"
        candidate = self._candidates[index]
        log.info(
            "Trying %s (%s)", candidate.get("label", "source"), candidate.get("kind", "hls")
        )
        self._show_loading("Starting stream\u2026")
        self._player.setSource(QUrl(str(candidate.get("url", ""))))
        self._player.play()
        self._candidate_timer.start(START_TIMEOUT_MS)

    def _on_candidate_timeout(self) -> None:
        if self._phase == "buffering":
            self._candidate_failed("start-up timed out")

    def _candidate_failed(self, reason: str) -> None:
        if self._phase not in ("buffering", "playing"):
            return
        log.info("Source failed: %s", reason)
        self._phase = "switching"
        self._stop_timers()
        self._player.stop()
        self._player.setSource(QUrl())
        next_candidate = self._candidate_index + 1
        if next_candidate < len(self._candidates):
            self._try_candidate(next_candidate)
        else:
            self._next_server()

    def _next_server(self) -> None:
        self._stop_timers()
        next_index = self._server_index + 1
        if next_index < len(self._servers):
            self.start_server(next_index, announce=True)
        else:
            self._fail_all()

    def _fail_all(self) -> None:
        log.info("Every server failed for %s", self._item.title if self._item else "title")
        self._phase = "error"
        self._stop_timers()
        self._player.stop()
        self._player.setSource(QUrl())
        self._hide_loading()
        self._card.hide()
        self._error.show()
        self._error.raise_()
        self._error_server.setCurrentIndex(self._server_index)
        self._retry.setFocus()

    # ── Media player signals ────────────────────────────────────────────────
    def _on_media_error(self, error, message: str) -> None:
        if error == QMediaPlayer.Error.NoError:
            return
        log.info("QMediaPlayer error %s: %s", error, message)
        self._candidate_failed(str(message) or "player error")

    def _on_media_status(self, status) -> None:
        if status in (
            QMediaPlayer.MediaStatus.LoadedMedia,
            QMediaPlayer.MediaStatus.BufferedMedia,
        ):
            if self._phase == "buffering":
                self._mark_playing()
        elif status == QMediaPlayer.MediaStatus.InvalidMedia:
            self._candidate_failed("invalid media")

    def _on_playback_state(self, state) -> None:
        if state == QMediaPlayer.PlaybackState.PlayingState and self._phase == "buffering":
            self._mark_playing()
        if state == QMediaPlayer.PlaybackState.PausedState:
            self._wake()
        self._sync_play_icon()

    def _mark_playing(self) -> None:
        self._phase = "playing"
        self._candidate_timer.stop()
        self._hide_loading()
        self._error.hide()
        self._card.hide()
        self._sync_play_icon()
        self._refresh_subtitles()
        self._wake()

    def _sync_play_icon(self) -> None:
        playing = self._player.playbackState() == QMediaPlayer.PlaybackState.PlayingState
        self._play.setIcon(make_icon("pause" if playing else "play", TEXT, 18))
        label = "Pause" if playing else "Play"
        self._play.setToolTip(label)
        self._play.setAccessibleName(label)

    # ── Playback controls ───────────────────────────────────────────────────
    def toggle_play(self) -> None:
        if self._phase == "error":
            self.start_server(self._error_server.currentIndex(), announce=False)
            return
        if self._player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self._player.pause()
        else:
            self._player.play()
        self._wake()

    def seek_by(self, seconds: int) -> None:
        duration = self._player.duration()
        if duration <= 0:
            return
        target = max(0, min(duration, self._player.position() + seconds * 1000))
        self._player.setPosition(target)
        self._wake()

    def _on_seek_start(self) -> None:
        self._seeking = True

    def _on_seek_move(self, value: int) -> None:
        duration = self._player.duration()
        if duration > 0:
            self._time.setText(
                f"{_fmt(duration * value / 1000)} / {_fmt(duration)}"
            )

    def _on_seek_end(self) -> None:
        duration = self._player.duration()
        if duration > 0:
            self._player.setPosition(int(duration * self._progress.value() / 1000))
        self._seeking = False
        self._wake()

    def _on_position(self, position: int) -> None:
        duration = self._player.duration()
        if not self._seeking:
            if duration > 0:
                self._progress.setValue(int(position / duration * 1000))
            self._time.setText(f"{_fmt(position)} / {_fmt(duration) if duration > 0 else '0:00'}")

    def _on_duration(self, duration: int) -> None:
        self._time.setText(f"{_fmt(self._player.position())} / {_fmt(duration)}")

    def _set_volume(self, value: int) -> None:
        self._audio.setVolume(max(0.0, min(1.0, value / 100)))
        self._audio.setMuted(value == 0)
        self._update_volume_ui()

    def toggle_mute(self) -> None:
        muted = not self._audio.isMuted()
        self._audio.setMuted(muted)
        if not muted and self._volume.value() == 0:
            self._volume.setValue(80)
        self._update_volume_ui()
        self._wake()

    def _update_volume_ui(self) -> None:
        muted = self._audio.isMuted() or self._volume.value() == 0
        self._mute.setIcon(make_icon("volume-x" if muted else "volume-2", TEXT, 18))
        label = "Unmute" if muted else "Mute"
        self._mute.setToolTip(label)
        self._mute.setAccessibleName(label)

    # ── Subtitles ───────────────────────────────────────────────────────────
    def _refresh_subtitles(self) -> None:
        try:
            self._subtitle_tracks = list(self._player.subtitleTracks() or [])
        except Exception:  # noqa: BLE001 - backend may not expose tracks
            self._subtitle_tracks = []
        self._cc_index = 0
        self._cc.setEnabled(bool(self._subtitle_tracks))
        self._cc.setToolTip(
            "Subtitles" if self._subtitle_tracks else "No subtitles available"
        )

    def cycle_subtitles(self) -> None:
        if not self._subtitle_tracks:
            self.toast("No subtitles available for this source.")
            return
        self._cc_index = (self._cc_index + 1) % (len(self._subtitle_tracks) + 1)
        if self._cc_index == 0:
            self._player.setActiveSubtitleTrack(-1)
            self.toast("Subtitles off")
        else:
            self._player.setActiveSubtitleTrack(self._cc_index - 1)
            self.toast(f"Subtitles: {_track_label(self._subtitle_tracks[self._cc_index - 1])}")
        self._cc.setProperty("active", self._cc_index > 0)
        self._cc.style().unpolish(self._cc)
        self._cc.style().polish(self._cc)

    # ── Episodes ────────────────────────────────────────────────────────────
    def _populate_seasons(self) -> None:
        item = self._item
        details = self._details
        seasons = (
            [season for season in details.seasons if season.number > 0]
            if details is not None
            else []
        )
        is_tv = item is not None and item.media_type == "tv"
        self._syncing = True
        try:
            self._season_combo.clear()
            for season in seasons:
                self._season_combo.addItem(
                    season.name or f"Season {season.number}", season.number
                )
        finally:
            self._syncing = False
        self._season_label.setVisible(is_tv and bool(seasons))
        self._season_combo.setVisible(is_tv and bool(seasons))
        self._episodes.setVisible(is_tv)
        if is_tv:
            self._request_episodes()

    def _on_season_picked(self, index: int) -> None:
        if self._syncing or index < 0:
            return
        season = self._season_combo.itemData(index)
        if not isinstance(season, int):
            return
        self._season = season
        self._episode = 1
        self._update_top_title()
        self._request_episodes()

    def _request_episodes(self) -> None:
        item = self._item
        if item is None or item.media_type != "tv":
            return
        season = self._season
        cached = self._episode_cache.get(season)
        if cached is not None:
            self._render_episodes(season)
            return
        self._episodes.clear()
        placeholder = QListWidgetItem("Loading episodes\u2026")
        placeholder.setFlags(Qt.ItemFlag.NoItemFlags)
        self._episodes.addItem(placeholder)
        run_async(
            self._provider.episodes,
            item.id,
            season,
            on_done=lambda episodes: self._on_episodes(season, episodes),
            on_error=lambda error: self._on_episodes_failed(season, error),
            owner=self,
        )

    def _on_episodes(self, season: int, episodes) -> None:
        self._episode_cache[season] = list(episodes)
        if self._active and season == self._season:
            self._render_episodes(season)

    def _on_episodes_failed(self, season: int, error: Exception) -> None:
        log.info("Episode list unavailable for season %s: %s", season, error)
        self._episode_cache[season] = []
        if self._active and season == self._season:
            self._render_episodes(season)

    def _render_episodes(self, season: int) -> None:
        episodes = self._episode_cache.get(season, [])
        self._episodes.clear()
        if not episodes:
            placeholder = QListWidgetItem("The episode list is unavailable right now.")
            placeholder.setFlags(Qt.ItemFlag.NoItemFlags)
            self._episodes.addItem(placeholder)
            return
        for episode in episodes:
            label = f"E{episode.number:02d}   {episode.name or f'Episode {episode.number}'}"
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, episode.number)
            if episode.runtime:
                item.setToolTip(f"{episode.runtime} min")
            if episode.number == self._episode:
                item.setSelected(True)
            self._episodes.addItem(item)

    def _on_episode_picked(self, item: QListWidgetItem) -> None:
        number = item.data(Qt.ItemDataRole.UserRole)
        if not isinstance(number, int):
            return
        self._episode = number
        self._update_top_title()
        self._render_episodes(self._season)
        self.start_server(self._server_index, announce=False)

    # ── Panels, states and chrome ───────────────────────────────────────────
    def toggle_panel(self) -> None:
        visible = not self._panel.isVisible()
        self._panel.setVisible(visible)
        if visible:
            self._panel.raise_()
            if self._item is not None and self._item.media_type == "tv":
                self._request_episodes()
            self._panel_server.setFocus()
        self._wake()

    def _show_loading(self, message: str) -> None:
        self._loading_label.setText(message)
        self._loading.show()
        self._loading.raise_()
        self._error.hide()
        self._card.hide()

    def _hide_loading(self) -> None:
        self._loading.hide()

    def toast(self, message: str) -> None:
        self._toast.setText(message)
        self._toast.show()
        self._toast.raise_()
        self._toast_timer.start(2600)

    def _wake(self) -> None:
        if not self._active:
            return
        self._top.show()
        self._bottom.show()
        self._card.setVisible(self._phase != "playing" and not self._loading.isVisible())
        self.unsetCursor()
        self._view.unsetCursor()
        self._hide_timer.start(HIDE_DELAY_MS)

    def _hide_chrome(self) -> None:
        if not self._active:
            return
        if self._phase != "playing":
            return
        if self._panel.isVisible() or self._error.isVisible() or self._toast.isVisible():
            self._hide_timer.start(HIDE_DELAY_MS)
            return
        self._top.hide()
        self._bottom.hide()
        self._card.hide()
        self.setCursor(Qt.CursorShape.BlankCursor)
        self._view.setCursor(Qt.CursorShape.BlankCursor)

    # ── Fullscreen and keyboard ─────────────────────────────────────────────
    def toggle_fullscreen(self) -> None:
        window = self.window()
        if window is None:
            return
        if window.isFullScreen():
            if self._was_maximized:
                window.showMaximized()
            else:
                window.showNormal()
        else:
            self._was_maximized = window.isMaximized()
            window.showFullScreen()
        self._sync_fullscreen_icon()
        self._wake()

    def _sync_fullscreen_icon(self) -> None:
        window = self.window()
        full = bool(window and window.isFullScreen())
        self._fullscreen.setIcon(make_icon("minimize" if full else "maximize", TEXT, 18))
        label = "Exit fullscreen" if full else "Fullscreen"
        self._fullscreen.setToolTip(label)
        self._fullscreen.setAccessibleName(label)

    def eventFilter(self, watched, event) -> bool:  # noqa: N802
        if not self._active:
            return False
        kind = event.type()
        if kind == QEvent.Type.MouseMove:
            self._wake()
        elif kind == QEvent.Type.MouseButtonPress and watched is self._view:
            self._wake()
        elif kind == QEvent.Type.MouseButtonDblClick and watched is self._view:
            self.toggle_fullscreen()
            return True
        elif kind == QEvent.Type.KeyPress:
            return self._handle_key(event)
        return False

    def _handle_key(self, event) -> bool:
        key = event.key()
        focus = QApplication.focusWidget()
        interactive = isinstance(focus, (QComboBox, QLineEdit, QSlider))
        if interactive and key in (
            Qt.Key.Key_Left,
            Qt.Key.Key_Right,
            Qt.Key.Key_Up,
            Qt.Key.Key_Down,
            Qt.Key.Key_Escape,
        ):
            return False
        if key in (Qt.Key.Key_Space, Qt.Key.Key_K):
            self.toggle_play()
        elif key == Qt.Key.Key_Left:
            self.seek_by(-SEEK_SECONDS)
        elif key == Qt.Key.Key_Right:
            self.seek_by(SEEK_SECONDS)
        elif key == Qt.Key.Key_Up:
            self._volume.setValue(min(100, self._volume.value() + 5))
        elif key == Qt.Key.Key_Down:
            self._volume.setValue(max(0, self._volume.value() - 5))
        elif key == Qt.Key.Key_F:
            self.toggle_fullscreen()
        elif key == Qt.Key.Key_M:
            self.toggle_mute()
        elif key == Qt.Key.Key_Escape:
            window = self.window()
            if window is not None and window.isFullScreen():
                self.toggle_fullscreen()
            elif self._panel.isVisible():
                self.toggle_panel()
            else:
                self.close_player()
        else:
            return False
        self._wake()
        return True

    def keyPressEvent(self, event) -> None:  # noqa: N802
        if not self._handle_key(event):
            super().keyPressEvent(event)


__all__ = ["PlaybackPage"]
