"""The floating card that grows out of a tile on hover (Netflix-style).

The preview is a child of the page, not of the shelf, so it can extend past the
shelf's edges. It is positioned over the hovered tile, scales and fades in from
the tile's centre, displays landscape backdrop art, official logo overlays,
interactive action controls, watch progress, and auto-plays the trailer with an
animated circular countdown ring.
"""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import (
    QEasingCurve,
    QPoint,
    QPointF,
    QRectF,
    Qt,
    QTimer,
    QVariantAnimation,
    Signal,
)
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPen, QPixmap, QWheelEvent
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from api.images import ImageStore, get_store
from api.movies import MediaDetails, MediaItem
from theme import theme_manager as theme
from ui.components.artwork import draw_cover, rounded_path
from ui.components.icons import make_icon
from ui.components.motion import ScaleFadeEffect, motion_enabled
from ui.components.trailer.player import (
    CountdownController,
    TrailerPlayer,
    TrailerSpec,
    render_trailer_html,
)

# Type alias: any widget that has .item, .pixmap, .underMouse(), .mapTo() etc.
_AnyTile = Any

CARD_W = 360
IMG_H = round(CARD_W * 9 / 16)  # 203 (16:9 aspect ratio)
INFO_H = 126
PAD = 20  # Room for diffused shadow

# Timing constants
SHOW_DELAY = 350        # Phase 1: hover intent delay before opening preview
SWAP_DELAY = 120        # Delay when switching between already visible tiles
HIDE_DELAY = 140        # Grace period before hiding on mouse leave




def _play_btn_style() -> str:
    return f"""
        QPushButton {{
            width: 32px;
            height: 32px;
            border-radius: 16px;
            border: none;
            background-color: {theme.PRIMARY};
            padding: 0;
        }}
        QPushButton:hover {{
            background-color: {theme.ACCENT_HOVER};
        }}
        QPushButton:pressed {{
            background-color: {theme.ACCENT_PRESSED};
        }}
    """


def _circle_btn_style() -> str:
    return """
        QPushButton {
            width: 32px;
            height: 32px;
            border-radius: 16px;
            border: 1px solid rgba(255, 255, 255, 0.3);
            background-color: transparent;
            padding: 0;
        }
        QPushButton:hover {
            border-color: #FFFFFF;
            background-color: rgba(255, 255, 255, 0.1);
        }
        QPushButton:pressed {
            background-color: rgba(255, 255, 255, 0.18);
        }
    """


def _active_circle_btn_style() -> str:
    return f"""
        QPushButton {{
            width: 32px;
            height: 32px;
            border-radius: 16px;
            border: 1px solid {theme.PRIMARY};
            background-color: rgba(255, 255, 255, 0.08);
            padding: 0;
        }}
        QPushButton:hover {{
            border-color: {theme.ACCENT_HOVER};
            background-color: rgba(255, 255, 255, 0.14);
        }}
        QPushButton:pressed {{
            background-color: rgba(255, 255, 255, 0.2);
        }}
    """


class _WatchTrack(QWidget):
    """Custom painted 3px progress track matching trailer_preview.html."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(3)
        self._ratio = 0.18

    def set_ratio(self, ratio: float) -> None:
        self._ratio = max(0.0, min(1.0, ratio))
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        rect = QRectF(self.rect())
        painter.setPen(Qt.PenStyle.NoPen)
        # Background track: rgba(255, 255, 255, 0.25)
        painter.setBrush(QColor(255, 255, 255, 64))
        painter.drawRoundedRect(rect, 1.5, 1.5)
        # Fill: theme.PRIMARY
        if self._ratio > 0:
            fill_w = max(3.0, rect.width() * self._ratio)
            fill_rect = QRectF(rect.left(), rect.top(), fill_w, rect.height())
            painter.setBrush(QColor(theme.PRIMARY))
            painter.drawRoundedRect(fill_rect, 1.5, 1.5)
        painter.end()


class _WatchProgressRow(QWidget):
    """Row displaying watch progress track and text ('23 of 127m')."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.track = _WatchTrack(self)
        self.label = QLabel("23 of 127m", self)
        self.label.setStyleSheet(
            "font-size: 11px; font-weight: 600; color: rgba(255, 255, 255, 0.85); white-space: nowrap;"
        )

        layout.addWidget(self.track, 1)
        layout.addWidget(self.label, 0)

    def set_progress(self, current_min: int, total_min: int) -> None:
        if current_min > 0 and total_min > 0:
            ratio = current_min / float(total_min)
            self.track.set_ratio(ratio)
            self.label.setText(f"{current_min} of {total_min}m")
            self.show()
        else:
            self.hide()


def embed_hover_html(
    key: str,
    logo_url: str = "",
    title: str = "",
    backdrop_url: str = "",
    muted: bool = False,
    show_close: bool = False,
) -> str:
    """Delegate to :func:`render_trailer_html` with mode ``hover``."""
    return render_trailer_html(
        "hover",
        TrailerSpec(
            key=key,
            title=title,
            logo_url=logo_url,
            backdrop_url=backdrop_url,
            muted=muted,
            show_close=show_close,
        ),
    )


class HoverPreview(QWidget):
    play_requested = Signal(object)      # MediaItem
    details_requested = Signal(object)   # MediaItem
    like_toggled = Signal(object, bool)  # MediaItem, is_liked
    watchlist_toggled = Signal(object, bool)  # MediaItem, in_watchlist
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
        self._effect: ScaleFadeEffect | None = None
        self._anchor = QPointF(0.5, 0.5)

        self._backdrop_pixmap: QPixmap | None = None
        self._logo_pixmap: QPixmap | None = None
        self._muted = False
        self._in_watchlist = False
        self._liked = False
        self._pending_trailer_play = False
        self._countdown_progress = 0.0
        self._watch_current = 23
        self._watch_total = 127

        self.setFixedSize(CARD_W + 2 * PAD, IMG_H + INFO_H + 2 * PAD)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.hide()

        # Countdown controller (replaces manual QTimer + tick math)
        self._countdown = CountdownController(parent=self)
        self._countdown.progressed.connect(self._on_countdown_progress)
        self._countdown.completed.connect(self._on_countdown_complete)

        # Unified trailer player for in-card trailer playback
        self._player = TrailerPlayer(mode="hover", parent=self)
        self._player.setGeometry(PAD, PAD, CARD_W, IMG_H)
        self._player.action_triggered.connect(self._on_player_action)
        self._player.playback_stopped.connect(self._on_playback_stopped)
        self._player.hide()

        # Audio mute toggle button for static preview
        self.mute_button = QPushButton(self)
        self.mute_button.setGeometry(PAD + CARD_W - 14 - 32, PAD + 12, 32, 32)
        self.mute_button.setIcon(make_icon("volume-2", "#FFFFFF", 15))
        self.mute_button.setToolTip("Mute trailer")
        self.mute_button.setAccessibleName("Toggle audio")
        self.mute_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mute_button.setStyleSheet(
            "QPushButton { background: rgba(18, 18, 22, 0.75); border: 1px solid rgba(255, 255, 255, 0.25); border-radius: 16px; } "
            "QPushButton:hover { background: rgba(35, 35, 42, 0.95); }"
        )
        self.mute_button.clicked.connect(self._toggle_mute)

        # Deck layout below 16:9 media zone matching trailer_preview.html info-deck
        column = QVBoxLayout(self)
        column.setContentsMargins(PAD + 14, PAD + IMG_H + 12, PAD + 14, PAD + 14)
        column.setSpacing(6)

        # Action controls row: Play, Add to list (+), Like, Spacer, More info (v)
        actions = QHBoxLayout()
        actions.setSpacing(8)

        self.play_button = QPushButton(self)
        self.play_button.setFixedSize(32, 32)
        self.play_button.setIcon(make_icon("play", theme.TEXT_ON_ACCENT, 14))
        self.play_button.setToolTip("Play trailer")
        self.play_button.setAccessibleName("Play trailer")
        self.play_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.play_button.setStyleSheet(_play_btn_style())
        self.play_button.clicked.connect(self._on_play)
        actions.addWidget(self.play_button)

        self.watchlist_button = QPushButton(self)
        self.watchlist_button.setFixedSize(32, 32)
        self.watchlist_button.setIcon(make_icon("plus", theme.TEXT_PRIMARY, 14))
        self.watchlist_button.setToolTip("Add to My List")
        self.watchlist_button.setAccessibleName("Add to My List")
        self.watchlist_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.watchlist_button.setStyleSheet(_circle_btn_style())
        self.watchlist_button.clicked.connect(self._toggle_watchlist)
        actions.addWidget(self.watchlist_button)

        self.like_button = QPushButton(self)
        self.like_button.setFixedSize(32, 32)
        self.like_button.setIcon(make_icon("thumbs-up", theme.TEXT_PRIMARY, 14))
        self.like_button.setToolTip("Like")
        self.like_button.setAccessibleName("Like")
        self.like_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.like_button.setStyleSheet(_circle_btn_style())
        self.like_button.clicked.connect(self._toggle_like)
        actions.addWidget(self.like_button)

        actions.addStretch(1)

        self.details_button = QPushButton(self)
        self.details_button.setFixedSize(32, 32)
        self.details_button.setIcon(make_icon("chevron-down", theme.TEXT_PRIMARY, 14))
        self.details_button.setToolTip("More info")
        self.details_button.setAccessibleName("More info")
        self.details_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.details_button.setStyleSheet(_circle_btn_style())
        self.details_button.clicked.connect(self._on_details)
        actions.addWidget(self.details_button)
        column.addLayout(actions)

        # Watch Progress Bar row (matching trailer_preview.html: progress-row)
        self.progress_row = _WatchProgressRow(self)
        column.addWidget(self.progress_row)

        # Metadata specifications row: Certification badge, Runtime, Quality badge, Views
        meta_row = QHBoxLayout()
        meta_row.setSpacing(8)

        self.cert_label = QLabel("PG-13", self)
        self.cert_label.setStyleSheet(
            "border: 1px solid rgba(255, 255, 255, 0.35); border-radius: 3px; "
            "padding: 1px 4px; font-size: 10px; font-weight: 700; color: rgba(255, 255, 255, 0.9);"
        )
        meta_row.addWidget(self.cert_label)

        self.runtime_label = QLabel("", self)
        self.runtime_label.setStyleSheet("font-size: 11px; color: rgba(255, 255, 255, 0.7);")
        meta_row.addWidget(self.runtime_label)

        self.quality_badge = QLabel("HD", self)
        self.quality_badge.setStyleSheet(
            "border: 1px solid rgba(255, 255, 255, 0.35); border-radius: 3px; "
            "padding: 1px 4px; font-size: 10px; font-weight: 700; color: rgba(255, 255, 255, 0.85);"
        )
        meta_row.addWidget(self.quality_badge)

        self.views_label = QLabel("", self)
        self.views_label.setStyleSheet("font-size: 11px; color: rgba(255, 255, 255, 0.7);")
        meta_row.addWidget(self.views_label)
        meta_row.addStretch(1)
        column.addLayout(meta_row)

        # Categorization / Genre line
        self.genres_label = QLabel("", self)
        self.genres_label.setStyleSheet("color: rgba(255, 255, 255, 0.55); font-size: 11px;")
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
        self._player.stop()

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

    def set_watch_progress(self, current_min: int, total_min: int) -> None:
        """Set watched minutes and total minutes for the progress bar."""
        self._watch_current = current_min
        self._watch_total = total_min
        self.progress_row.set_progress(current_min, total_min)

    def _fill(self, item: MediaItem) -> None:
        self._backdrop_pixmap = None
        self._logo_pixmap = None
        self._in_watchlist = False
        self._liked = False

        # Apply theme-based styling to action buttons
        self.play_button.setStyleSheet(_play_btn_style())
        self.play_button.setIcon(make_icon("play", theme.TEXT_ON_ACCENT, 14))

        self.watchlist_button.setStyleSheet(_circle_btn_style())
        self.watchlist_button.setIcon(make_icon("plus", theme.TEXT_PRIMARY, 14))
        self.watchlist_button.setToolTip("Add to My List")

        self.like_button.setStyleSheet(_circle_btn_style())
        self.like_button.setIcon(make_icon("thumbs-up", theme.TEXT_PRIMARY, 14))
        self.like_button.setToolTip("Like")

        self.details_button.setStyleSheet(_circle_btn_style())
        self.details_button.setIcon(make_icon("chevron-down", theme.TEXT_PRIMARY, 14))

        # Request landscape backdrop
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

        # Watch progress bar matching trailer_preview.html
        if hasattr(item, "watch_progress") and item.watch_progress:
            curr, tot = item.watch_progress
            self.set_watch_progress(curr, tot)
        else:
            # Default watch progress demonstration matching trailer_preview.html (23 of 127m)
            self.set_watch_progress(23, 127)

        self.mute_button.setIcon(make_icon("volume-x" if self._muted else "volume-2", "#FFFFFF", 15))
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
            text = details.runtime_text
            try:
                total_m = 0
                for part in text.split():
                    if part.endswith("h"):
                        total_m += int(part[:-1]) * 60
                    elif part.endswith("m"):
                        total_m += int(part[:-1])
                if total_m > 0:
                    curr_m = round(total_m * 0.18)
                    self.set_watch_progress(curr_m, total_m)
            except Exception:
                pass

        backdrop_url = details.backdrop_url("w780")
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
                180,
                48,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        self.update()

    # ── Countdown and video playback ─────────────────────────────────────────

    @property
    def _countdown_active(self) -> bool:
        return self._countdown.is_active

    @property
    def _is_playing(self) -> bool:
        return self._player.is_playing

    @property
    def web_view(self):
        """Backward-compatible accessor for tests that inspect the web view."""
        vp = self._player.viewport
        return vp.widget() if vp is not None else None

    def _on_countdown_progress(self, progress: float) -> None:
        self._countdown_progress = progress
        self.update()

    def _on_countdown_complete(self) -> None:
        self._countdown_progress = 1.0
        self._start_trailer_playback()

    def _on_player_action(self, action: str) -> None:
        if action == "details":
            self._on_details()
        elif action == "play":
            self._on_play()
        elif action == "watchlist":
            self._toggle_watchlist()
        elif action == "like":
            self._toggle_like()
        elif action == "close":
            self.dismiss()
        elif action in ("muted", "unmuted"):
            self._muted = action == "muted"
            self.mute_button.setIcon(make_icon("volume-x" if self._muted else "volume-2", "#FFFFFF", 15))
            self.mute_button.setToolTip("Unmute trailer" if self._muted else "Mute trailer")

    def _on_playback_stopped(self) -> None:
        self.mute_button.show()
        self.update()

    def _start_countdown(self) -> None:
        self._countdown.start()
        self._countdown_progress = 0.0
        self.mute_button.setIcon(make_icon("volume-x" if self._muted else "volume-2", "#FFFFFF", 15))
        self.mute_button.setToolTip("Unmute trailer" if self._muted else "Mute trailer")
        self.mute_button.show()
        self.mute_button.raise_()

    def _stop_countdown(self) -> None:
        self._countdown.stop()
        self._countdown_progress = 0.0
        self._pending_trailer_play = False
        self._player.stop()
        self.mute_button.show()
        self.update()

    def _on_countdown_tick(self) -> None:
        """Backward-compatible shim for tests that call this directly."""
        self._countdown.tick()

    def _start_trailer_playback(self) -> None:
        if not self._player.available:
            return
        if self._details is not None and self._details.trailer_key:
            key = self._details.trailer_key
            logo_url = self._details.logo_url("w500") if self._details.logo_path else ""
            backdrop_url = (
                self._details.backdrop_url("w780")
                or (self._item.backdrop_url("w780") if self._item else "")
            )
            title = self._item.title if self._item else ""
            spec = TrailerSpec(
                key=key,
                title=title,
                logo_url=logo_url,
                backdrop_url=backdrop_url,
                muted=self._muted,
            )
            self._player.setGeometry(PAD, PAD, CARD_W, IMG_H)
            self._player.load(spec)
            self.mute_button.hide()
            self.update()
        else:
            self._pending_trailer_play = True

    def _toggle_mute(self) -> None:
        self._muted = not self._muted
        self.mute_button.setIcon(make_icon("volume-x" if self._muted else "volume-2", "#FFFFFF", 15))
        self.mute_button.setToolTip("Unmute trailer" if self._muted else "Mute trailer")
        if self._is_playing:
            self._player.set_muted(self._muted)

    def _toggle_watchlist(self) -> None:
        self._in_watchlist = not self._in_watchlist
        if self._in_watchlist:
            self.watchlist_button.setIcon(make_icon("check", theme.PRIMARY, 14))
            self.watchlist_button.setStyleSheet(_active_circle_btn_style())
            self.watchlist_button.setToolTip("In My List")
        else:
            self.watchlist_button.setIcon(make_icon("plus", theme.TEXT_PRIMARY, 14))
            self.watchlist_button.setStyleSheet(_circle_btn_style())
            self.watchlist_button.setToolTip("Add to My List")
        if self._item is not None:
            self.watchlist_toggled.emit(self._item, self._in_watchlist)

    def _toggle_like(self) -> None:
        self._liked = not self._liked
        if self._liked:
            self.like_button.setIcon(make_icon("thumbs-up", theme.PRIMARY, 14))
            self.like_button.setStyleSheet(_active_circle_btn_style())
            self.like_button.setToolTip("Liked")
        else:
            self.like_button.setIcon(make_icon("thumbs-up", theme.TEXT_PRIMARY, 14))
            self.like_button.setStyleSheet(_circle_btn_style())
            self.like_button.setToolTip("Like")
        if self._item is not None:
            self.like_toggled.emit(self._item, self._liked)

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
        effect = ScaleFadeEffect(self)
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
        radius = 8.0  # Matches trailer_preview.html border-radius: 8px

        # Multi-layer diffused shadow: 0 12px 32px rgba(0, 0, 0, 0.75)
        painter.setPen(Qt.PenStyle.NoPen)
        for step in range(12, 0, -1):
            grow = step * 1.5
            shadow = QColor(0, 0, 0)
            shadow.setAlphaF(0.038 + (12 - step) * 0.005)
            painter.setBrush(shadow)
            painter.drawRoundedRect(
                card.adjusted(-grow, -grow + 6, grow, grow + 6),
                radius + grow,
                radius + grow,
            )

        # Card background surface
        painter.setClipPath(rounded_path(card, radius))
        painter.fillRect(card, QColor(theme.BG_CARD))

        art = QRectF(card.left(), card.top(), card.width(), IMG_H)

        # 16:9 Media Preview Area (when web video is not active)
        if not self._is_playing:
            if self._backdrop_pixmap is not None and not self._backdrop_pixmap.isNull():
                draw_cover(painter, art, self._backdrop_pixmap, 0.5, 0.15)
            else:
                ground = QLinearGradient(art.topLeft(), art.bottomRight())
                ground.setColorAt(0.0, QColor(theme.BG_ELEVATED))
                ground.setColorAt(1.0, QColor(theme.BG_CARD))
                painter.fillRect(art, ground)

            # Scrim overlay matching trailer_preview.html:
            # linear-gradient(to top, bg_card 0%, rgba(..., 0.35) 35%, transparent 70%)
            scrim = QLinearGradient(art.left(), art.bottom(), art.left(), art.top())
            c_bottom = QColor(theme.BG_CARD)
            c_mid = QColor(theme.BG_CARD)
            c_mid.setAlphaF(0.35)
            c_top = QColor(theme.BG_CARD)
            c_top.setAlphaF(0.0)
            scrim.setColorAt(0.0, c_bottom)
            scrim.setColorAt(0.35, c_mid)
            scrim.setColorAt(0.70, c_top)
            scrim.setColorAt(1.0, c_top)
            painter.fillRect(art, scrim)

            # Official transparent logo overlay in top-left
            if self._logo_pixmap is not None and not self._logo_pixmap.isNull():
                painter.drawPixmap(QPointF(art.left() + 14, art.top() + 12), self._logo_pixmap)
            elif self._item is not None:
                font = painter.font()
                font.setPixelSize(16)
                font.setWeight(QFont.Weight.ExtraBold)
                font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, -0.3)
                painter.setFont(font)
                text = painter.fontMetrics().elidedText(
                    self._item.title.upper(), Qt.TextElideMode.ElideRight, int(art.width() - 80)
                )
                # Drop shadow
                painter.setPen(QColor(0, 0, 0, 240))
                painter.drawText(int(art.left() + 14), int(art.top() + 32) + 1, text)
                painter.setPen(QColor(255, 255, 255))
                painter.drawText(int(art.left() + 14), int(art.top() + 32), text)

            # 6-second circular countdown ring around mute button
            if self._countdown_active and self._countdown_progress > 0:
                center = self.mute_button.geometry().center()
                r = 17.0
                ring_box = QRectF(center.x() - r, center.y() - r, r * 2, r * 2)
                # Background circle
                painter.setPen(QPen(QColor(0, 0, 0, 115), 2))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawEllipse(ring_box)
                # Animated progress arc
                prog_pen = QPen(
                    QColor(theme.PRIMARY),
                    2,
                    Qt.PenStyle.SolidLine,
                    Qt.PenCapStyle.RoundCap,
                )
                painter.setPen(prog_pen)
                start_angle = 90 * 16  # 12 o'clock
                span_angle = int(-360 * 16 * self._countdown_progress)
                painter.drawArc(ring_box, start_angle, span_angle)

        painter.setClipping(False)

        # 1px perimeter border matching trailer_preview.html: 0 0 0 1px rgba(255, 255, 255, 0.08)
        painter.setPen(QPen(QColor(255, 255, 255, 20), 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(rounded_path(card.adjusted(0.5, 0.5, -0.5, -0.5), radius))
        painter.end()
