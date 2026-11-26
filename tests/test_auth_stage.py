from PySide6.QtCore import QPointF
from PySide6.QtGui import QTransform

from ui.components.auth.stage import (
    WORD_TO_CARD,
    WORDS,
    AuthStage,
    MediaFan,
    RotatingWord,
)


def test_poster_fan_hover_hits_side_cards_and_centre(app):
    fan = MediaFan()
    fan.resize(420, 420)
    fan.show()
    cards, card_w, card_h = fan._layout()

    def world(index, local):
        origin, angle, *_ = cards[index]
        transform = QTransform()
        transform.translate(origin.x(), origin.y())
        transform.rotate(angle)
        transform.translate(-card_w / 2, -card_h / 2)
        return transform.map(QPointF(*local))

    assert fan._card_at(world(0, (8, card_h / 2))) == 0
    assert fan._card_at(world(1, (card_w - 8, card_h / 2))) == 1
    assert fan._card_at(world(2, (card_w / 2, card_h / 2))) == 2

    fan._set_hover(0)
    assert fan._hover == 0
    assert fan._animations[0].endValue() == 1.0
    assert fan._animations[2].endValue() == 0.0


def test_spotlight_lifts_one_cover_and_releases_the_rest(app):
    fan = MediaFan()
    fan.set_spotlight(1)
    assert [a.endValue() for a in fan._spot_animations] == [0.0, 1.0, 0.0]

    fan.set_spotlight(0)
    assert [a.endValue() for a in fan._spot_animations] == [1.0, 0.0, 0.0]

    fan.set_spotlight(-1)
    assert all(a.endValue() == 0.0 for a in fan._spot_animations)


def test_fan_paints_with_idle_float_and_spotlight(app):
    fan = MediaFan()
    fan.resize(520, 420)
    fan.show()
    fan.set_phase(0.37)
    fan._spot[2] = 1.0
    image = fan.grab().toImage()

    assert not image.isNull()
    assert any(image.pixel(x, y) >> 24 for x in range(0, 520, 20) for y in range(0, 420, 20))


def test_rotating_word_cycles_and_announces_each_change(app):
    word = RotatingWord()
    seen = []
    word.changed.connect(seen.append)

    assert word.word == WORDS[0]
    word.advance()
    word.advance()
    word.advance()  # wraps around

    assert seen == [1, 2, 0]
    assert word.word == WORDS[0]


def test_rotating_word_keeps_its_size_for_the_longest_word(app):
    word = RotatingWord()
    first = word.sizeHint()
    word.set_index(1, animate=False)

    assert word.sizeHint() == first
    assert first.width() > 0 and first.height() > 0


def test_each_word_spotlights_its_matching_poster(app):
    stage = AuthStage()
    for index in range(len(WORDS)):
        stage.word.set_index(index)
        assert stage.fan._spotlight == WORD_TO_CARD[index]


def test_stage_paints_and_ticks(app):
    stage = AuthStage()
    stage.resize(680, 760)
    stage.show()
    stage._tick()

    assert 0.0 <= stage._phase < 1.0
    assert not stage.grab().isNull()


def test_stage_introduces_itself_once(app):
    stage = AuthStage()
    stage.resize(680, 760)
    stage.show()
    assert stage._entered

    stage.hide()
    stage.show()
    assert stage._entered
