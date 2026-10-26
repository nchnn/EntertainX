from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QStackedWidget, QSizePolicy,
)
from PySide6.QtCore import Qt
from auth.auth_manager import AuthManager


class LoginWindow(QWidget):
    def __init__(self, auth_manager: AuthManager, on_login_success) -> None:
        super().__init__()
        self._auth = auth_manager
        self._on_success = on_login_success
        self._stack = QStackedWidget()
        self._stack.addWidget(self._make_login_page())
        self._stack.addWidget(self._make_register_page())
        layout = QVBoxLayout(self)
        layout.addStretch()
        layout.addWidget(self._stack, alignment=Qt.AlignCenter)
        layout.addStretch()

    # ── Login page ──────────────────────────────────────────────────────────
    def _make_login_page(self) -> QWidget:
        page = QWidget()
        vbox = QVBoxLayout(page)
        vbox.setSpacing(10)

        title = QLabel("EntertainX — Login")
        title.setAlignment(Qt.AlignCenter)
        vbox.addWidget(title)

        self._login_user = QLineEdit()
        self._login_user.setPlaceholderText("Username")
        vbox.addWidget(self._login_user)

        self._login_pass = QLineEdit()
        self._login_pass.setPlaceholderText("Password")
        self._login_pass.setEchoMode(QLineEdit.Password)
        vbox.addWidget(self._login_pass)

        btn = QPushButton("Login")
        btn.clicked.connect(self._do_login)
        vbox.addWidget(btn)

        self._login_err = QLabel("")
        self._login_err.setAlignment(Qt.AlignCenter)
        self._login_err.setStyleSheet("color: red;")
        vbox.addWidget(self._login_err)

        link = QLabel('<a href="#">Don\'t have an account? Register</a>')
        link.setAlignment(Qt.AlignCenter)
        link.linkActivated.connect(lambda _: self._switch(1))
        vbox.addWidget(link)

        return page

    # ── Register page ────────────────────────────────────────────────────────
    def _make_register_page(self) -> QWidget:
        page = QWidget()
        vbox = QVBoxLayout(page)
        vbox.setSpacing(10)

        title = QLabel("EntertainX — Register")
        title.setAlignment(Qt.AlignCenter)
        vbox.addWidget(title)

        self._reg_user = QLineEdit()
        self._reg_user.setPlaceholderText("Username")
        vbox.addWidget(self._reg_user)

        self._reg_email = QLineEdit()
        self._reg_email.setPlaceholderText("Email")
        vbox.addWidget(self._reg_email)

        self._reg_pass = QLineEdit()
        self._reg_pass.setPlaceholderText("Password")
        self._reg_pass.setEchoMode(QLineEdit.Password)
        vbox.addWidget(self._reg_pass)

        self._reg_confirm = QLineEdit()
        self._reg_confirm.setPlaceholderText("Confirm Password")
        self._reg_confirm.setEchoMode(QLineEdit.Password)
        vbox.addWidget(self._reg_confirm)

        btn = QPushButton("Register")
        btn.clicked.connect(self._do_register)
        vbox.addWidget(btn)

        self._reg_err = QLabel("")
        self._reg_err.setAlignment(Qt.AlignCenter)
        self._reg_err.setStyleSheet("color: red;")
        vbox.addWidget(self._reg_err)

        link = QLabel('<a href="#">Already have an account? Login</a>')
        link.setAlignment(Qt.AlignCenter)
        link.linkActivated.connect(lambda _: self._switch(0))
        vbox.addWidget(link)

        return page

    # ── Slots ────────────────────────────────────────────────────────────────
    def _switch(self, index: int) -> None:
        self._login_err.setText("")
        self._reg_err.setText("")
        self._stack.setCurrentIndex(index)

    def _do_login(self) -> None:
        username = self._login_user.text()
        password = self._login_pass.text()
        ok, result = self._auth.login(username, password)
        if ok:
            self._on_success(result)
        else:
            self._login_err.setText(result)

    def _do_register(self) -> None:
        if self._reg_pass.text() != self._reg_confirm.text():
            self._reg_err.setText("Passwords do not match")
            return
        ok, msg = self._auth.register(
            self._reg_user.text(),
            self._reg_email.text(),
            self._reg_pass.text(),
        )
        if ok:
            self._reg_err.setStyleSheet("color: green;")
            self._reg_err.setText("Registered! Switching to login…")
            self._switch(0)
            self._reg_err.setStyleSheet("color: red;")
        else:
            self._reg_err.setStyleSheet("color: red;")
            self._reg_err.setText(msg)
