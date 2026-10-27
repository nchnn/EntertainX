import sys
from PySide6.QtWidgets import QApplication, QMainWindow
from database.db import get_connection, init_db
from auth.auth_manager import AuthManager
from ui.login_window import LoginWindow
from theme.theme_manager import apply_theme


class MainApp(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("EntertainX")
        self.resize(1200, 800)
        conn = get_connection()
        init_db(conn)
        self._auth = AuthManager(conn)
        self._show_login()

    def _show_login(self) -> None:
        login_win = LoginWindow(self._auth, self._on_login_success)
        self.setCentralWidget(login_win)

    def _on_login_success(self, user: dict) -> None:
        from ui.main_window import MainWindow
        main_win = MainWindow(self._auth, user, on_logout=self._do_logout)
        self.setCentralWidget(main_win)

    def _do_logout(self) -> None:
        self._auth.logout()
        self._show_login()


def main() -> None:
    app = QApplication(sys.argv)
    apply_theme(app)
    window = MainApp()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
