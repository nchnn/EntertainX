"""Domain models and parsing helpers for the EntertainX music subsystem."""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class Track:
    id: str
    title: str
    artist: str
    album: str = ""
    duration_ms: int = 180_000
    artwork_url: str = ""
    stream_url: str = ""
    quality: str = "320KBPS"
    source: str = "jiosaavn"
    has_lyrics: bool = False
    encrypted_media_url: str = ""

    @property
    def duration_formatted(self) -> str:
        return format_time(self.duration_ms)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "artist": self.artist,
            "album": self.album,
            "duration_ms": self.duration_ms,
            "artwork_url": self.artwork_url,
            "stream_url": self.stream_url,
            "quality": self.quality,
            "source": self.source,
        }


@dataclass
class LyricLine:
    time_ms: int
    text: str


@dataclass
class ArtistProfile:
    id: str
    name: str
    image_url: str = ""
    monthly_listeners: str = ""
    subscribers: str = ""
    bio: str = ""
    top_tracks: list[Track] = field(default_factory=list)
    albums: list[dict] = field(default_factory=list)


def format_time(ms: int) -> str:
    """Format milliseconds into m:ss format, clamped at zero."""
    total_seconds = max(0, int(ms)) // 1000
    minutes, seconds = divmod(total_seconds, 60)
    return f"{minutes}:{seconds:02d}"


def parse_duration(val: str | int | float) -> int:
    """Parse duration in seconds or 'm:ss' into milliseconds."""
    if isinstance(val, (int, float)):
        return int(val * 1000) if val < 10000 else int(val)
    text = str(val).strip()
    if not text:
        return 180_000
    if ":" in text:
        parts = text.split(":")
        try:
            if len(parts) == 2:
                return (int(parts[0]) * 60 + int(parts[1])) * 1000
            if len(parts) == 3:
                return (int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])) * 1000
        except ValueError:
            return 180_000
    try:
        sec = float(text)
        return int(sec * 1000)
    except ValueError:
        return 180_000


_LRC_TIMESTAMP_RE = re.compile(r"\[(\d{1,2}):(\d{2})(?:\.(\d{1,3}))?\]")


def parse_lrc(lrc_text: str) -> list[LyricLine]:
    """Parse timestamped LRC lyric text into a sorted list of LyricLine objects."""
    lines: list[LyricLine] = []
    if not lrc_text:
        return lines

    for raw_line in lrc_text.splitlines():
        raw_line = raw_line.strip()
        if not raw_line:
            continue

        matches = list(_LRC_TIMESTAMP_RE.finditer(raw_line))
        if not matches:
            continue

        clean_text = _LRC_TIMESTAMP_RE.sub("", raw_line).strip()
        # Clean any word-sync brackets like <00:12.34>
        clean_text = re.sub(r"<[^>]+>", "", clean_text).strip()

        for match in matches:
            minutes = int(match.group(1))
            seconds = int(match.group(2))
            frac_str = match.group(3) or "0"
            if len(frac_str) == 1:
                ms = int(frac_str) * 100
            elif len(frac_str) == 2:
                ms = int(frac_str) * 10
            else:
                ms = int(frac_str[:3])

            timestamp_ms = (minutes * 60 + seconds) * 1000 + ms
            lines.append(LyricLine(time_ms=timestamp_ms, text=clean_text))

    lines.sort(key=lambda item: item.time_ms)
    return lines
