"""Tests for EntertainX music models, audio engine, components, and page."""

import pytest
from PySide6.QtCore import Qt

from api.music import MusicClient, decrypt_jiosaavn_url
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
from ui.pages.music import MusicPage


def test_format_time():
    assert format_time(0) == "0:00"
    assert format_time(65_000) == "1:05"
    assert format_time(222_000) == "3:42"
    assert format_time(-500) == "0:00"


def test_parse_duration():
    assert parse_duration("3:42") == 222_000
    assert parse_duration(180) == 180_000
    assert parse_duration(180_000) == 180_000
    assert parse_duration("") == 180_000


def test_parse_lrc_synced_timestamps():
    lrc = (
        "[00:22.76] Humingang malalim, pumikit na muna\n"
        "[00:31.76] At baka sakaling namamalikmata lang\n"
    )
    lines = parse_lrc(lrc)
    assert len(lines) == 2
    assert lines[0].time_ms == 22760
    assert lines[0].text == "Humingang malalim, pumikit na muna"
    assert lines[1].time_ms == 31760
    assert lines[1].text == "At baka sakaling namamalikmata lang"


def test_track_model_properties():
    track = Track(
        id="test_1",
        title="Multo",
        artist="Cup of Joe",
        album="Sagada",
        duration_ms=222_000,
        artwork_url="https://example.com/art.jpg",
        stream_url="https://example.com/stream.mp4",
        quality="320KBPS",
    )
    assert track.duration_formatted == "3:42"
    d = track.to_dict()
    assert d["title"] == "Multo"
    assert d["quality"] == "320KBPS"


def test_decrypt_jiosaavn_url():
    # Token from earlier test run
    enc = "ID2ieOjCrwfgWvL5sXl4B1ImC5QfbsDyft5bxAtreIQ10KxXW0VFxQNMSPN3mCrWvICJvxKdvsjZrsW62Wv7Fhw7tS9a8Gtq"
    url = decrypt_jiosaavn_url(enc)
    assert url.startswith("https://aac.saavncdn.com/")
    assert "_96.mp4" in url


def test_audio_engine_queue_and_playback(app):
    engine = AudioEngine()
    t1 = Track(id="1", title="Track 1", artist="Artist 1", stream_url="https://example.com/1.mp3")
    t2 = Track(id="2", title="Track 2", artist="Artist 2", stream_url="https://example.com/2.mp3")

    engine.play_queue([t1, t2], start_index=0)
    assert engine.current_track is not None
    assert engine.current_track.id == "1"
    assert len(engine.queue) == 2

    # Volume control
    engine.set_volume(0.5)
    assert pytest.approx(engine.volume, abs=0.05) == 0.5

    # Shuffle and repeat toggles
    assert not engine.is_shuffle
    engine.toggle_shuffle()
    assert engine.is_shuffle

    assert not engine.is_repeat
    engine.toggle_repeat()
    assert engine.is_repeat

    # Next track
    engine.next_track()
    assert engine.current_track is not None


def test_track_card_widget(app):
    track = Track(id="1", title="Multo", artist="Cup of Joe", quality="320KBPS")
    card = TrackCard(track)
    assert card.title_label.text() == "Multo"
    assert card.artist_label.text() == "Cup of Joe"
    assert card.width() == 176


def test_track_row_widget(app):
    track = Track(id="1", title="Multo", artist="Cup of Joe", duration_ms=222_000)
    row = TrackRow(track, index=1)
    assert row.title_label.text() == "Multo"
    assert row.duration_label.text() == "3:42"


def test_player_bar_widget(app):
    bar = PlayerBar()
    assert bar.title_label.text() == "No track playing"
    assert bar.pos_label.text() == "0:00"
    assert bar.dur_label.text() == "0:00"


def test_lyrics_view_widget(app):
    lyrics_view = LyricsView()
    lines = [
        LyricLine(time_ms=1000, text="First line"),
        LyricLine(time_ms=5000, text="Second line"),
    ]
    lyrics_view._on_lyrics_loaded(lines)
    assert len(lyrics_view._rows) == 2
    assert lyrics_view._rows[0].text() == "First line"


def test_queue_drawer_widget(app):
    drawer = QueueDrawer()
    assert drawer.now_title.text() == "No track playing"


def test_artist_header_widget(app):
    profile = ArtistProfile(
        id="cup-of-joe",
        name="Cup of Joe",
        monthly_listeners="12M monthly audience",
        bio="OPM indie band.",
    )
    header = ArtistHeader(profile)
    assert header.name_label.text() == "Cup of Joe"


def test_music_page_builds_with_header_and_shelves(app):
    page = MusicPage()
    assert page.title == "Music"
    assert page.header.title == "Music"
    assert hasattr(page, "search")
    assert hasattr(page, "player_bar")
    assert hasattr(page, "lyrics_view")
    assert hasattr(page, "queue_drawer")
    assert hasattr(page, "shelf_albums")
    assert hasattr(page, "shelf_trending")

