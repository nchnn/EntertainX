import sys

from PySide6.QtWidgets import QApplication

from auth.auth_manager import AuthManager
from auth.preferences import LoginPreferences
from database.db import get_connection, init_db
from theme.theme_manager import apply_theme
from ui.components.icons import app_icon
from ui.frameless import FramelessWindow
from ui.login_window import LoginWindow


class MainApp(FramelessWindow):
    """Top-level application window; swaps auth and main views in place.

    On start-up it resumes a session remembered with "Remember me" when the
    saved token is still valid; otherwise it opens the sign-in screen.
    """

    def __init__(self, connection=None, preferences: LoginPreferences | None = None) -> None:
        super().__init__("EntertainX")
        self.setWindowIcon(app_icon())
        self.resize(1240, 820)
        self._center_on_screen()

        conn = connection if connection is not None else get_connection()
        init_db(conn)
        self._auth = AuthManager(conn)
        self._prefs = preferences if preferences is not None else LoginPreferences()
        self._start()

    def _center_on_screen(self) -> None:
        screen = QApplication.primaryScreen()
        if screen is None:
            return
        area = screen.availableGeometry()
        width = min(1240, max(self.minimumWidth(), area.width() - 80))
        height = min(820, max(self.minimumHeight(), area.height() - 80))
        self.resize(width, height)

        frame = self.frameGeometry()
        frame.moveCenter(area.center())
        top_left = frame.topLeft()
        top_left.setX(
            max(area.left(), min(top_left.x(), area.right() - frame.width() + 1))
        )
        top_left.setY(
            max(area.top(), min(top_left.y(), area.bottom() - frame.height() + 1))
        )
        self.move(top_left)

    def _start(self) -> None:
        """Resume a remembered session, or show the sign-in screen."""
        token = self._prefs.remember_token()
        if not token:
            self._show_login()
            return

        ok, result = self._auth.login_with_token(token)
        if ok:
            self._on_login_success(result)
            return

        # Expired, revoked, or tampered with: forget it and say why.
        self._prefs.clear_token()
        self._show_login(notice=f"{result} Please sign in again.")

    def _show_login(self, notice: str = "") -> None:
        self.set_content(
            LoginWindow(
                self._auth,
                self._on_login_success,
                preferences=self._prefs,
                notice=notice,
            )
        )

    def _on_login_success(self, user: dict) -> None:
        from ui.main_window import MainWindow

        main_window = MainWindow(self._auth, user, on_logout=self._return_to_login)
        self.set_content(main_window)
        main_window.content.top_bar.set_user_session(
            user=user,
            on_theme=main_window.open_theme_dialog,
            on_settings=lambda: main_window.content.show_category("Settings"),
            on_logout=main_window.do_logout,
        )

    def _return_to_login(self) -> None:
        # MainWindow has already cleared the session via the auth manager.
        # Signing out also ends the remembered session on this device; the
        # username stays pre-filled so signing back in is one field shorter.
        token = self._prefs.remember_token()
        if token:
            self._auth.revoke_remember_token(token)
            self._prefs.clear_token()
        self._show_login()


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("EntertainX")
    app.setOrganizationName("EntertainX")
    app.setWindowIcon(app_icon())
    apply_theme(app)
    window = MainApp()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
