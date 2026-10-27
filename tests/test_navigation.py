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


def test_content_area_restores_last_subtab():
    from ui.content_area import ContentArea
    ca = ContentArea(on_logout=lambda: None)
    ca.show_category("Video")
    ca._switch_subtab(2)   # TV Shows (index 2)
    ca.show_category("Music")
    ca.show_category("Video")
    assert ca._last_tab.get("Video") == 2

