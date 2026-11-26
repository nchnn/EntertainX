"""Inline movie / TV player view.

Hosts ui/web/player.html in a QWebEngineView so playback happens inside the
app window (no popups, no new windows).  BrowsePage swaps this widget in for
the browse view and swaps back when `back_requested` fires.

Payload keys: title, year, runtime, rating, synopsis, backdrop,
type ("movie" | "tv"), servers [{name, url}], plus optional tmdbId, season,
episode, episodes [{season, episode, title}], stars.
"""
from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import QUrl, Signal
from PySide6.QtWidgets import QLabel, QStackedLayout, QWidget

try:
    from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineSettings
    from PySide6.QtWebEngineWidgets import QWebEngineView
    HAVE_WEBENGINE = True
except ImportError:  # graceful degradation, same as TrailerDialog
    HAVE_WEBENGINE = False

PLAYER_HTML = Path(__file__).resolve().parent.parent / "web" / "player.html"


class VideoPlayerView(QWidget):
    back_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._pending: dict | None = None
        self._loaded = False
        self._was_fullscreen = False
        layout = QStackedLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        if not HAVE_WEBENGINE:
            msg = QLabel("The video player needs PySide6 WebEngine.\nInstall it and restart EntertainX.")
            msg.setStyleSheet("color:#f2efe9;background:#07070a;")
            layout.addWidget(msg)
            self._view = None
            return

        self._view = QWebEngineView(self)
        s = self._view.settings()
        s.setAttribute(QWebEngineSettings.WebAttribute.PlaybackRequiresUserGesture, False)
        s.setAttribute(QWebEngineSettings.WebAttribute.FullScreenSupportEnabled, True)
        s.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        page = self._view.page()
        page.fullScreenRequested.connect(self._on_fullscreen)
        self._view.urlChanged.connect(self._on_url_changed)
        self._view.loadFinished.connect(self._on_loaded)
        layout.addWidget(self._view)
        self._view.load(QUrl.fromLocalFile(str(PLAYER_HTML)))

    # ── public API ──────────────────────────────────────────────────────
    def play(self, payload: dict) -> None:
        """Show the player for a title. Safe to call before the page finished loading."""
        if self._view is None:
            return
        self._pending = payload
        if self._loaded:
            self._flush()

    def stop(self) -> None:
        if self._view is not None and self._loaded:
            self._view.page().runJavaScript("window.EntertainXPlayer && EntertainXPlayer.stop()")

    # ── internals ───────────────────────────────────────────────────────
    def _flush(self) -> None:
        if self._pending is None:
            return
        data = json.dumps(self._pending).replace("</", "<\\/")
        self._view.page().runJavaScript(f"EntertainXPlayer.load({data})")
        self._pending = None

    def _on_loaded(self, ok: bool) -> None:
        self._loaded = ok
        if ok:
            self._flush()

    def _on_url_changed(self, url: QUrl) -> None:
        if url.fragment() == "back":
            self._view.page().runJavaScript("history.replaceState(null, '', location.pathname)")
            self.stop()
            self.back_requested.emit()

    def _on_fullscreen(self, request) -> None:
        request.accept()
        win = self.window()
        if request.toggleOn():
            self._was_fullscreen = win.isFullScreen()
            win.showFullScreen()
        elif not self._was_fullscreen:
            win.showNormal()


# ── Payload helpers ─────────────────────────────────────────────────────────
import os


def configured_servers() -> list[dict]:
    """Servers you are licensed to stream from, read from the environment.

    Set ENTERTAINX_STREAM_SERVERS to a JSON list, e.g.
      [{"name": "Main 1", "url": "https://cdn.example.com/movie/{id}/index.m3u8"},
       {"name": "Main 2", "url": "https://backup.example.com/{id}.mp4"}]
    URL templates may use {id} (TMDB id), {s} (season) and {e} (episode).
    Returns [] when unset, in which case callers should keep the trailer flow.
    """
    raw = os.environ.get("ENTERTAINX_STREAM_SERVERS", "").strip()
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except ValueError:
        return []
    return [
        {"name": str(s.get("name") or f"Main {i + 1}"), "url": str(s.get("url") or "")}
        for i, s in enumerate(data)
        if isinstance(s, dict)
    ]


def build_payload(item, details, servers: list[dict], episodes: list[dict] | None = None) -> dict:
    """Translate MediaItem + MediaDetails into the player's input payload."""
    backdrop = (
        details.backdrop_url("w1280") or item.backdrop_url("w1280") or item.poster_url("w780")
    )
    rating = round(float(item.rating or 0.0), 1)
    return {
        "title": item.title,
        "year": item.year,
        "runtime": details.runtime_text,
        "rating": details.certification or "",
        "stars": rating or None,
        "synopsis": item.overview or "No synopsis is available for this title yet.",
        "backdrop": backdrop,
        "type": "tv" if item.media_type == "tv" else "movie",
        "tmdbId": item.id,
        "servers": servers,
        "season": 1,
        "episode": 1,
        "episodes": episodes or [],
        "seasons": [
            {"number": s.number, "name": s.name, "episodeCount": s.episode_count}
            for s in (getattr(details, "seasons", None) or [])
            if s.number > 0
        ],
    }
