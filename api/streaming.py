"""Direct video source resolution for the in-app movie and TV player.

The player never talks to a third-party site directly. This module turns a
TMDB id (plus season/episode for TV) into one or more playable HLS/MP4 URLs,
using the provider flows documented in ``STREAMING_SOURCES.md``:

* **VidRock** -- encrypted CDN mirrors (Nova, Astra, Lyra, ...), decrypted with
  AES-256-GCM.
* **VixSrc** -- a signed HLS master playlist.

Everything here is provider-specific and network-bound, so the UI only calls
:func:`resolve` from a worker thread and receives :class:`StreamSource` values.
Failures raise :class:`StreamError` with a message that is safe to display.
"""

from __future__ import annotations

import base64
import json
import logging
import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

import requests
from Crypto.Cipher import AES

log = logging.getLogger(__name__)

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
VIDROCK_HOSTS = ("https://vidrock.to", "https://vidrock.net")
VIDROCK_KEY = bytes.fromhex(
    "7f3e9c2a8b5d1f4e6a9c3b7d2e5f8a1c4b6d9e2f5a8c1b4d7e9f2a5c8b1d4e7f"
)
VIXSRC_HOST = "https://vixsrc.to"
REQUEST_TIMEOUT = (5, 12)
PREFLIGHT_TIMEOUT = (4, 7)


class StreamError(Exception):
    """No playable source was found; the message is safe to show."""


@dataclass(frozen=True)
class StreamServer:
    """One entry in the player's SERVER dropdown."""

    id: str
    name: str
    provider: str
    quality: str = "HD"


#: Ordered failover list. Add or reorder providers here and the player UI
#: follows automatically (the web layer receives this list at start-up).
SERVERS: tuple[StreamServer, ...] = (
    StreamServer("main-1", "Main 1", "vidrock"),
    StreamServer("main-2", "Main 2", "vixsrc"),
)


@dataclass(frozen=True)
class StreamSource:
    """A playable URL plus the headers its CDN expects."""

    url: str
    label: str
    language: str = "English"
    kind: str = "hls"
    headers: tuple[tuple[str, str], ...] = ()

    def header_dict(self) -> dict[str, str]:
        return dict(self.headers)


# ── Session helpers ─────────────────────────────────────────────────────────
def _session() -> requests.Session:
    """A session with no default User-Agent.

    Several VidRock CDNs reject requests that carry one, so the header is set
    per source instead of globally.
    """
    session = requests.Session()
    session.headers.clear()
    session.headers["Accept"] = "*/*"
    return session


def servers_payload() -> list[dict]:
    """The server list the web player renders in its dropdowns."""
    return [
        {"id": s.id, "name": s.name, "quality": s.quality}
        for s in SERVERS
    ]


# ── VidRock (AES-256-GCM) ───────────────────────────────────────────────────
def decrypt_vidrock_url(cipher_b64: str) -> str:
    """Decrypt one VidRock payload into a direct ``.m3u8`` URL."""
    if not cipher_b64 or len(cipher_b64) < 28:
        raise StreamError("Empty stream payload.")
    encoded = cipher_b64.replace("-", "+").replace("_", "/")
    encoded += "=" * ((4 - len(encoded) % 4) % 4)
    raw = base64.b64decode(encoded)
    if len(raw) < 29:
        raise StreamError("Stream payload is too short.")
    iv, sealed = raw[:12], raw[12:]
    cipher = AES.new(VIDROCK_KEY, AES.MODE_GCM, nonce=iv)
    plain = cipher.decrypt_and_verify(sealed[:-16], sealed[-16:])
    url = plain.decode("utf-8").strip()
    if not url.startswith(("http://", "https://")):
        raise StreamError("Stream payload did not contain a URL.")
    return url


def _vidrock_api(tmdb_id: int, season: int | None, episode: int | None) -> dict:
    if season is not None and episode is not None:
        path = f"/api/tv/{tmdb_id}/{season}/{episode}"
    else:
        path = f"/api/movie/{tmdb_id}"
    headers = {"Referer": "https://vidrock.to/", "Origin": "https://vidrock.to"}
    last_error: Exception | None = None
    for host in VIDROCK_HOSTS:
        try:
            response = _session().get(
                host + path, headers=headers, timeout=REQUEST_TIMEOUT
            )
            if response.status_code == 404:
                continue
            response.raise_for_status()
            payload = response.json()
            if isinstance(payload, dict):
                return payload
        except (requests.RequestException, ValueError) as exc:
            last_error = exc
            log.info("VidRock mirror %s failed: %s", host, exc)
    if last_error is not None:
        raise StreamError("The stream provider is not responding right now.")
    raise StreamError("No video source found for this title.")


def resolve_vidrock(
    tmdb_id: int, season: int | None = None, episode: int | None = None
) -> list[StreamSource]:
    """Every working VidRock CDN mirror, best first."""
    payload = _vidrock_api(tmdb_id, season, episode)
    sources: list[StreamSource] = []
    seen: set[str] = set()
    headers = (
        ("Referer", "https://vidrock.to/"),
        ("Origin", "https://vidrock.to"),
    )
    for name, item in payload.items():
        if not isinstance(item, dict):
            continue
        encrypted = item.get("url")
        if not encrypted:
            continue
        try:
            url = decrypt_vidrock_url(str(encrypted))
        except Exception as exc:  # noqa: BLE001 - one bad mirror must not stop the rest
            log.info("VidRock mirror %s could not be decrypted: %s", name, exc)
            continue
        if url in seen:
            continue
        seen.add(url)
        kind = "mp4" if url.lower().endswith(".mp4") else "hls"
        sources.append(
            StreamSource(
                url=url,
                label=str(name),
                language=str(item.get("language") or "English"),
                kind=kind,
                headers=headers,
            )
        )
    return _verified(sources)


# ── VixSrc (signed HLS master playlist) ─────────────────────────────────────
def resolve_vixsrc(
    tmdb_id: int, season: int | None = None, episode: int | None = None
) -> list[StreamSource]:
    if season is not None and episode is not None:
        api_url = f"{VIXSRC_HOST}/api/tv/{tmdb_id}/{season}/{episode}"
        referer = f"{VIXSRC_HOST}/tv/{tmdb_id}/{season}/{episode}"
    else:
        api_url = f"{VIXSRC_HOST}/api/movie/{tmdb_id}"
        referer = f"{VIXSRC_HOST}/movie/{tmdb_id}"

    headers = {
        "User-Agent": UA,
        "Referer": referer,
        "Origin": VIXSRC_HOST,
        "Accept": "application/json, text/html;q=0.9,*/*;q=0.8",
    }
    session = _session()
    try:
        response = session.get(api_url, headers=headers, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError) as exc:
        log.info("VixSrc metadata failed: %s", exc)
        raise StreamError("The stream provider is not responding right now.") from exc

    src = payload.get("src") if isinstance(payload, dict) else None
    if not src:
        raise StreamError("No video source found for this title.")

    embed_url = VIXSRC_HOST + str(src)
    try:
        embed = session.get(
            embed_url,
            headers={"User-Agent": UA, "Referer": referer},
            timeout=REQUEST_TIMEOUT,
        )
        embed.raise_for_status()
    except requests.RequestException as exc:
        log.info("VixSrc embed page failed: %s", exc)
        raise StreamError("The stream provider is not responding right now.") from exc

    match = re.search(
        r"window\.masterPlaylist\s*=\s*(\{.*?\});", embed.text, re.DOTALL
    )
    if match is None:
        raise StreamError("No video source found for this title.")

    token = re.search(r"'token':\s*'([^']+)'", match.group(1))
    expires = re.search(r"'expires':\s*'([^']+)'", match.group(1))
    playlist = re.search(r"url:\s*'([^']+)'", match.group(1))
    if not (token and expires and playlist):
        raise StreamError("No video source found for this title.")

    url = f"{playlist.group(1)}?token={token.group(1)}&expires={expires.group(1)}"
    source = StreamSource(
        url=url,
        label="VixSrc",
        language="English",
        kind="hls",
        headers=(
            ("User-Agent", UA),
            ("Referer", referer),
            ("Origin", VIXSRC_HOST),
        ),
    )
    verified = _verified([source])
    if not verified:
        raise StreamError("No video source found for this title.")
    return verified


# ── Verification and dispatch ───────────────────────────────────────────────
def _looks_playable(source: StreamSource) -> bool:
    """Cheap pre-flight so dead CDN mirrors never reach the player."""
    if source.kind == "mp4":
        return True
    try:
        with _session().get(
            source.url,
            headers=source.header_dict(),
            timeout=PREFLIGHT_TIMEOUT,
            stream=True,
            allow_redirects=True,
        ) as response:
            if response.status_code >= 400:
                log.info(
                    "Pre-flight %s returned HTTP %s", source.label, response.status_code
                )
                return False
            head = response.raw.read(24, decode_content=True) or b""
            return b"#EXTM3U" in head
    except requests.RequestException as exc:
        log.info("Pre-flight %s failed: %s", source.label, exc)
        return False


def _verified(sources: list[StreamSource]) -> list[StreamSource]:
    if not sources:
        return []
    if len(sources) == 1:
        return sources if _looks_playable(sources[0]) else []
    with ThreadPoolExecutor(max_workers=min(6, len(sources))) as pool:
        results = list(pool.map(_looks_playable, sources))
    return [source for source, ok in zip(sources, results) if ok]


def resolve(
    server_id: str,
    media_type: str,
    tmdb_id: int,
    season: int | None = None,
    episode: int | None = None,
) -> list[StreamSource]:
    """Resolve one server entry into ordered playable sources."""
    server = next((s for s in SERVERS if s.id == server_id), None)
    if server is None:
        raise StreamError("That server is not available.")

    is_tv = media_type == "tv"
    season_arg = season if is_tv else None
    episode_arg = episode if is_tv else None

    try:
        if server.provider == "vidrock":
            sources = resolve_vidrock(tmdb_id, season_arg, episode_arg)
        elif server.provider == "vixsrc":
            sources = resolve_vixsrc(tmdb_id, season_arg, episode_arg)
        else:
            sources = []
    except StreamError:
        raise
    except Exception as exc:  # noqa: BLE001 - never leak provider internals
        log.warning("Unexpected %s failure: %s", server.provider, exc, exc_info=True)
        raise StreamError("No video source found for this title.") from exc

    if not sources:
        raise StreamError("No video source found for this title.")
    log.info(
        "%s resolved %d source(s) for %s %s S%sE%s",
        server.name,
        len(sources),
        media_type,
        tmdb_id,
        season_arg,
        episode_arg,
    )
    return sources


def parse_vidrock_payload(payload: dict) -> list[tuple[str, str]]:
    """Expose decrypted (label, url) pairs; used by tests and diagnostics."""
    pairs: list[tuple[str, str]] = []
    for name, item in payload.items():
        if isinstance(item, dict) and item.get("url"):
            try:
                pairs.append((name, decrypt_vidrock_url(str(item["url"]))))
            except Exception:  # noqa: BLE001
                continue
    return pairs


__all__ = [
    "SERVERS",
    "StreamError",
    "StreamServer",
    "StreamSource",
    "decrypt_vidrock_url",
    "parse_vidrock_payload",
    "resolve",
    "resolve_vidrock",
    "resolve_vixsrc",
    "servers_payload",
]
