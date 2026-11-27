"""Offline tests for provider resolution and the loopback stream proxy."""

from __future__ import annotations

import base64
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from Crypto.Cipher import AES

from api import streaming
from api.stream_proxy import StreamProxy


# ── VidRock payload decryption ──────────────────────────────────────────────
def _encrypt(url: str) -> str:
    nonce = b"0123456789ab"
    cipher = AES.new(streaming.VIDROCK_KEY, AES.MODE_GCM, nonce=nonce)
    sealed, tag = cipher.encrypt_and_digest(url.encode("utf-8"))
    return base64.urlsafe_b64encode(nonce + sealed + tag).decode("ascii").rstrip("=")


def test_decrypt_vidrock_round_trip():
    url = "https://cdn.example.com/movie/550/master.m3u8?token=abc"
    assert streaming.decrypt_vidrock_url(_encrypt(url)) == url


def test_decrypt_rejects_payload_that_is_not_a_url():
    with pytest.raises(streaming.StreamError):
        streaming.decrypt_vidrock_url(_encrypt("not-a-url"))


def test_decrypt_rejects_empty_payload():
    with pytest.raises(streaming.StreamError):
        streaming.decrypt_vidrock_url("")


def test_parse_payload_skips_unreadable_mirrors():
    payload = {
        "Nova": {"url": _encrypt("https://cdn.example/nova.m3u8")},
        "Broken": {"url": "!!!not-base64!!!"},
        "Missing": {},
    }
    assert streaming.parse_vidrock_payload(payload) == [
        ("Nova", "https://cdn.example/nova.m3u8")
    ]


# ── Provider dispatch ───────────────────────────────────────────────────────
def test_servers_payload_matches_configured_servers():
    assert streaming.servers_payload() == [
        {"id": s.id, "name": s.name, "quality": s.quality} for s in streaming.SERVERS
    ]


def test_resolve_forwards_tv_season_and_episode(monkeypatch):
    seen: dict = {}

    def fake_vidrock(tmdb_id, season=None, episode=None):
        seen.update(id=tmdb_id, season=season, episode=episode)
        return [streaming.StreamSource("https://cdn/x.m3u8", "Nova")]

    monkeypatch.setattr(streaming, "resolve_vidrock", fake_vidrock)
    sources = streaming.resolve("main-1", "tv", 1399, 2, 3)
    assert seen == {"id": 1399, "season": 2, "episode": 3}
    assert [source.label for source in sources] == ["Nova"]


def test_resolve_drops_season_for_movies(monkeypatch):
    seen: dict = {}

    def fake_vixsrc(tmdb_id, season=None, episode=None):
        seen.update(id=tmdb_id, season=season, episode=episode)
        return [streaming.StreamSource("https://cdn/x.m3u8", "VixSrc")]

    monkeypatch.setattr(streaming, "resolve_vixsrc", fake_vixsrc)
    streaming.resolve("main-2", "movie", 550, 4, 5)
    assert seen == {"id": 550, "season": None, "episode": None}


def test_resolve_unknown_server_is_safe_to_display():
    with pytest.raises(streaming.StreamError, match="not available"):
        streaming.resolve("nope", "movie", 550)


def test_resolve_hides_unexpected_provider_errors(monkeypatch):
    def boom(*_args, **_kwargs):
        raise RuntimeError("internal provider detail")

    monkeypatch.setattr(streaming, "resolve_vidrock", boom)
    with pytest.raises(streaming.StreamError) as caught:
        streaming.resolve("main-1", "movie", 550)
    assert "internal provider detail" not in str(caught.value)


def test_resolve_reports_when_every_mirror_is_dead(monkeypatch):
    monkeypatch.setattr(streaming, "resolve_vidrock", lambda *a, **k: [])
    with pytest.raises(streaming.StreamError, match="No video source"):
        streaming.resolve("main-1", "movie", 550)


# ── Playlist rewriting ──────────────────────────────────────────────────────
def test_rewrite_master_playlist_points_children_at_tokens():
    proxy = StreamProxy()
    text = (
        "#EXTM3U\n"
        "#EXT-X-STREAM-INF:BANDWIDTH=800000,RESOLUTION=1280x720\n"
        "720/index.m3u8\n"
        "#EXT-X-MEDIA:TYPE=AUDIO,GROUP-ID=\"aud\",URI=\"audio/en.m3u8\"\n"
    )
    rewritten = proxy.rewrite_playlist(text, "https://cdn.example/show/master.m3u8", {})
    assert "https://cdn.example" not in rewritten
    assert "/s/" in rewritten
    assert rewritten.count(".m3u8") == 2
    assert "720/index.m3u8" not in rewritten


def test_rewrite_media_playlist_points_segments_at_tokens():
    proxy = StreamProxy()
    text = (
        "#EXTM3U\n"
        "#EXT-X-KEY:METHOD=AES-128,URI=\"key.bin\"\n"
        "#EXTINF:4.0,\n"
        "seg-1.jpg\n"
        "#EXTINF:4.0,\n"
        "seg-2.jpg\n"
    )
    rewritten = proxy.rewrite_playlist(text, "https://cdn.example/v/index.m3u8", {})
    assert rewritten.count("/s/") == 3
    assert "seg-1.jpg" not in rewritten
    assert 'URI="' in rewritten


def test_rewrite_keeps_webvtt_extension_for_subtitle_segments():
    """FFmpeg rejects a WebVTT cue list whose URL claims to be a .ts segment."""
    proxy = StreamProxy()
    text = "#EXTM3U\n#EXTINF:3162.5,\nsubs-0000.vtt\n#EXT-X-ENDLIST\n"
    rewritten = proxy.rewrite_playlist(text, "https://cdn.example/s/index.m3u8", {})
    segment = [line for line in rewritten.splitlines() if line.startswith("http")][0]
    assert segment.endswith(".vtt")


def test_rewrite_keeps_key_and_init_segment_extensions():
    proxy = StreamProxy()
    text = (
        "#EXTM3U\n"
        '#EXT-X-KEY:METHOD=AES-128,URI="enc.key"\n'
        '#EXT-X-MAP:URI="init.mp4"\n'
        "#EXTINF:4.0,\n"
        "seg.m4s\n"
    )
    rewritten = proxy.rewrite_playlist(text, "https://cdn.example/v/index.m3u8", {})
    assert '.key"' in rewritten
    assert '.mp4"' in rewritten
    assert rewritten.rstrip().endswith(".m4s")


def test_rewrite_master_prefers_english_audio():
    proxy = StreamProxy()
    text = (
        "#EXTM3U\n"
        '#EXT-X-MEDIA:TYPE=AUDIO,GROUP-ID="audio",NAME="Italian",'
        'DEFAULT=YES,AUTOSELECT=YES,LANGUAGE="ita",URI="ita.m3u8"\n'
        '#EXT-X-MEDIA:TYPE=AUDIO,GROUP-ID="audio",NAME="English",'
        'DEFAULT=NO,AUTOSELECT=NO,LANGUAGE="eng",URI="eng.m3u8"\n'
        '#EXT-X-STREAM-INF:BANDWIDTH=800000,AUDIO="audio"\n'
        "variant.m3u8\n"
    )
    rewritten = proxy.rewrite_playlist(text, "https://cdn.example/master.m3u8", {})
    italian = next(line for line in rewritten.splitlines() if "Italian" in line)
    english = next(line for line in rewritten.splitlines() if "English" in line)
    assert "DEFAULT=NO" in italian
    assert "DEFAULT=YES" in english


def test_registered_resource_keeps_source_headers():
    proxy = StreamProxy()
    token_url = proxy.register("https://cdn.example/a.m3u8", {"Referer": "https://x/"})
    token = token_url.rsplit("/", 1)[-1]
    resource = proxy.resource(token)
    assert resource is not None
    assert resource.headers == {"Referer": "https://x/"}


# ── Loopback proxy end to end ───────────────────────────────────────────────
class _Upstream(BaseHTTPRequestHandler):
    seen_headers: list[dict] = []

    def log_message(self, *_args):  # silence the test server
        pass

    def do_GET(self):  # noqa: N802
        _Upstream.seen_headers.append(dict(self.headers))
        if self.path == "/master.m3u8":
            body = (
                b"#EXTM3U\n"
                b"#EXT-X-STREAM-INF:BANDWIDTH=800000\n"
                b"variant.m3u8\n"
            )
            content_type = "application/vnd.apple.mpegurl"
        elif self.path == "/variant.m3u8":
            body = b"#EXTM3U\n#EXTINF:4.0,\nseg.ts\n"
            content_type = "application/vnd.apple.mpegurl"
        elif self.path == "/seg.ts":
            body = b"SEGMENT-BYTES"
            content_type = "video/mp2t"
        else:
            self.send_response(404)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


@pytest.fixture()
def proxy():
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Upstream)
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    proxy = StreamProxy()
    base = proxy.start()
    try:
        yield proxy, base, f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        proxy.stop()
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def _get(url: str, **kwargs):
    import requests

    return requests.get(url, timeout=10, **kwargs)


def test_proxy_serves_and_rewrites_a_real_playlist(proxy):
    stream_proxy, base, upstream = proxy
    local = stream_proxy.register(upstream + "/master.m3u8", {"Referer": "https://origin/"})
    response = _get(local + ".m3u8")
    assert response.status_code == 200
    assert "#EXTM3U" in response.text
    assert upstream not in response.text

    variant_line = next(
        line for line in response.text.splitlines() if line and not line.startswith("#")
    )
    variant = _get(base + variant_line.removeprefix(base))
    assert variant.status_code == 200
    segment_line = next(
        line for line in variant.text.splitlines() if line and not line.startswith("#")
    )
    segment = _get(base + segment_line.removeprefix(base))
    assert segment.content == b"SEGMENT-BYTES"


def test_proxy_forwards_source_headers(proxy):
    stream_proxy, base, upstream = proxy
    _Upstream.seen_headers.clear()
    local = stream_proxy.register(upstream + "/seg.ts", {"Referer": "https://origin/"})
    assert _get(local + ".ts").content == b"SEGMENT-BYTES"
    assert any(
        headers.get("Referer") == "https://origin/" for headers in _Upstream.seen_headers
    )


def test_proxy_refuses_unregistered_tokens(proxy):
    _stream_proxy, base, _upstream = proxy
    assert _get(base + "/s/" + "0" * 32 + ".m3u8").status_code == 410
