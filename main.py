import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QLabel, QPushButton,
)
from PySide6.QtCore import Qt
from database.db import get_connection, init_db
from auth.auth_manager import AuthManager
from ui.login_window import LoginWindow


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
        placeholder = QWidget()
        vbox = QVBoxLayout(placeholder)
        vbox.setAlignment(Qt.AlignCenter)
        vbox.addWidget(QLabel(f"Welcome, {user['username']}! Main app goes here."))
        logout_btn = QPushButton("Logout")
        logout_btn.clicked.connect(self._do_logout)
        vbox.addWidget(logout_btn)
        self.setCentralWidget(placeholder)

    def _do_logout(self) -> None:
        self._auth.logout()
        self._show_login()


def main() -> None:
    app = QApplication(sys.argv)
    window = MainApp()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
