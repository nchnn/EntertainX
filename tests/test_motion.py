import pytest
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from ui.components import motion


@pytest.fixture()
def animated(monkeypatch):
    """Turn real animation back on (the suite runs with it off)."""
    monkeypatch.delenv(motion.REDUCE_MOTION_ENV, raising=False)


@pytest.fixture()
def shown(app):
    host = QWidget()
    layout = QVBoxLayout(host)
    target = QLabel("hello")
    layout.addWidget(target)
    host.resize(240, 100)
    host.show()
    app.processEvents()
    yield target
    host.close()


def test_reduced_motion_applies_the_end_state_immediately(app, shown):
    calls = []
    motion.reveal(shown, on_finished=lambda: calls.append("reveal"))
    motion.conceal(shown, on_finished=lambda: calls.append("conceal"))
    motion.swap(shown, lambda: calls.append("swap"))
    motion.shake(shown)

    assert calls == ["reveal", "conceal", "swap"]
    assert shown.graphicsEffect() is None


def test_reveal_fades_in_then_removes_its_effect(animated, shown, wait_for):
    done = []
    motion.reveal(shown, duration=80, on_finished=lambda: done.append(True))

    effect = shown.graphicsEffect()
    assert isinstance(effect, motion.MotionEffect)
    assert effect.progress == 0.0

    assert wait_for(lambda: bool(done))
    assert shown.graphicsEffect() is None


def test_conceal_holds_the_widget_invisible(animated, shown, wait_for):
    done = []
    motion.conceal(shown, duration=60, on_finished=lambda: done.append(True))
    assert wait_for(lambda: bool(done))

    assert shown.graphicsEffect().progress == 0.0
    motion.clear(shown)
    assert shown.graphicsEffect() is None


def test_swap_applies_the_change_while_hidden(animated, shown, wait_for):
    seen = []

    def apply():
        seen.append(shown.graphicsEffect().progress)

    motion.swap(shown, apply, out_ms=60, in_ms=60)
    assert wait_for(lambda: shown.graphicsEffect() is None and bool(seen))

    assert seen == [0.0]


def test_a_newer_motion_is_not_cleared_by_an_older_one(animated, shown, wait_for):
    motion.reveal(shown, duration=300)
    motion.conceal(shown, duration=40)
    assert wait_for(lambda: shown.graphicsEffect() is not None and shown.graphicsEffect().progress == 0.0)

    # Give the interrupted reveal every chance to report back late.
    wait_for(lambda: False, timeout=0.4)
    assert isinstance(shown.graphicsEffect(), motion.MotionEffect)
    assert shown.graphicsEffect().progress == 0.0


def test_shake_cleans_up(animated, shown, wait_for):
    motion.shake(shown, duration=80)
    assert isinstance(shown.graphicsEffect(), motion.MotionEffect)
    assert wait_for(lambda: shown.graphicsEffect() is None)


def test_cascade_staggers_each_widget(animated, app, wait_for):
    host = QWidget()
    layout = QVBoxLayout(host)
    labels = [QLabel(str(i)) for i in range(3)]
    for item in labels:
        layout.addWidget(item)
    host.show()

    motion.cascade(labels, start=0, step=40, duration=60)
    assert all(item.graphicsEffect() is not None for item in labels)
    assert wait_for(lambda: all(item.graphicsEffect() is None for item in labels))
    host.close()


def test_effect_draws_nothing_at_zero_progress(app, shown):
    effect = motion.MotionEffect(0, 12)
    shown.setGraphicsEffect(effect)
    effect.set_progress(0.0)
    image = shown.window().grab().toImage()

    background = image.pixel(2, 2)
    assert all(
        image.pixel(x, y) == background
        for x in range(10, 60, 5)
        for y in range(40, 60, 5)
    )
    shown.setGraphicsEffect(None)
