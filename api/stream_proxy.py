"""Local HTTP bridge between the web player and remote streaming CDNs.

The player runs inside ``QWebEngineView``. Chromium enforces CORS and blocks
mixed content, and the CDNs behind the providers expect ``Referer``/``Origin``
headers that a page is not allowed to set. This small loopback server solves
all three problems at once:

* it serves the player page and its assets from the same origin,
* it fetches playlists and segments with the headers the CDN expects,
* it rewrites every playlist URL to a local, opaque token URL.

Only URLs registered by :mod:`api.streaming` can be fetched, so the server
cannot be used as an open proxy. It binds to ``127.0.0.1`` on a random port.
"""

from __future__ import annotations

import atexit
import logging
import mimetypes
import os
import re
import secrets
import threading
from collections import OrderedDict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urljoin, urlparse

import requests

log = logging.getLogger(__name__)

WEB_ROOT = Path(__file__).resolve().parents[1] / "ui" / "components" / "player" / "web"
ICON_ROOT = Path(__file__).resolve().parents[1] / "assets" / "icons"

MAX_RESOURCES = 6000
TOKEN_RE = re.compile(r"^/s/([0-9a-f]{32})(?:\.[a-z0-9]+)?$")
URI_RE = re.compile(r'URI="([^"]+)"')
CHUNK = 64 * 1024

_LOCAL = threading.local()


def _session() -> requests.Session:
    """One keep-alive session per worker thread, with no default User-Agent."""
    session = getattr(_LOCAL, "session", None)
    if session is None:
        session = requests.Session()
        session.headers.clear()
        session.headers["Accept"] = "*/*"
        _LOCAL.session = session
    return session


class _Resource:
    __slots__ = ("url", "headers")

    def __init__(self, url: str, headers: dict[str, str]) -> None:
        self.url = url
        self.headers = headers


class StreamProxy:
    """Loopback server that plays remote HLS through the in-app browser."""

    def __init__(self, web_root: Path | None = None, icon_root: Path | None = None) -> None:
        self._web_root = web_root or WEB_ROOT
        self._icon_root = icon_root or ICON_ROOT
        self._resources: OrderedDict[str, _Resource] = OrderedDict()
        self._lock = threading.Lock()
        self._server: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None

    # ── Lifecycle ───────────────────────────────────────────────────────────
    def start(self) -> str:
        if self._server is not None:
            return self.base_url
        server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
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

    def player_url(self) -> str:
        return f"{self.base_url}/player"

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
                    return f'URI="{local}{".m3u8" if is_playlist else ".ts"}"'

                lines.append(URI_RE.sub(replace, line))
                continue
            absolute = urljoin(base_url, stripped)
            suffix = ".m3u8" if master else ".ts"
            lines.append(f"{self.register(absolute, headers)}{suffix}")
        return "\n".join(lines) + "\n"

    # ── Static files ────────────────────────────────────────────────────────
    def static_file(self, root: Path, relative: str) -> Path | None:
        candidate = (root / unquote(relative)).resolve()
        try:
            candidate.relative_to(root.resolve())
        except ValueError:
            return None
        return candidate if candidate.is_file() else None


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
        if path in ("/", "/player", "/player/"):
            self._serve_static(self.proxy._web_root, "index.html")
            return
        if path.startswith("/assets/"):
            self._serve_static(self.proxy._web_root, path[len("/assets/"):])
            return
        if path.startswith("/icons/"):
            self._serve_static(self.proxy._icon_root, path[len("/icons/"):])
            return
        if path == "/favicon.ico":
            self.send_response(204)
            self._cors()
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        match = TOKEN_RE.match(path)
        if match:
            self._serve_resource(match.group(1))
            return
        self._plain(404, b"Not found")

    # ── Static ──────────────────────────────────────────────────────────────
    def _serve_static(self, root: Path, relative: str) -> None:
        target = self.proxy.static_file(root, relative)
        if target is None:
            self._plain(404, b"Not found")
            return
        try:
            body = target.read_bytes()
        except OSError:
            self._plain(404, b"Not found")
            return
        content_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        if target.suffix == ".svg":
            content_type = "image/svg+xml"
        self.send_response(200)
        self._cors()
        self.send_header("Content-Type", f"{content_type}; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(body)

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
        self.wfile.write(body)

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
        except (BrokenPipeError, ConnectionResetError):
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
        self.wfile.write(body)


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


def player_url() -> str:
    return get_proxy().player_url()


__all__ = ["StreamProxy", "get_proxy", "player_url"]
