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
    ca = ContentArea()
    ca.show_category("Video")
    ca._switch_subtab(1)   # TV Shows (index 1)
    ca.show_category("Music")
    ca.show_category("Video")
    assert ca._last_tab.get("Video") == 1


def test_sidebar_marks_active_button():
    from ui.sidebar import Sidebar

    sb = Sidebar("testuser", lambda c: None)
    sb.set_active("Music")
    assert sb._buttons["Music"].property("active") == "true"
    assert sb._buttons["Video"].property("active") == "false"
    assert sb._buttons["Music"].isChecked()
    assert not sb._buttons["Video"].isChecked()


def test_sidebar_has_no_duplicate_branding():
    """Branding lives in the title bar only, never in the navigation rail."""
    from PySide6.QtWidgets import QLabel

    from ui.sidebar import Sidebar

    sb = Sidebar("testuser", lambda c: None)
    brand_labels = [
        child for child in sb.findChildren(QLabel)
        if child.property("role") == "brand"
    ]
    assert brand_labels == []
    texts = [child.text() for child in sb.findChildren(QLabel)]
    assert "EntertainX" not in texts


def test_content_area_switches_pages_and_tabs():
    from ui.content_area import ContentArea

    ca = ContentArea()
    ca.show_category("Music")
    assert ca.current_page().__class__.__name__ == "MusicPage"
    assert ca._tab_bar.isVisibleTo(ca)  # the sub-tab strip keeps a stable height

    ca.show_category("Games")
    ca._switch_subtab(2)
    assert ca.current_page().__class__.__name__ == "BrowseGamesPage"
    assert ca.current_tab_index() == 2
    assert ca._tab_buttons[2].property("active") == "true"


def test_content_area_passes_user_to_settings():
    from PySide6.QtWidgets import QLabel

    from ui.content_area import ContentArea

    ca = ContentArea(
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
    window.do_logout()
    assert auth.logged_out
    assert calls == [True]



def test_regular_sidebar_has_no_admin():
    from ui.sidebar import Sidebar

    sb = Sidebar("testuser", lambda c: None)
    assert "Admin" not in sb._buttons


def test_admin_sidebar_has_admin():
    from ui.sidebar import Sidebar

    sb = Sidebar("testuser", lambda c: None, is_admin=True)
    assert "Admin" in sb._buttons


def test_regular_content_area_has_no_admin():
    from ui.content_area import ContentArea

    ca = ContentArea(user={"id": 1, "username": "user", "role": "user"})
    assert "Admin" not in ca._categories


def test_admin_content_area_has_admin():
    import sqlite3
    from auth.auth_manager import AuthManager
    from database.db import init_db
    from ui.content_area import ContentArea

    conn = sqlite3.connect(":memory:")
    init_db(conn)
    auth = AuthManager(conn)
    auth.register("admin", "admin@test.com", "AdminPass1!")
    conn.execute("UPDATE users SET role = 'admin' WHERE username = 'admin'")
    conn.commit()
    auth.login("admin", "AdminPass1!")

    ca = ContentArea(
        user={"id": 1, "username": "admin", "role": "admin"},
        auth_manager=auth,
    )
    assert "Admin" in ca._categories
    conn.close()


def test_admin_main_window_has_admin_sidebar_and_content():
    import sqlite3
    from auth.auth_manager import AuthManager
    from database.db import init_db
    from ui.main_window import MainWindow

    conn = sqlite3.connect(":memory:")
    init_db(conn)
    auth = AuthManager(conn)
    auth.register("admin", "admin@test.com", "AdminPass1!")
    conn.execute("UPDATE users SET role = 'admin' WHERE username = 'admin'")
    conn.commit()
    auth.login("admin", "AdminPass1!")

    user = auth.current_user
    window = MainWindow(auth, user, on_logout=lambda: None)
    assert "Admin" in window.sidebar._buttons
    assert "Admin" in window.content._categories
    conn.close()
