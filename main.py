import sys

from PySide6.QtWidgets import QApplication

from auth.auth_manager import AuthManager
from database.db import get_connection, init_db
from theme.theme_manager import apply_theme
from ui.components.icons import app_icon
from ui.frameless import FramelessWindow
from ui.login_window import LoginWindow


class MainApp(FramelessWindow):
    """Top-level application window; swaps auth and main views in place."""

    def __init__(self) -> None:
        super().__init__("EntertainX")
        self.setWindowIcon(app_icon())
        self.resize(1240, 820)
        self._center_on_screen()

        conn = get_connection()
        init_db(conn)
        self._auth = AuthManager(conn)
        self._show_login()

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

    def _show_login(self) -> None:
        self.set_content(LoginWindow(self._auth, self._on_login_success))

    def _on_login_success(self, user: dict) -> None:
        from ui.main_window import MainWindow

        self.set_content(
            MainWindow(self._auth, user, on_logout=self._return_to_login)
        )

    def _return_to_login(self) -> None:
        # MainWindow has already cleared the session via the auth manager.
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
