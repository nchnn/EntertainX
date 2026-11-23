"""The floating card that grows out of a tile on hover (Netflix-style).

The preview is a child of the page, not of the shelf, so it can extend past the
shelf's edges. It is positioned over the hovered tile, scales and fades in from
the tile's centre, displays landscape backdrop art, official logo overlays,
interactive controls, and auto-plays the trailer after a 2.5s countdown.
"""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import (
    QEasingCurve,
    QPoint,
    QPointF,
    QRect,
    QRectF,
    Qt,
    QTimer,
    QUrl,
    QVariantAnimation,
    Signal,
)
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPen, QPixmap, QWheelEvent
from PySide6.QtWidgets import (
    QGraphicsEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from api.images import ImageStore, get_store
from api.movies import MediaDetails, MediaItem
from theme import theme_manager as theme
from ui.components.artwork import draw_cover, fill_vertical_scrim, rounded_path
from ui.components.icons import make_icon
from ui.components.motion import motion_enabled

try:
    from PySide6.QtWebEngineWidgets import QWebEngineView
    _HAVE_WEBENGINE = True
except ImportError:
    _HAVE_WEBENGINE = False
    QWebEngineView = None  # type: ignore[assignment, misc]

# Type alias: any widget that has .item, .pixmap, .underMouse(), .mapTo() etc.
_AnyTile = Any

CARD_W = 356
IMG_H = round(CARD_W * 9 / 16)
INFO_H = 118
PAD = 22  # room for the shadow on every side

# Timing constants
SHOW_DELAY = 350       # Phase 1: hover intent delay before opening preview
SWAP_DELAY = 120       # Delay when switching between already visible tiles
HIDE_DELAY = 140       # Grace period before hiding on mouse leave
COUNTDOWN_MS = 2500    # Phase 2: trailer autoplay countdown (2.5 seconds)
COUNTDOWN_STEP_MS = 30 # Progress bar tick rate (~33 fps)


def embed_hover_html(
    key: str,
    logo_url: str,
    title: str,
    muted: bool = True,
    show_close: bool = False,
) -> str:
    """HTML page holding the embedded YouTube player with logo and mute overlay."""
    mute_flag = 1 if muted else 0
    safe_title = (
        title.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )

    if logo_url:
        logo_content = f'<img class="logo-img" src="{logo_url}" alt="{safe_title}">'
    else:
        logo_content = f'<span class="logo-text">{safe_title}</span>'

    svg_muted = (
        '<svg viewBox="0 0 24 24">'
        '<path d="M11 4.702a.705.705 0 0 0-1.203-.498L6.413 7.587A1.4 1.4 0 0 1 5.416 8H3a1 1 0 0 0-1 1v6a1 1 0 0 0 1 1h2.416a1.4 1.4 0 0 1 .997.413l3.383 3.384A.705.705 0 0 0 11 19.298z"/>'
        '<path d="m16.5 14.5 5-5"/><path d="m16.5 9.5 5 5"/>'
        '</svg>'
    )
    svg_sound = (
        '<svg viewBox="0 0 24 24">'
        '<path d="M11 4.702a.705.705 0 0 0-1.203-.498L6.413 7.587A1.4 1.4 0 0 1 5.416 8H3a1 1 0 0 0-1 1v6a1 1 0 0 0 1 1h2.416a1.4 1.4 0 0 1 .997.413l3.383 3.384A.705.705 0 0 0 11 19.298z"/>'
        '<path d="M16 9a5 5 0 0 1 0 6"/>'
        '<path d="M19.364 18.364a9 9 0 0 0 0-12.728"/>'
        '</svg>'
    )
    svg_close = (
        '<svg viewBox="0 0 24 24">'
        '<path d="M18 6 6 18"/><path d="m6 6 12 12"/>'
        '</svg>'
    )

    initial_icon = svg_muted if muted else svg_sound
    close_btn_html = (
        f'<button id="close-btn" class="icon-btn" title="Close" onclick="onCloseClick()">{svg_close}</button>'
        if show_close
        else ""
    )

    return f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<meta name="referrer" content="strict-origin-when-cross-origin">
<style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
html, body {{
  width: 100%; height: 100%; background: #000; overflow: hidden;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  border-radius: 8px 8px 0 0;
}}
#player-wrap {{
  position: relative; inset: 0; width: 100%; height: 100%;
  overflow: hidden; pointer-events: none;
  border-radius: 8px 8px 0 0;
}}
iframe {{
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  transform: scale(1.5);
  transform-origin: center center;
  border: 0;
  pointer-events: none;
}}
.scrim-bottom {{
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 48px;
  background: linear-gradient(to top, rgba(18, 18, 22, 0.95), transparent);
  pointer-events: none;
  z-index: 5;
}}
.overlay {{
  position: absolute; inset: 0; pointer-events: none; z-index: 10;
}}
.logo-box {{
  position: absolute; top: 12px; left: 16px; max-width: 160px; max-height: 54px;
  display: flex; align-items: center; pointer-events: none;
}}
.logo-img {{
  max-width: 100%; max-height: 54px; object-fit: contain;
  filter: drop-shadow(0 2px 8px rgba(0,0,0,0.85));
}}
.logo-text {{
  color: #fff; font-size: 15px; font-weight: 700;
  text-shadow: 0 2px 6px rgba(0,0,0,0.9);
  line-height: 1.2;
}}
.controls-box {{
  position: absolute; top: 12px; right: 14px;
  display: flex; align-items: center; gap: 8px;
}}
.icon-btn {{
  width: 32px; height: 32px; border-radius: 50%;
  background: rgba(18, 18, 22, 0.75); border: 1px solid rgba(255, 255, 255, 0.25);
  color: #fff; cursor: pointer; display: flex; align-items: center; justify-content: center;
  pointer-events: auto; transition: background 0.2s, transform 0.15s; outline: none;
}}
.icon-btn:hover {{ background: rgba(40, 42, 50, 0.9); transform: scale(1.08); }}
.icon-btn svg {{
  width: 16px; height: 16px; fill: none; stroke: currentColor; stroke-width: 2;
  stroke-linecap: round; stroke-linejoin: round;
}}
</style>
</head>
<body>
<div id="player-wrap">
  <iframe id="yt-player"
    src="https://www.youtube-nocookie.com/embed/{key}?autoplay=1&mute={mute_flag}&enablejsapi=1&controls=0&modestbranding=1&rel=0&playsinline=1&loop=1&playlist={key}&disablekb=1&fs=0&iv_load_policy=3&cc_load_policy=0"
    referrerpolicy="strict-origin-when-cross-origin"
    allow="autoplay; encrypted-media"
    allowfullscreen></iframe>
  <div class="scrim-bottom"></div>
</div>
<div class="overlay">
  <div class="logo-box">
    {logo_content}
  </div>
  <div class="controls-box">
    <button id="mute-btn" class="icon-btn" title="Toggle audio" onclick="toggleMute()">
      {initial_icon}
    </button>
    {close_btn_html}
  </div>
</div>
<script>
let isMuted = {'true' if muted else 'false'};
const svgMuted = `{svg_muted}`;
const svgSound = `{svg_sound}`;
function toggleMute() {{
  const iframe = document.getElementById('yt-player');
  isMuted = !isMuted;
  const cmd = isMuted ? 'mute' : 'unMute';
  iframe.contentWindow.postMessage(JSON.stringify({{
    event: 'command',
    func: cmd,
    args: ''
  }}), '*');
  const btn = document.getElementById('mute-btn');
  btn.innerHTML = isMuted ? svgMuted : svgSound;
  btn.setAttribute('title', isMuted ? 'Unmute' : 'Mute');
}}
function onCloseClick() {{
  document.title = "action:close";
}}
</script>
</body>
</html>"""


class _ScaleFadeEffect(QGraphicsEffect):
    """Draws the widget scaled about ``anchor`` and faded; progress 1 is rest."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._progress = 1.0
        self._anchor = QPointF(0.5, 0.5)

    def set_anchor(self, fx: float, fy: float) -> None:
        self._anchor = QPointF(fx, fy)

    def set_progress(self, value: float) -> None:
        value = max(0.0, min(1.0, float(value)))
        if value != self._progress:
            self._progress = value
            self.update()

    def draw(self, painter) -> None:
        if self._progress <= 0.0:
            return
        offset = QPoint()
        pixmap = self.sourcePixmap(
            Qt.CoordinateSystem.LogicalCoordinates,
            offset,
            QGraphicsEffect.PixmapPadMode.NoPad,
        )
        if pixmap.isNull():
            return
        ratio = pixmap.devicePixelRatio() or 1.0
        width, height = pixmap.width() / ratio, pixmap.height() / ratio
        scale = 0.84 + 0.16 * self._progress
        center = QPointF(offset) + QPointF(
            width * self._anchor.x(), height * self._anchor.y()
        )
        painter.save()
        painter.setOpacity(painter.opacity() * self._progress)
        painter.translate(center)
        painter.scale(scale, scale)
        painter.translate(-center)
        painter.drawPixmap(QPointF(offset), pixmap)
        painter.restore()


class HoverPreview(QWidget):
    play_requested = Signal(object)      # MediaItem
    details_requested = Signal(object)   # MediaItem
    wheel_passthrough = Signal(object)   # QWheelEvent
    details_needed = Signal(object)      # MediaItem

    def __init__(self, host: QWidget, store: ImageStore | None = None) -> None:
        super().__init__(host)
        self._store = store
        self._tile: _AnyTile | None = None
        self._pending: _AnyTile | None = None
        self._item: MediaItem | None = None
        self._details: MediaDetails | None = None
        self._anim: QVariantAnimation | None = None
        self._effect: _ScaleFadeEffect | None = None
        self._anchor = QPointF(0.5, 0.5)

        self._backdrop_pixmap: QPixmap | None = None
        self._logo_pixmap: QPixmap | None = None
        self._muted = True
        self._in_watchlist = False
        self._is_playing = False
        self._pending_trailer_play = False
        self._countdown_active = False
        self._countdown_progress = 0.0
        self._countdown_remaining = COUNTDOWN_MS

        self.setFixedSize(CARD_W + 2 * PAD, IMG_H + INFO_H + 2 * PAD)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.hide()

        # WebEngine embedded view for in-card trailer playback
        if _HAVE_WEBENGINE and QWebEngineView is not None:
            self.web_view = QWebEngineView(self)
            self.web_view.setGeometry(PAD, PAD, CARD_W, IMG_H)
            self.web_view.hide()
        else:
            self.web_view = None

        # Audio mute toggle button for static preview
        self.mute_button = QPushButton(self)
        self.mute_button.setGeometry(PAD + CARD_W - 42, PAD + 12, 32, 32)
        self.mute_button.setIcon(make_icon("volume-x", "#FFFFFF", 16))
        self.mute_button.setToolTip("Unmute trailer")
        self.mute_button.setAccessibleName("Toggle audio")
        self.mute_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mute_button.setStyleSheet(
            "QPushButton { background: rgba(18, 18, 22, 0.75); border: 1px solid rgba(255, 255, 255, 0.25); border-radius: 16px; } "
            "QPushButton:hover { background: rgba(40, 42, 50, 0.9); }"
        )
        self.mute_button.clicked.connect(self._toggle_mute)

        # Deck layout below 16:9 media zone
        column = QVBoxLayout(self)
        column.setContentsMargins(PAD + 16, PAD + IMG_H + 12, PAD + 16, PAD + 12)
        column.setSpacing(6)

        # Action controls row: Play, Watchlist (+), stretch, Details (v)
        actions = QHBoxLayout()
        actions.setSpacing(theme.SPACE_SM)

        self.play_button = QPushButton()
        self.play_button.setProperty("variant", "playDisc")
        self.play_button.setFixedSize(36, 36)
        self.play_button.setIcon(make_icon("play", theme.TEXT_ON_ACCENT, 16))
        self.play_button.setToolTip("Play trailer")
        self.play_button.setAccessibleName("Play trailer")
        self.play_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.play_button.clicked.connect(self._on_play)
        actions.addWidget(self.play_button)

        self.watchlist_button = QPushButton()
        self.watchlist_button.setProperty("variant", "ring")
        self.watchlist_button.setFixedSize(36, 36)
        self.watchlist_button.setIcon(make_icon("plus", theme.TEXT_PRIMARY, 16))
        self.watchlist_button.setToolTip("Add to My List")
        self.watchlist_button.setAccessibleName("Add to My List")
        self.watchlist_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.watchlist_button.clicked.connect(self._toggle_watchlist)
        actions.addWidget(self.watchlist_button)

        actions.addStretch(1)

        self.details_button = QPushButton()
        self.details_button.setProperty("variant", "ring")
        self.details_button.setFixedSize(36, 36)
        self.details_button.setIcon(make_icon("chevron", theme.TEXT_PRIMARY, 16, rotate=90))
        self.details_button.setToolTip("More info")
        self.details_button.setAccessibleName("More info")
        self.details_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.details_button.clicked.connect(self._on_details)
        actions.addWidget(self.details_button)
        column.addLayout(actions)

        # Metadata specifications row: Certification, Runtime, Quality, Views
        meta_row = QHBoxLayout()
        meta_row.setSpacing(8)

        self.cert_label = QLabel("PG-13")
        self.cert_label.setStyleSheet(
            "border: 1px solid rgba(255, 255, 255, 0.35); border-radius: 3px; "
            "padding: 1px 5px; font-size: 10px; font-weight: bold; color: rgba(255, 255, 255, 0.9);"
        )
        meta_row.addWidget(self.cert_label)

        self.runtime_label = QLabel("")
        self.runtime_label.setProperty("role", "muted")
        meta_row.addWidget(self.runtime_label)

        self.quality_badge = QLabel("HD")
        self.quality_badge.setStyleSheet(
            "border: 1px solid rgba(255, 255, 255, 0.35); border-radius: 3px; "
            "padding: 1px 4px; font-size: 10px; font-weight: bold; color: rgba(255, 255, 255, 0.85);"
        )
        meta_row.addWidget(self.quality_badge)

        self.views_label = QLabel("")
        self.views_label.setProperty("role", "muted")
        meta_row.addWidget(self.views_label)
        meta_row.addStretch(1)
        column.addLayout(meta_row)

        # Categorization / Genre line
        self.genres_label = QLabel("")
        self.genres_label.setStyleSheet("color: rgba(255, 255, 255, 0.65); font-size: 11px;")
        column.addWidget(self.genres_label)
        column.addStretch(1)

        # Intent delay timer (Phase 1)
        self._show_timer = QTimer(self)
        self._show_timer.setSingleShot(True)
        self._show_timer.timeout.connect(self._show_pending)

        # Hide grace period timer
        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self._maybe_hide)

        # Trailer countdown timer (Phase 2)
        self._countdown_timer = QTimer(self)
        self._countdown_timer.setInterval(COUNTDOWN_STEP_MS)
        self._countdown_timer.timeout.connect(self._on_countdown_tick)

    # ── Driven by the tiles ─────────────────────────────────────────────────
    @property
    def item(self) -> MediaItem | None:
        return self._item

    def tile_entered(self, tile: Any) -> None:
        self._hide_timer.stop()
        if self.isVisible() and self._tile is tile:
            return
        self._pending = tile
        self._show_timer.start(SWAP_DELAY if self.isVisible() else SHOW_DELAY)

    def tile_left(self, tile: Any) -> None:
        if self._pending is tile:
            self._show_timer.stop()
            self._pending = None
        if self.isVisible() and self._tile is tile:
            self._hide_timer.start(HIDE_DELAY)

    def dismiss(self) -> None:
        """Hide immediately (scrolling, navigation, closing the page)."""
        self._show_timer.stop()
        self._hide_timer.stop()
        self._pending = None
        self._stop_countdown()
        self._stop_animation()
        self._tile = None
        self.hide()

    # ── Showing and hiding ──────────────────────────────────────────────────
    def _show_pending(self) -> None:
        tile = self._pending
        self._pending = None
        if tile is None or not tile.isVisible() or not tile.underMouse():
            return
        visible = tile.visibleRegion().boundingRect()
        if visible.width() < tile.width() * 0.4:
            return

        self._stop_animation()
        self._stop_countdown()
        self._tile = tile
        self._item = tile.item
        self._details = None
        self._pending_trailer_play = False
        self._is_playing = False

        if self.web_view is not None:
            self.web_view.setHtml("")
            self.web_view.hide()

        self._fill(tile.item)
        anchor = self._place(tile)
        self.raise_()
        self.show()
        self._animate_in(anchor)
        self._start_countdown()
        self.details_needed.emit(tile.item)

    def _maybe_hide(self) -> None:
        if self._tile is not None and self._tile.underMouse():
            return
        if self.underMouse():
            return
        self._stop_countdown()
        self._animate_out()

    def _fill(self, item: MediaItem) -> None:
        self._backdrop_pixmap = None
        self._logo_pixmap = None
        self._in_watchlist = False
        self.watchlist_button.setIcon(make_icon("plus", theme.TEXT_PRIMARY, 16))
        self.watchlist_button.setToolTip("Add to My List")

        # Request separate landscape backdrop (never reuse portrait poster as default)
        store = self._store or get_store()
        url = item.backdrop_url("w780") or item.poster_url("w500")
        store.request(url, CARD_W * 2, self._on_backdrop, owner=self)

        # Baseline specifications
        cert = "PG-13" if item.media_type == "movie" else "TV-14"
        self.cert_label.setText(cert)
        self.runtime_label.setText(item.year)
        self.quality_badge.setVisible(True)

        views_val = item.votes * 12 + 1042 if item.votes > 0 else 0
        self.views_label.setText(f"\U0001F441 {views_val:,}" if views_val > 0 else "")

        genres = " \u2022 ".join(item.genre_names[:3])
        self.genres_label.setText(genres)

        self.mute_button.show()
        self.mute_button.raise_()
        self.update()

    def set_details(self, details: MediaDetails) -> None:
        """Receive rich metadata from TMDB: certification, runtime, logo, trailer."""
        if self._item is None or details.item.key != self._item.key:
            return
        self._details = details
        if details.certification:
            self.cert_label.setText(details.certification)
        if details.runtime_text:
            self.runtime_label.setText(details.runtime_text)
        backdrop_url = details.textless_backdrop_url("w780") or details.backdrop_url("w780")
        if backdrop_url:
            (self._store or get_store()).request(
                backdrop_url,
                CARD_W * 2,
                self._on_backdrop,
                owner=self,
            )
        if details.logo_path:
            (self._store or get_store()).request(
                details.logo_url("w500"),
                300,
                self._on_logo,
                owner=self,
            )
        if self._pending_trailer_play:
            self._pending_trailer_play = False
            self._start_trailer_playback()

    def _on_backdrop(self, pixmap: QPixmap | None) -> None:
        self._backdrop_pixmap = pixmap
        self.update()

    def _on_logo(self, pixmap: QPixmap | None) -> None:
        if pixmap is not None and not pixmap.isNull():
            self._logo_pixmap = pixmap.scaled(
                150,
                48,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        self.update()

    # ── Countdown and video playback ─────────────────────────────────────────
    def _start_countdown(self) -> None:
        self._countdown_active = True
        self._countdown_progress = 0.0
        self._countdown_remaining = COUNTDOWN_MS
        self._countdown_timer.start()
        self.mute_button.setIcon(make_icon("volume-x" if self._muted else "volume-2", "#FFFFFF", 16))
        self.mute_button.setToolTip("Unmute trailer" if self._muted else "Mute trailer")
        self.mute_button.show()
        self.mute_button.raise_()

    def _stop_countdown(self) -> None:
        self._countdown_timer.stop()
        self._countdown_active = False
        self._countdown_progress = 0.0
        self._pending_trailer_play = False
        self._is_playing = False
        if self.web_view is not None:
            self.web_view.setHtml("")
            self.web_view.hide()
        self.mute_button.show()
        self.update()

    def _on_countdown_tick(self) -> None:
        self._countdown_remaining -= COUNTDOWN_STEP_MS
        self._countdown_progress = 1.0 - max(0.0, self._countdown_remaining) / float(COUNTDOWN_MS)
        if self._countdown_remaining <= 0:
            self._countdown_timer.stop()
            self._countdown_active = False
            self._countdown_progress = 1.0
            self._start_trailer_playback()
        self.update()

    def _start_trailer_playback(self) -> None:
        if not _HAVE_WEBENGINE or self.web_view is None:
            return
        if self._details is not None and self._details.trailer_key:
            key = self._details.trailer_key
            logo_url = self._details.logo_url("w500") if self._details.logo_path else ""
            title = self._item.title if self._item else ""
            html = embed_hover_html(key, logo_url, title, muted=self._muted)
            self.web_view.setHtml(html, QUrl("https://entertainx.local/"))
            self.web_view.show()
            self.web_view.raise_()
            self.mute_button.hide()
            self._is_playing = True
            self.update()
        else:
            # Details still in flight: flag to start immediately upon receipt
            self._pending_trailer_play = True

    def _toggle_mute(self) -> None:
        self._muted = not self._muted
        self.mute_button.setIcon(make_icon("volume-x" if self._muted else "volume-2", "#FFFFFF", 16))
        self.mute_button.setToolTip("Unmute trailer" if self._muted else "Mute trailer")
        if self._is_playing and self.web_view is not None:
            self.web_view.page().runJavaScript("if (typeof toggleMute === 'function') toggleMute();")

    def _toggle_watchlist(self) -> None:
        self._in_watchlist = not self._in_watchlist
        if self._in_watchlist:
            self.watchlist_button.setIcon(make_icon("check", theme.PRIMARY, 16))
            self.watchlist_button.setToolTip("In My List")
        else:
            self.watchlist_button.setIcon(make_icon("plus", theme.TEXT_PRIMARY, 16))
            self.watchlist_button.setToolTip("Add to My List")

    # ── Placement & Geometry ────────────────────────────────────────────────
    def _place(self, tile: Any) -> QPointF:
        host = self.parentWidget()
        if host is None:
            return QPointF(0.5, 0.5)
        origin = tile.mapTo(host, QPoint(0, 0))
        overlap = getattr(tile, "overlap", 0)
        poster_w = tile.width() - overlap
        poster_center_x = origin.x() + overlap + poster_w // 2
        poster_center_y = origin.y() + tile.height() // 2

        card_h = IMG_H + INFO_H
        x = poster_center_x - CARD_W // 2
        y = poster_center_y - IMG_H // 2
        x = max(8, min(x, host.width() - 8 - CARD_W))
        y = max(8, min(y, host.height() - 8 - card_h))
        self.move(x - PAD, y - PAD)

        anchor_x = (poster_center_x - (x - PAD)) / self.width()
        anchor_y = (poster_center_y - (y - PAD)) / self.height()
        return QPointF(anchor_x, anchor_y)

    # ── Motion ──────────────────────────────────────────────────────────────
    def _stop_animation(self) -> None:
        if self._anim is not None:
            self._anim.stop()
            self._anim = None
        if self._effect is not None:
            self.setGraphicsEffect(None)  # type: ignore[arg-type]
            self._effect = None

    def _run(self, start: float, end: float, duration: int, easing, on_finished) -> None:
        effect = _ScaleFadeEffect(self)
        effect.set_anchor(self._anchor.x(), self._anchor.y())
        effect.set_progress(start)
        self.setGraphicsEffect(effect)
        self._effect = effect

        animation = QVariantAnimation(self)
        animation.setStartValue(float(start))
        animation.setEndValue(float(end))
        animation.setDuration(duration)
        animation.setEasingCurve(easing)
        animation.valueChanged.connect(lambda value: effect.set_progress(float(value)))

        def finished() -> None:
            if self._anim is animation:
                self._anim = None
                self.setGraphicsEffect(None)  # type: ignore[arg-type]
                self._effect = None
                on_finished()

        animation.finished.connect(finished)
        self._anim = animation
        animation.start()

    def _animate_in(self, anchor: QPointF) -> None:
        self._anchor = anchor
        if not motion_enabled():
            return
        self._run(0.0, 1.0, 190, QEasingCurve.Type.OutCubic, lambda: None)

    def _animate_out(self) -> None:
        self._stop_animation()
        self._tile = None
        if not motion_enabled():
            self.hide()
            return
        self._run(1.0, 0.0, 110, QEasingCurve.Type.InCubic, self.hide)

    # ── Actions ─────────────────────────────────────────────────────────────
    def _on_play(self) -> None:
        if self._item is not None:
            self.play_requested.emit(self._item)

    def _on_details(self) -> None:
        if self._item is not None:
            self.details_requested.emit(self._item)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self._on_details()
        super().mouseReleaseEvent(event)

    def enterEvent(self, event) -> None:  # noqa: N802
        super().enterEvent(event)
        self._hide_timer.stop()

    def leaveEvent(self, event) -> None:  # noqa: N802
        super().leaveEvent(event)
        if self.isVisible():
            self._hide_timer.start(HIDE_DELAY)

    def wheelEvent(self, event: QWheelEvent) -> None:  # noqa: N802
        self.wheel_passthrough.emit(event)

    # ── Painting ────────────────────────────────────────────────────
    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        card = QRectF(PAD, PAD, CARD_W, IMG_H + INFO_H)
        radius = float(theme.RADIUS_LG)

        # Multi-layer diffused shadow
        painter.setPen(Qt.PenStyle.NoPen)
        for step in range(10, 0, -1):
            grow = step * 1.6
            shadow = QColor(theme.SHADOW)
            shadow.setAlphaF(0.045 + (10 - step) * 0.006)
            painter.setBrush(shadow)
            painter.drawRoundedRect(
                card.adjusted(-grow, -grow + 7, grow, grow + 7), radius + grow, radius + grow
            )

        painter.setClipPath(rounded_path(card, radius))
        painter.fillRect(card, QColor(theme.BG_CARD))

        art = QRectF(card.left(), card.top(), card.width(), IMG_H)

        # Only paint media background when web_view video is not active
        if not self._is_playing:
            if self._backdrop_pixmap is not None and not self._backdrop_pixmap.isNull():
                draw_cover(painter, art, self._backdrop_pixmap, 0.5, 0.15)
            else:
                ground = QLinearGradient(art.topLeft(), art.bottomRight())
                ground.setColorAt(0.0, QColor(theme.BG_ELEVATED))
                ground.setColorAt(1.0, QColor(theme.BG_CARD))
                painter.fillRect(art, ground)

            fill_vertical_scrim(painter, art, 0.40, 0.88)

            # Official transparent logo overlay in top-left
            if self._logo_pixmap is not None and not self._logo_pixmap.isNull():
                painter.drawPixmap(QPointF(art.left() + 16, art.top() + 14), self._logo_pixmap)
            elif self._item is not None:
                font = painter.font()
                font.setPixelSize(theme.FONT_SIZE_XL)
                font.setWeight(font.Weight.DemiBold)
                painter.setFont(font)
                painter.setPen(QColor(theme.TEXT_PRIMARY))
                text = painter.fontMetrics().elidedText(
                    self._item.title, Qt.TextElideMode.ElideRight, int(art.width() - 80)
                )
                painter.drawText(int(art.left() + 16), int(art.top() + 38), text)

            # Countdown progress bar along bottom of media preview
            if self._countdown_active and self._countdown_progress > 0:
                prog_w = art.width() * min(1.0, max(0.0, self._countdown_progress))
                if prog_w > 0:
                    painter.setPen(Qt.PenStyle.NoPen)
                    painter.fillRect(
                        QRectF(art.left(), art.bottom() - 3, art.width(), 3),
                        QColor(255, 255, 255, 45),
                    )
                    painter.fillRect(
                        QRectF(art.left(), art.bottom() - 3, prog_w, 3),
                        QColor(theme.PRIMARY),
                    )

        painter.setClipping(False)
        painter.setPen(QPen(QColor(theme.BORDER_STRONG), 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(rounded_path(card.adjusted(0.5, 0.5, -0.5, -0.5), radius))
        painter.end()
