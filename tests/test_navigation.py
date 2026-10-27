import sys
import pytest
from PySide6.QtWidgets import QApplication

app = QApplication.instance() or QApplication(sys.argv)


def test_sidebar_default_active():
    from ui.sidebar import Sidebar
    activated = []
    sb = Sidebar("testuser", lambda c: activated.append(c))
    assert sb.active_category() == "Video"


def test_sidebar_category_change():
    from ui.sidebar import Sidebar
    activated = []
    sb = Sidebar("testuser", lambda c: activated.append(c))
    sb.set_active("Music")
    assert sb.active_category() == "Music"


def test_sidebar_all_categories_reachable():
    from ui.sidebar import Sidebar, CATEGORIES
    results = []
    sb = Sidebar("testuser", lambda c: results.append(c))
    for cat in CATEGORIES:
        sb.set_active(cat)
    assert results[-len(CATEGORIES):] == CATEGORIES
