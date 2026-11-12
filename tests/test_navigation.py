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


def test_sidebar_marks_active_button():
    from ui.sidebar import Sidebar

    sb = Sidebar("testuser", lambda c: None)
    sb.set_active("Music")
    assert sb._buttons["Music"].property("active") == "true"
    assert sb._buttons["Video"].property("active") == "false"
    assert sb._buttons["Music"].isChecked()
    assert not sb._buttons["Video"].isChecked()


def test_sidebar_logout_calls_callback():
    from PySide6.QtWidgets import QPushButton

    from ui.sidebar import Sidebar

    logged_out = []
    sb = Sidebar("testuser", lambda c: None, on_logout=lambda: logged_out.append(True))
    buttons = [b for b in sb.findChildren(QPushButton) if "Log out" in b.text()]
    assert buttons
    buttons[0].click()
    assert logged_out == [True]


def test_content_area_switches_pages_and_tabs():
    from ui.content_area import ContentArea

    ca = ContentArea(on_logout=lambda: None)
    ca.show_category("Music")
    assert ca.current_page().__class__.__name__ == "MusicPage"
    assert not ca._tab_bar.isVisible()  # single-tab category hides the tab bar

    ca.show_category("Games")
    ca._switch_subtab(2)
    assert ca.current_page().__class__.__name__ == "BrowseGamesPage"
    assert ca.current_tab_index() == 2
    assert ca._tab_buttons[2].property("active") == "true"


def test_content_area_passes_user_to_settings():
    from PySide6.QtWidgets import QLabel

    from ui.content_area import ContentArea

    ca = ContentArea(
        on_logout=lambda: None,
        user={"username": "chris", "email": "chris@example.com"},
    )
    ca.show_category("Settings")
    page = ca.current_page()
    assert page.__class__.__name__ == "SettingsPage"
    texts = [child.text() for child in page.findChildren(QLabel)]
    assert "chris@example.com" in texts


def test_main_window_logout_reaches_callback():
    from ui.main_window import MainWindow

    class FakeAuth:
        def __init__(self):
            self.logged_out = False

        def logout(self):
            self.logged_out = True

    auth = FakeAuth()
    calls = []
    window = MainWindow(
        auth,
        {"id": 1, "username": "chris", "email": "chris@example.com"},
        on_logout=lambda: calls.append(True),
    )
    window._do_logout()
    assert auth.logged_out
    assert calls == [True]

