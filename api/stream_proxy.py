"""Local HTTP bridge between the in-app player and remote streaming CDNs.

The player uses Qt Multimedia's FFmpeg backend. The CDNs behind the providers
expect ``Referer``/``Origin`` headers that a media backend cannot set, some
serve segments with a disguised extension, and a few redirect across hosts.
This small loopback server solves all of those at once:

* it fetches playlists and segments with the headers the CDN expects,
* it rewrites every playlist URL to a local, opaque token URL,
* it keeps a token extension FFmpeg accepts for the resource's real format.

Only URLs registered by :mod:`api.streaming` can be fetched, so the server
cannot be used as an open proxy. It binds to ``127.0.0.1`` on a random port.
"""

from __future__ import annotations

import atexit
import logging
import os
import re
import secrets
import sys
import threading
import time
from collections import OrderedDict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests

log = logging.getLogger(__name__)

MAX_RESOURCES = 6000
TOKEN_RE = re.compile(r"^/s/([0-9a-f]{32})(?:\.[a-z0-9]+)?$")
URI_RE = re.compile(r'URI="([^"]+)"')
CHUNK = 64 * 1024

# FFmpeg's HLS demuxer rejects a segment whose detected format does not match
# the URL extension (a WebVTT cue list served as ``.ts`` fails the whole
# playlist), so token URLs keep the upstream extension whenever it is a real
# media extension and fall back to ``.m3u8``/``.ts`` otherwise.
_PLAYLIST_SUFFIXES = {".m3u8", ".m3u"}
_MEDIA_SUFFIXES = {
    ".ts", ".m4s", ".mp4", ".m4v", ".m4a", ".aac", ".mp3", ".ac3", ".eac3",
    ".vtt", ".webvtt", ".srt", ".ass", ".ssa", ".sub", ".key", ".cmfv", ".cmfa",
}


def _suffix_for(url: str, playlist: bool) -> str:
    """Pick a token extension FFmpeg will accept for ``url``."""
    extension = Path(urlparse(url).path).suffix.lower()
    if playlist:
        return extension if extension in _PLAYLIST_SUFFIXES else ".m3u8"
    return extension if extension in _MEDIA_SUFFIXES else ".ts"


def _prefer_english_audio(text: str) -> str:
    """Make an English audio rendition the default when the provider offers one.

    VixSrc is an Italian service and marks the Italian track ``DEFAULT=YES``.
    HLS players follow that flag, so an English user would otherwise hear
    Italian; every rendition stays available, only the default changes.
    """
    lines = text.splitlines()
    audio = [
        index
        for index, line in enumerate(lines)
        if line.startswith("#EXT-X-MEDIA:TYPE=AUDIO")
    ]
    english = [
        index
        for index in audio
        if re.search(r'(LANGUAGE="eng"|NAME="English")', lines[index], re.IGNORECASE)
    ]
    if not english:
        return text
    preferred = english[0]
    for index in audio:
        line = re.sub(r"DEFAULT=(YES|NO)", "DEFAULT=NO", lines[index], flags=re.IGNORECASE)
        if index == preferred:
            if "DEFAULT=" in line:
                line = re.sub(
                    r"DEFAULT=(YES|NO)", "DEFAULT=YES", line, flags=re.IGNORECASE
                )
            else:
                line += ",DEFAULT=YES"
        lines[index] = line
    return "\n".join(lines)


def _trim_subtitles(text: str) -> str:
    """Keep English (and forced) subtitle renditions when a provider lists many.

    VixSrc advertises around 25 subtitle languages, and FFmpeg downloads every
    rendition playlist while opening the master. That alone doubled start-up
    time, so the untranslated tracks the player cannot surface are dropped.
    """
    lines = text.splitlines()
    subtitles = [
        index
        for index, line in enumerate(lines)
        if line.startswith("#EXT-X-MEDIA:TYPE=SUBTITLES")
    ]
    if len(subtitles) <= 6:
        return text
    keep = {
        index
        for index in subtitles
        if re.search(r'(LANGUAGE="eng"|NAME="English")', lines[index], re.IGNORECASE)
        or "FORCED=YES" in lines[index]
    }
    if not keep:
        return text
    return "\n".join(
        line for index, line in enumerate(lines) if index not in subtitles or index in keep
    )

_LOCAL = threading.local()

#: One shared session, so every worker reuses the same TLS connection pool.
#: Creating a session per request forced a fresh handshake for each playlist
#: and segment, which alone cost several seconds of start-up on provider CDNs.
_SHARED: requests.Session | None = None
_SHARED_LOCK = threading.Lock()


def _session() -> requests.Session:
    """Return the shared session, with no default User-Agent."""
    global _SHARED
    session = _SHARED
    if session is None:
        with _SHARED_LOCK:
            if _SHARED is None:
                session = requests.Session()
                session.headers.clear()
                session.headers["Accept"] = "*/*"
                adapter = requests.adapters.HTTPAdapter(
                    pool_connections=16, pool_maxsize=32
                )
                session.mount("http://", adapter)
                session.mount("https://", adapter)
                _SHARED = session
            session = _SHARED
    return session


class _Resource:
    __slots__ = ("url", "headers")

    def __init__(self, url: str, headers: dict[str, str]) -> None:
        self.url = url
        self.headers = headers


class _ProxyServer(ThreadingHTTPServer):
    """Threaded loopback server that ignores clients hanging up mid-response."""

    daemon_threads = True

    def handle_error(self, request, client_address) -> None:
        error = sys.exc_info()[1]
        if isinstance(
            error, (ConnectionResetError, ConnectionAbortedError, BrokenPipeError)
        ):
            log.debug("Client %s disconnected", client_address)
            return
        super().handle_error(request, client_address)


class StreamProxy:
    """Loopback server that relays remote HLS to the native player."""

    def __init__(self) -> None:
        self._resources: OrderedDict[str, _Resource] = OrderedDict()
        self._lock = threading.Lock()
        self._server: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None

    # ── Lifecycle ───────────────────────────────────────────────────────────
    def start(self) -> str:
        if self._server is not None:
            return self.base_url
        server = _ProxyServer(("127.0.0.1", 0), _Handler)
        server.daemon_threads = True
        server.proxy = self  # type: ignore[attr-defined]
        self._server = server
        self._thread = threading.Thread(
            target=server.serve_forever,
            name="entertainx-stream-proxy",
            daemon=True,
        )
        self._thread.start()
        log.info("Stream proxy listening on %s", self.base_url)
        return self.base_url

    def stop(self) -> None:
        server, self._server = self._server, None
        if server is not None:
            server.shutdown()
            server.server_close()

    @property
    def port(self) -> int:
        return self._server.server_address[1] if self._server else 0

    @property
    def base_url(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    # ── Resource registry ───────────────────────────────────────────────────
    def register(self, url: str, headers: dict[str, str] | None = None) -> str:
        token = secrets.token_hex(16)
        with self._lock:
            self._resources[token] = _Resource(url, dict(headers or {}))
            while len(self._resources) > MAX_RESOURCES:
                self._resources.popitem(last=False)
        return f"{self.base_url}/s/{token}"

    def resource(self, token: str) -> _Resource | None:
        with self._lock:
            resource = self._resources.get(token)
            if resource is not None:
                self._resources.move_to_end(token)
            return resource

    # ── Playlist rewriting ──────────────────────────────────────────────────
    def rewrite_playlist(self, text: str, base_url: str, headers: dict[str, str]) -> str:
        """Point every child playlist/segment/key at a local token URL."""
        master = "#EXT-X-STREAM-INF" in text
        if master:
            text = _prefer_english_audio(text)
            text = _trim_subtitles(text)
        lines: list[str] = []
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped:
                lines.append(line)
                continue
            if stripped.startswith("#"):
                def replace(match: re.Match[str]) -> str:
                    absolute = urljoin(base_url, match.group(1))
                    is_playlist = (
                        master
                        or "EXT-X-MEDIA" in line
                        or "EXT-X-I-FRAME" in line
                    )
                    local = self.register(absolute, headers)
                    return f'URI="{local}{_suffix_for(absolute, is_playlist)}"'

                lines.append(URI_RE.sub(replace, line))
                continue
            absolute = urljoin(base_url, stripped)
            lines.append(
                f"{self.register(absolute, headers)}{_suffix_for(absolute, master)}"
            )
        return "\n".join(lines) + "\n"


class _Handler(BaseHTTPRequestHandler):
    server_version = "EntertainXPlayer"
    protocol_version = "HTTP/1.1"

    @property
    def proxy(self) -> StreamProxy:
        return self.server.proxy  # type: ignore[attr-defined]

    def log_message(self, fmt: str, *args) -> None:  # noqa: A003
        log.debug("proxy: " + fmt, *args)

    # ── Routing ─────────────────────────────────────────────────────────────
    def do_OPTIONS(self) -> None:  # noqa: N802
        self.send_response(204)
        self._cors()
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        match = TOKEN_RE.match(path)
        if match:
            self._serve_resource(match.group(1))
            return
        self._plain(404, b"Not found")

    # ── Proxying ────────────────────────────────────────────────────────────
    def _serve_resource(self, token: str) -> None:
        resource = self.proxy.resource(token)
        if resource is None:
            self._plain(410, b"Stream link expired")
            return

        headers = dict(resource.headers)
        headers["Accept-Encoding"] = "identity"
        range_header = self.headers.get("Range")
        if range_header:
            headers["Range"] = range_header

        started = time.perf_counter()
        try:
            upstream = _session().get(
                resource.url,
                headers=headers,
                stream=True,
                allow_redirects=True,
                timeout=(8, 40),
            )
        except requests.RequestException as exc:
            log.info("Upstream fetch failed: %s", exc)
            self._plain(502, b"Stream unavailable")
            return
        elapsed_ms = (time.perf_counter() - started) * 1000

        log.debug(
            "Proxy fetch %s%s -> %s in %.0f ms",
            urlparse(resource.url).netloc,
            urlparse(resource.url).path,
            upstream.status_code,
            elapsed_ms,
        )
        try:
            if upstream.status_code >= 400:
                log.info(
                    "Upstream %s returned HTTP %s",
                    urlparse(resource.url).netloc,
                    upstream.status_code,
                )
                self._plain(502, b"Stream unavailable")
                return

            content_type = (upstream.headers.get("Content-Type") or "").lower()
            playlist = "mpegurl" in content_type or urlparse(
                resource.url
            ).path.lower().endswith(".m3u8")
            if playlist:
                self._send_playlist(upstream, resource, headers)
            else:
                self._send_binary(upstream)
        finally:
            upstream.close()

    def _send_playlist(
        self,
        upstream: requests.Response,
        resource: _Resource,
        headers: dict[str, str],
    ) -> None:
        try:
            text = upstream.content.decode(upstream.encoding or "utf-8", "replace")
        except (LookupError, UnicodeDecodeError):
            text = upstream.content.decode("utf-8", "replace")
        if "#EXTM3U" not in text:
            self._plain(502, b"Stream unavailable")
            return
        rewritten = self.proxy.rewrite_playlist(text, upstream.url, resource.headers)
        body = rewritten.encode("utf-8")
        self.send_response(200)
        self._cors()
        self.send_header("Content-Type", "application/vnd.apple.mpegurl")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self._write(body)

    def _send_binary(self, upstream: requests.Response) -> None:
        self.send_response(upstream.status_code)
        self._cors()
        for header in (
            "Content-Type",
            "Content-Length",
            "Content-Range",
            "Accept-Ranges",
        ):
            value = upstream.headers.get(header)
            if value:
                self.send_header(header, value)
        self.send_header("Cache-Control", "private, max-age=120")
        if not upstream.headers.get("Content-Length"):
            self.send_header("Connection", "close")
            self.close_connection = True
        self.end_headers()
        try:
            for chunk in upstream.iter_content(CHUNK):
                if chunk:
                    self.wfile.write(chunk)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass

    # ── Helpers ─────────────────────────────────────────────────────────────
    def _cors(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")

    def _plain(self, status: int, body: bytes) -> None:
        self.send_response(status)
        self._cors()
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self._write(body)

    def _write(self, body: bytes) -> bool:
        try:
            self.wfile.write(body)
            return True
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            self.close_connection = True
            return False


_proxy: StreamProxy | None = None
_proxy_lock = threading.Lock()


def get_proxy() -> StreamProxy:
    """Return the process-wide proxy, starting it on first use."""
    global _proxy
    with _proxy_lock:
        if _proxy is None:
            _proxy = StreamProxy()
            _proxy.start()
            atexit.register(_proxy.stop)
        return _proxy


__all__ = ["StreamProxy", "get_proxy"]
