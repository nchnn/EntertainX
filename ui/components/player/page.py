"""In-app movie and TV player.

The picture is a self-contained HTML5 player (hls.js + a native ``<video>``)
running in a ``QWebEngineView``. Python resolves provider URLs, proxies the
stream through a loopback server, and feeds the web layer over ``QWebChannel``.
Nothing opens a second window: the page is an overlay inside the main window.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from PySide6.QtCore import QObject, Qt, QUrl, Signal, Slot
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineCore import (
    QWebEnginePage,
    QWebEngineProfile,
    QWebEngineSettings,
)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QVBoxLayout, QWidget

from api import streaming
from api.movies import MediaDetails, MediaItem, TmdbClient
from api.stream_proxy import get_proxy
from api.tasks import run_async

log = logging.getLogger(__name__)


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


class _PlayerPage(QWebEnginePage):
    """Web page that cannot open popups and reports console output to Python."""

    def createWindow(self, _type) -> None:  # type: ignore[override]
        return None

    def javaScriptConsoleMessage(  # noqa: N802
        self, level, message: str, line: int, source: str
    ) -> None:
        log.debug("player js %s:%s %s", source, line, message)

    def featurePermissionRequested(self, origin: QUrl, feature) -> None:  # noqa: N802
        self.setFeaturePermission(
            origin, feature, QWebEnginePage.PermissionPolicy.PermissionDeniedByUser
        )


class _Bridge(QObject):
    """Objects and signals exposed to the web player as ``bridge``."""

    sourceReady = Signal(str)
    sourceFailed = Signal(str, str)
    episodesReady = Signal(str)

    def __init__(self, page: PlaybackPage) -> None:
        super().__init__(page)
        self._page = page

    @Slot(result=str)
    def payload(self) -> str:
        return json.dumps(self._page.payload, ensure_ascii=False)

    @Slot(str, str, int, int, int)
    def requestSource(
        self,
        server_id: str,
        media_type: str,
        tmdb_id: int,
        season: int,
        episode: int,
    ) -> None:
        self._page.request_source(server_id, media_type, tmdb_id, season, episode)

    @Slot(int)
    def requestEpisodes(self, season: int) -> None:
        self._page.request_episodes(season)

    @Slot(str, str)
    def reportPlaybackError(self, server_id: str, detail: str) -> None:
        log.info("Playback failed on %s: %s", server_id, detail)

    @Slot()
    def back(self) -> None:
        self._page.close_player()


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
        self.setStyleSheet("background-color: #050506;")

        self._provider = provider if provider is not None else TmdbClient()
        self._view: QWebEngineView | None = None
        self._page: _PlayerPage | None = None
        self._bridge: _Bridge | None = None
        self._channel: QWebChannel | None = None

        self._item: MediaItem | None = None
        self._details: MediaDetails | None = None
        self._payload: dict[str, Any] = {}
        self._season = 1
        self._episode = 1
        self._active = False
        self._request_id = 0
        self._episode_cache: dict[int, list[dict[str, Any]]] = {}
        self._was_maximized = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

    # ── Public API ──────────────────────────────────────────────────────────
    @property
    def payload(self) -> dict[str, Any]:
        return self._payload

    @property
    def web_view(self) -> QWebEngineView | None:
        return self._view

    def open(self, item: MediaItem, details: MediaDetails) -> None:
        self._item = item
        self._details = details
        self._season = 1
        self._episode = 1
        self._episode_cache.clear()
        self._request_id += 1
        self._payload = self._build_payload(item, details)
        self._active = True

        self._ensure_view()
        self.show()
        self.raise_()
        self.setFocus()
        if self._view is not None:
            self._view.setFocus()
            self._view.setUrl(QUrl(get_proxy().player_url()))

    def close_player(self) -> None:
        if not self._active:
            return
        self._active = False
        self._request_id += 1
        self._episode_cache.clear()
        if self._view is not None:
            self._view.setUrl(QUrl("about:blank"))
        self.hide()
        self.closed.emit()

    # ── Payload ─────────────────────────────────────────────────────────────
    def _build_payload(self, item: MediaItem, details: MediaDetails) -> dict[str, Any]:
        backdrop = (
            details.backdrop_url("w1280")
            or item.backdrop_url("w1280")
            or item.poster_url("w780")
        )
        return {
            "title": item.title,
            "year": item.year,
            "runtime": details.runtime_text,
            "rating": round(float(item.rating or 0.0), 1),
            "certification": details.certification,
            "synopsis": item.overview
            or "No synopsis is available for this title yet.",
            "tagline": details.tagline,
            "backdrop": backdrop,
            "type": item.media_type,
            "tmdbId": item.id,
            "servers": streaming.servers_payload(),
            "seasons": [
                {
                    "number": season.number,
                    "name": season.name,
                    "episodeCount": season.episode_count,
                }
                for season in details.seasons
            ],
            "season": 1,
            "episode": 1,
        }

    # ── Chromium surface ────────────────────────────────────────────────────
    def _ensure_view(self) -> None:
        if self._view is not None:
            return

        profile = QWebEngineProfile(self)
        profile.setHttpCacheType(QWebEngineProfile.HttpCacheType.MemoryHttpCache)
        profile.setPersistentCookiesPolicy(
            QWebEngineProfile.PersistentCookiesPolicy.NoPersistentCookies
        )

        page = _PlayerPage(profile, self)
        settings = page.settings()
        on = QWebEngineSettings.WebAttribute
        settings.setAttribute(on.JavascriptEnabled, True)
        settings.setAttribute(on.PlaybackRequiresUserGesture, False)
        settings.setAttribute(on.FullScreenSupportEnabled, True)
        settings.setAttribute(on.LocalStorageEnabled, True)
        settings.setAttribute(on.JavascriptCanOpenWindows, False)
        settings.setAttribute(on.LinksIncludedInFocusChain, False)
        page.fullScreenRequested.connect(self._on_fullscreen_requested)

        view = QWebEngineView(self)
        view.setPage(page)
        view.setContextMenuPolicy(__import__("PySide6").QtCore.Qt.ContextMenuPolicy.NoContextMenu)
        view.loadFinished.connect(self._on_load_finished)

        bridge = _Bridge(self)
        channel = QWebChannel(page)
        channel.registerObject("bridge", bridge)
        page.setWebChannel(channel)

        layout = self.layout()
        if layout is not None:
            layout.addWidget(view)

        self._profile = profile
        self._page = page
        self._view = view
        self._bridge = bridge
        self._channel = channel

    def _on_load_finished(self, ok: bool) -> None:
        if not ok:
            log.warning("Player page failed to load")
            return
        if self._view is not None:
            self._view.setFocus()

    def _on_fullscreen_requested(self, request) -> None:
        request.accept()
        self._apply_window_fullscreen(bool(request.toggleOn()))

    def _apply_window_fullscreen(self, on: bool) -> None:
        window = self.window()
        if window is None:
            return
        if on:
            self._was_maximized = window.isMaximized()
            window.showFullScreen()
        else:
            if self._was_maximized:
                window.showMaximized()
            else:
                window.showNormal()

    # ── Stream resolution ───────────────────────────────────────────────────
    def request_source(
        self,
        server_id: str,
        media_type: str,
        tmdb_id: int,
        season: int,
        episode: int,
    ) -> None:
        if not self._active or self._bridge is None:
            return
        self._request_id += 1
        request_id = self._request_id
        is_tv = media_type == "tv"
        season_arg = season if is_tv and season > 0 else None
        episode_arg = episode if is_tv and episode > 0 else None

        run_async(
            _resolve_sources,
            server_id,
            media_type,
            tmdb_id,
            season_arg,
            episode_arg,
            on_done=lambda candidates: self._deliver_sources(
                request_id, server_id, candidates
            ),
            on_error=lambda error: self._deliver_failure(
                request_id, server_id, error
            ),
            owner=self,
        )

    def _deliver_sources(
        self, request_id: int, server_id: str, candidates: list[dict[str, str]]
    ) -> None:
        if request_id != self._request_id or not self._active or self._bridge is None:
            return
        self._bridge.sourceReady.emit(
            json.dumps(
                {"serverId": server_id, "candidates": candidates},
                ensure_ascii=False,
            )
        )

    def _deliver_failure(
        self, request_id: int, server_id: str, error: Exception
    ) -> None:
        if request_id != self._request_id or not self._active or self._bridge is None:
            return
        log.info("Server %s could not resolve a stream: %s", server_id, error)
        self._bridge.sourceFailed.emit(
            server_id, "No video source found for this title."
        )

    # ── Episodes ────────────────────────────────────────────────────────────
    def request_episodes(self, season: int) -> None:
        if not self._active or self._bridge is None or self._item is None:
            return
        if self._item.media_type != "tv":
            return
        cached = self._episode_cache.get(season)
        if cached is not None:
            self._emit_episodes(season, cached)
            return
        run_async(
            self._provider.episodes,
            self._item.id,
            season,
            on_done=lambda episodes: self._on_episodes(season, episodes),
            on_error=lambda error: self._on_episodes_failed(season, error),
            owner=self,
        )

    def _on_episodes(self, season: int, episodes) -> None:
        if not self._active or self._bridge is None:
            return
        payload = [
            {
                "number": episode.number,
                "name": episode.name,
                "runtime": episode.runtime,
                "airDate": episode.air_date,
                "still": episode.still_url,
            }
            for episode in episodes
        ]
        self._episode_cache[season] = payload
        self._emit_episodes(season, payload)

    def _on_episodes_failed(self, season: int, error: Exception) -> None:
        log.info("Episode list unavailable for season %s: %s", season, error)
        self._episode_cache[season] = []
        self._emit_episodes(season, [])

    def _emit_episodes(self, season: int, episodes: list[dict[str, Any]]) -> None:
        if not self._active or self._bridge is None:
            return
        self._bridge.episodesReady.emit(
            json.dumps({"season": season, "episodes": episodes}, ensure_ascii=False)
        )


__all__ = ["PlaybackPage"]
