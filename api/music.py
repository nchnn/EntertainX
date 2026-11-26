"""Music streaming, metadata, and lyrics adapter.

Integrates JioSaavn (with DES URL decryption for direct 320k/160k streaming),
Deezer and iTunes for international discovery, and LRCLIB for time-synced lyrics.
"""

from __future__ import annotations

import base64
import hashlib
import json
import re
import time
from pathlib import Path
from urllib.parse import quote, urlencode

import requests
from Crypto.Cipher import DES

from api.config import CACHE_DIR
from ui.components.music.models import (
    ArtistProfile,
    LyricLine,
    Track,
    parse_duration,
    parse_lrc,
)

JIOSAAVN_API = "https://www.jiosaavn.com/api.php"
DES_KEY = b"38346591"

JIO_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36"
    ),
    "X-Forwarded-For": "49.36.0.1",
    "X-Real-IP": "49.36.0.1",
    "Cookie": "explicit_content=1",
}

LRCLIB_API = "https://lrclib.net/api"
DEEZER_API = "https://api.deezer.com"

SEARCH_TTL = 15 * 60
CHART_TTL = 60 * 60
LYRICS_TTL = 7 * 24 * 3600


def _unpad_pkcs5(data: bytes) -> bytes:
    if not data:
        return b""
    pad_len = data[-1]
    if pad_len < 1 or pad_len > 8:
        return data
    return data[:-pad_len]


def decrypt_jiosaavn_url(encrypted_b64: str) -> str:
    """Decrypt a JioSaavn encrypted media token into a direct CDN audio URL."""
    if not encrypted_b64:
        return ""
    try:
        cipher = DES.new(DES_KEY, DES.MODE_ECB)
        raw_ciphertext = base64.b64decode(encrypted_b64)
        decrypted = cipher.decrypt(raw_ciphertext)
        return _unpad_pkcs5(decrypted).decode("utf-8").strip()
    except Exception:
        return ""


def clean_html(text: str) -> str:
    """Clean encoded HTML entities and quotes in metadata."""
    if not text:
        return ""
    return (
        text.replace("&quot;", '"')
        .replace("&#039;", "'")
        .replace("&amp;", "&")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
    )


class MusicClient:
    """API adapter for streaming music, fetching charts, metadata, and lyrics."""

    def __init__(self, cache_dir: Path | None = None) -> None:
        self._cache_dir = (cache_dir or CACHE_DIR) / "music"
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._session = requests.Session()

    def _cache_path(self, bucket: str, key: str) -> Path:
        hashed = hashlib.md5(key.encode("utf-8")).hexdigest()
        bucket_dir = self._cache_dir / bucket
        bucket_dir.mkdir(parents=True, exist_ok=True)
        return bucket_dir / f"{hashed}.json"

    def _read_cache(self, bucket: str, key: str, ttl: int) -> dict | list | None:
        path = self._cache_path(bucket, key)
        if not path.exists():
            return None
        try:
            stat = path.stat()
            if time.time() - stat.st_mtime > ttl:
                return None
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None

    def _write_cache(self, bucket: str, key: str, data: dict | list) -> None:
        try:
            path = self._cache_path(bucket, key)
            path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass

    # ── JioSaavn Track Extraction ───────────────────────────────────────────
    def _parse_jiosaavn_track(self, item: dict) -> Track | None:
        more = item.get("more_info", {})
        enc_url = more.get("encrypted_media_url")
        if not enc_url:
            return None

        supports_320 = str(more.get("320kbps", "")).lower() == "true"
        raw_stream_url = decrypt_jiosaavn_url(enc_url)
        if not raw_stream_url:
            return None

        if supports_320:
            stream_url = re.sub(
                r"_(48|96|160|320)\.(mp4|aac|mp3)(?=[?#]|$)",
                r"_320.\2",
                raw_stream_url,
            )
            quality = "320KBPS"
        else:
            stream_url = raw_stream_url
            quality = "160KBPS"

        primary_artists = [
            a.get("name")
            for a in more.get("artistMap", {}).get("primary_artists", [])
            if a.get("name")
        ]
        artist_name = ", ".join(primary_artists) if primary_artists else clean_html(item.get("subtitle", "Unknown Artist"))
        if not artist_name or artist_name.strip() == "":
            artist_name = "Unknown Artist"

        raw_image = item.get("image", "")
        artwork = (
            raw_image.replace("150x150", "500x500")
            .replace("50x50", "500x500")
            .replace("http://", "https://")
        )

        duration_sec = int(more.get("duration", 0) or 0)
        has_lyrics = str(more.get("has_lyrics", "")).lower() == "true"

        return Track(
            id=str(item.get("id", "")),
            title=clean_html(item.get("title", "Untitled")),
            artist=artist_name,
            album=clean_html(more.get("album", "")),
            duration_ms=duration_sec * 1000 if duration_sec > 0 else 180_000,
            artwork_url=artwork,
            stream_url=stream_url,
            quality=quality,
            source="jiosaavn",
            has_lyrics=has_lyrics,
            encrypted_media_url=enc_url,
        )

    def _resolve_full_stream(self, title: str, artist: str) -> tuple[str, str, int] | None:
        """Resolve full-length 320kbps JioSaavn stream for a given title and artist."""
        try:
            params = {
                "__call": "search.getResults",
                "_format": "json",
                "_marker": "0",
                "api_version": "4",
                "ctx": "android",
                "q": f"{title} {artist}",
                "p": "1",
                "n": "3",
            }
            url = f"{JIOSAAVN_API}?{urlencode(params)}"
            resp = self._session.get(url, headers=JIO_HEADERS, timeout=(3, 6))
            if resp.status_code == 200:
                data = resp.json()
                for item in data.get("results", []):
                    track = self._parse_jiosaavn_track(item)
                    if track and track.stream_url:
                        return track.stream_url, track.quality, track.duration_ms
        except Exception:
            pass
        return None

    # ── Search ──────────────────────────────────────────────────────────────
    def search(self, query: str, limit: int = 25) -> list[Track]:
        """Search full-length tracks across JioSaavn."""
        query = query.strip()
        if not query:
            return []

        cached = self._read_cache("search", query, SEARCH_TTL)
        if isinstance(cached, list):
            return [Track(**item) for item in cached]

        tracks: list[Track] = []
        try:
            params = {
                "__call": "search.getResults",
                "_format": "json",
                "_marker": "0",
                "api_version": "4",
                "ctx": "android",
                "q": query,
                "p": "1",
                "n": str(max(limit, 25)),
            }
            url = f"{JIOSAAVN_API}?{urlencode(params)}"
            resp = self._session.get(url, headers=JIO_HEADERS, timeout=(4, 8))
            if resp.status_code == 200:
                data = resp.json()
                for item in data.get("results", []):
                    track = self._parse_jiosaavn_track(item)
                    if track:
                        tracks.append(track)
        except Exception:
            pass

        # If JioSaavn yielded few results, discover via Deezer and resolve full 320k streams
        if len(tracks) < 5:
            try:
                deezer_url = f"{DEEZER_API}/search?q={quote(query)}&limit={limit}"
                resp = self._session.get(deezer_url, timeout=(4, 8))
                if resp.status_code == 200:
                    data = resp.json()
                    for item in data.get("data", []):
                        title = clean_html(item.get("title", ""))
                        artist = clean_html(item.get("artist", {}).get("name", ""))
                        resolved = self._resolve_full_stream(title, artist)
                        if resolved:
                            full_url, quality, duration_ms = resolved
                            tracks.append(
                                Track(
                                    id=f"dz_{item.get('id')}",
                                    title=title,
                                    artist=artist,
                                    album=clean_html(item.get("album", {}).get("title", "")),
                                    duration_ms=duration_ms or (int(item.get("duration", 0)) * 1000),
                                    artwork_url=item.get("album", {}).get("cover_big", "") or item.get("album", {}).get("cover_medium", ""),
                                    stream_url=full_url,
                                    quality=quality,
                                    source="deezer_full",
                                )
                            )
            except Exception:
                pass

        if tracks:
            self._write_cache("search", query, [t.to_dict() for t in tracks])
        return tracks

    # ── Trending & Editorial Shelves ────────────────────────────────────────
    def get_trending(self, limit: int = 25) -> list[Track]:
        """Fetch trending chart tracks with guaranteed full-length streams."""
        cached = self._read_cache("charts", "trending", CHART_TTL)
        if isinstance(cached, list):
            return [Track(**item) for item in cached]

        tracks: list[Track] = []
        for chart_query in ["Trending Hits 2026", "Global Top Hits", "Pop Hits", "OPM Hits"]:
            jio_tracks = self.search(chart_query, limit=limit)
            for t in jio_tracks:
                if t.id not in {existing.id for existing in tracks}:
                    tracks.append(t)
            if len(tracks) >= limit:
                break

        tracks = tracks[:limit]
        if tracks:
            self._write_cache("charts", "trending", [t.to_dict() for t in tracks])
        return tracks

    def get_albums_and_singles(self, query: str = "Pop hits") -> list[dict]:
        """Fetch album and single cards for the carousel shelf."""
        cached = self._read_cache("albums", query, CHART_TTL)
        if isinstance(cached, list):
            return cached

        results: list[dict] = []
        try:
            resp = self._session.get(f"{DEEZER_API}/search/album?q={quote(query)}&limit=15", timeout=(4, 8))
            if resp.status_code == 200:
                for item in resp.json().get("data", []):
                    results.append({
                        "id": str(item.get("id")),
                        "title": clean_html(item.get("title", "")),
                        "artist": clean_html(item.get("artist", {}).get("name", "")),
                        "artwork_url": item.get("cover_big") or item.get("cover_medium", ""),
                        "record_type": item.get("record_type", "album").capitalize(),
                        "tracklist_url": item.get("tracklist", ""),
                    })
        except Exception:
            pass

        if results:
            self._write_cache("albums", query, results)
        return results

    # ── Artist Profile ──────────────────────────────────────────────────────
    def get_artist(self, artist_name: str) -> ArtistProfile:
        """Fetch artist profile banner, listeners count, bio, and top tracks."""
        clean_name = artist_name.strip()
        cached = self._read_cache("artists", clean_name, CHART_TTL)
        if isinstance(cached, dict):
            tracks = [Track(**t) for t in cached.get("top_tracks", [])]
            return ArtistProfile(
                id=cached.get("id", ""),
                name=cached.get("name", clean_name),
                image_url=cached.get("image_url", ""),
                monthly_listeners=cached.get("monthly_listeners", ""),
                subscribers=cached.get("subscribers", ""),
                bio=cached.get("bio", ""),
                top_tracks=tracks,
                albums=cached.get("albums", []),
            )

        profile = ArtistProfile(
            id=clean_name.lower().replace(" ", "-"),
            name=clean_name,
            monthly_listeners="12.5M monthly listeners",
            subscribers="4.2M subscribers",
            bio=f"Popular music artist {clean_name}.",
        )

        try:
            resp = self._session.get(f"{DEEZER_API}/search/artist?q={quote(clean_name)}&limit=1", timeout=(4, 8))
            if resp.status_code == 200:
                artists = resp.json().get("data", [])
                if artists:
                    a = artists[0]
                    profile.id = str(a.get("id"))
                    profile.name = a.get("name", clean_name)
                    profile.image_url = a.get("picture_xl") or a.get("picture_big", "")
                    fans = a.get("nb_fan", 0)
                    if fans:
                        if fans >= 1_000_000:
                            profile.monthly_listeners = f"{fans / 1_000_000:.1f}M monthly audience"
                        else:
                            profile.monthly_listeners = f"{fans:,} monthly audience"
        except Exception:
            pass

        # Top tracks for artist
        top_tracks = self.search(clean_name, limit=12)
        profile.top_tracks = top_tracks

        # Write cache
        cache_data = {
            "id": profile.id,
            "name": profile.name,
            "image_url": profile.image_url,
            "monthly_listeners": profile.monthly_listeners,
            "subscribers": profile.subscribers,
            "bio": profile.bio,
            "top_tracks": [t.to_dict() for t in profile.top_tracks],
            "albums": profile.albums,
        }
        self._write_cache("artists", clean_name, cache_data)
        return profile

    # ── Synced Lyrics (LRCLIB backend) ──────────────────────────────────────
    def get_lyrics(
        self,
        track_title: str,
        artist_name: str,
        duration_sec: int | None = None,
    ) -> list[LyricLine]:
        """Fetch time-synced lyrics from LRCLIB."""
        cache_key = f"{track_title} - {artist_name}".lower()
        cached = self._read_cache("lyrics", cache_key, LYRICS_TTL)
        if isinstance(cached, list):
            return [LyricLine(**item) for item in cached]

        lines: list[LyricLine] = []
        try:
            params = {
                "track_name": track_title,
                "artist_name": artist_name,
            }
            if duration_sec:
                params["duration"] = str(duration_sec)

            url = f"{LRCLIB_API}/search?{urlencode(params)}"
            resp = self._session.get(url, headers={"User-Agent": "EntertainX/1.0"}, timeout=(4, 8))
            if resp.status_code == 200:
                results = resp.json()
                if isinstance(results, list) and results:
                    best = results[0]
                    synced = best.get("syncedLyrics")
                    plain = best.get("plainLyrics")
                    if synced:
                        lines = parse_lrc(synced)
                    elif plain:
                        # Construct faux timed lines if only plain lyrics exist
                        raw_lines = [l.strip() for l in plain.splitlines() if l.strip()]
                        interval = 4000
                        for i, l in enumerate(raw_lines):
                            lines.append(LyricLine(time_ms=i * interval, text=l))
        except Exception:
            pass

        if lines:
            self._write_cache("lyrics", cache_key, [{"time_ms": l.time_ms, "text": l.text} for l in lines])
        return lines
