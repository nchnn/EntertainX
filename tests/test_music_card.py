import pytest

from ui.components.music_card import (
    PlayerProgress,
    duration_ms,
    format_duration,
)


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
