from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel

from ui.frameless import FramelessWindow, TitleBar


def test_window_is_frameless_with_minimum_size(app):
    window = FramelessWindow()
    assert window.windowFlags() & Qt.WindowType.FramelessWindowHint
    assert window.minimumWidth() == 900
    assert window.minimumHeight() == 620
    window.close()


def test_set_content_swaps_body(app):
    window = FramelessWindow()
    first = QLabel("first")
    second = QLabel("second")

    window.set_content(first)
    assert window.content is first
    assert first.parent() is not None

    window.set_content(second)
    assert window.content is second
    window.close()


def test_titlebar_emits_signals(app):
    bar = TitleBar()
    events = []
    bar.minimize_requested.connect(lambda: events.append("minimize"))
    bar.maximize_requested.connect(lambda: events.append("maximize"))
    bar.close_requested.connect(lambda: events.append("close"))

    bar.minimize_button.click()
    bar.maximize_button.click()
    bar.close_button.click()
    assert events == ["minimize", "maximize", "close"]


def test_titlebar_reflects_maximized_state(app):
    bar = TitleBar()
    bar.set_maximized(True)
    assert bar.maximize_button.toolTip() == "Restore"
    bar.set_maximized(False)
    assert bar.maximize_button.toolTip() == "Maximize"


def test_toggle_maximize_round_trip(app):
    window = FramelessWindow()
    window.show()
    app.processEvents()

    assert not window.is_maximized()
    window.toggle_maximize()
    app.processEvents()
    assert window.is_maximized()

    window.toggle_maximize()
    app.processEvents()
    assert not window.is_maximized()
    window.close()
