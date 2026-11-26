"""Music UI components and models."""

from ui.components.music.artist_header import ArtistHeader
from ui.components.music.audio_engine import AudioEngine, get_audio_engine
from ui.components.music.lyrics_view import LyricsView
from ui.components.music.models import (
    ArtistProfile,
    LyricLine,
    Track,
    format_time,
    parse_duration,
    parse_lrc,
)
from ui.components.music.player_bar import PlayerBar
from ui.components.music.queue_drawer import QueueDrawer
from ui.components.music.track_card import AlbumCover, TrackCard
from ui.components.music.track_row import TrackRow

__all__ = [
    "AlbumCover",
    "ArtistHeader",
    "AudioEngine",
    "LyricLine",
    "LyricsView",
    "PlayerBar",
    "QueueDrawer",
    "Track",
    "TrackCard",
    "TrackRow",
    "format_time",
    "get_audio_engine",
    "parse_duration",
    "parse_lrc",
]
