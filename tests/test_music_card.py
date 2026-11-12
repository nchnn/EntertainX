import re

import pytest
from PySide6.QtCore import Qt

from theme import theme_manager as theme
from ui.components.music_card import (
    AlbumArt,
    MusicPlayerCard,
    PlayerProgress,
    duration_ms,
    format_duration,
)
from ui.pages.sample_data import ALBUMS


def test_duration_parses_minutes_and_hours():
    assert duration_ms("3:42") == 222_000
    assert duration_ms("1:02:03") == 3_723_000


@pytest.mark.parametrize("text", ["", "nope", "3", "3:xx"])
def test_duration_falls_back_for_bad_input(text):
    assert duration_ms(text) == 180_000


def test_format_duration_clamps_and_pads():
    assert format_duration(0) == "0:00"
    assert format_duration(111_000) == "1:51"
    assert format_duration(-500) == "0:00"


def test_progress_value_is_clamped(app):
    bar = PlayerProgress()
    bar.set_value(1.4)
    assert bar.value() == 1.0
    bar.set_value(-0.2)
    assert bar.value() == 0.0


def test_album_art_side_is_deterministic(app):
    art = AlbumArt("Soft Static")
    assert art.disc_side() in (-1, 1)
    assert art.disc_side() == AlbumArt("Soft Static").disc_side()


def test_player_card_exposes_text_and_search(app):
    card = MusicPlayerCard("Soft Static", "Mira Vale", "10 tracks", "3:42")
    assert card.title == "Soft Static"
    assert card.subtitle_label.full_text() == "Mira Vale"
    assert card.meta_label.full_text() == "10 tracks"
    assert card.matches("mira")
    assert card.matches("tracks")
    assert not card.matches("zzzz")


def test_player_card_elides_long_text_without_widening(app):
    card = MusicPlayerCard(
        "A very long album title " * 4, "An artist", "10 tracks", "3:42"
    )
    assert card.minimumSizeHint().width() == theme.CARD_MIN_WIDTH


def test_play_toggle_switches_state_and_glyph(app):
    card = MusicPlayerCard("Soft Static", "Mira Vale", "10 tracks", "3:42")
    assert not card.is_playing()
    assert card._button.toolTip() == "Play Soft Static"

    card.toggle()
    assert card.is_playing()
    assert card._button.toolTip() == "Pause Soft Static"

    card.toggle()
    assert not card.is_playing()
    assert card._button.toolTip() == "Play Soft Static"


def test_play_disc_is_keyboard_reachable_and_named(app):
    card = MusicPlayerCard("Soft Static", "Mira Vale", "10 tracks", "3:42")
    assert card._button.focusPolicy() != Qt.FocusPolicy.NoFocus
    assert card._button.accessibleName() == "Play Soft Static"


def test_progress_updates_bar_and_elapsed(app):
    card = MusicPlayerCard("A", "B", "1 track", "3:42")
    card.play()
    card._animation.setCurrentTime(111_000)
    assert card._progress == pytest.approx(0.5, abs=0.02)
    assert card._progress_bar.value() == pytest.approx(0.5, abs=0.02)
    assert card._elapsed_label.text() == "1:51"
    card.pause()


def test_finishing_resets_to_the_start(app):
    card = MusicPlayerCard("A", "B", "1 track", "3:42")
    card.play()
    card._on_finished()
    assert not card.is_playing()
    assert card._elapsed_label.text() == "0:00"
    assert card._progress_bar.value() == 0.0


@pytest.mark.parametrize("length", ["", "nope"])
def test_missing_length_uses_three_minutes(app, length):
    card = MusicPlayerCard("A", "B", "1 track", length)
    assert card._track_ms == 180_000
    assert card._total_label.text() == "3:00"


def test_every_album_has_a_valid_length():
    assert all(re.fullmatch(r"\d+:\d{2}", album["length"]) for album in ALBUMS)
