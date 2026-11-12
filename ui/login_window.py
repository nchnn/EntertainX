from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from auth.auth_manager import AuthManager
from auth.preferences import LoginPreferences
from theme import theme_manager as theme
from ui.components.fields import FormField, IconLineEdit, PasswordLineEdit
from ui.components.surfaces import BrandLockup, InlineBanner, label

CARD_MAX_WIDTH = 430


class LoginWindow(QWidget):
    """Sign-in and registration surface with a shared card design."""

    def __init__(
        self,
        auth_manager: AuthManager,
        on_login_success,
        preferences: LoginPreferences | None = None,
    ) -> None:
        super().__init__()
        self._auth = auth_manager
        self._on_success = on_login_success
        self._prefs = preferences if preferences is not None else LoginPreferences()
        self._busy = False

        self.setObjectName("AuthBackdrop")
        self._build()
        self._restore_remembered()

    # ── Layout ──────────────────────────────────────────────────────────────
    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        root.addWidget(scroll)

        canvas = QWidget()
        canvas.setObjectName("AuthBackdrop")
        column = QVBoxLayout(canvas)
        column.setContentsMargins(theme.SPACE_XXL, theme.SPACE_XXL, theme.SPACE_XXL, theme.SPACE_XXL)
        column.setSpacing(theme.SPACE_LG)
        column.addStretch(1)

        self._login_card = self._build_login_card()
        self._register_card = self._build_register_card()
        self._register_card.setVisible(False)

        column.addWidget(self._login_card, 0, Qt.AlignmentFlag.AlignHCenter)
        column.addWidget(self._register_card, 0, Qt.AlignmentFlag.AlignHCenter)
        column.addStretch(1)

        scroll.setWidget(canvas)

    def _base_card(self) -> tuple[QFrame, QVBoxLayout]:
        card = QFrame()
        card.setProperty("role", "card")
        card.setMaximumWidth(CARD_MAX_WIDTH)
        card.setMinimumWidth(400)
        card.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)

        body = QVBoxLayout(card)
        body.setContentsMargins(
            theme.SPACE_XXL, theme.SPACE_XXL, theme.SPACE_XXL, theme.SPACE_XXL
        )
        body.setSpacing(theme.SPACE_MD + 2)
        return card, body

    # ── Login card ──────────────────────────────────────────────────────────
    def _build_login_card(self) -> QFrame:
        card, body = self._base_card()

        body.addWidget(BrandLockup(38, "Stream. Play. Listen."))
        body.addSpacing(theme.SPACE_MD)

        heading = label("Welcome back", "h1", wrap=False)
        body.addWidget(heading)
        body.addWidget(
            label("Sign in to pick up where you left off.", "muted")
        )
        body.addSpacing(theme.SPACE_SM)

        self._login_success = InlineBanner("success")
        self._login_error = InlineBanner("error")
        body.addWidget(self._login_success)
        body.addWidget(self._login_error)

        self._login_user = IconLineEdit("user", "Your username")
        self._user_field = FormField("Username", self._login_user)
        body.addWidget(self._user_field)

        self._login_pass = PasswordLineEdit("Your password")
        self._pass_field = FormField("Password", self._login_pass)
        body.addWidget(self._pass_field)

        options = QHBoxLayout()
        options.setContentsMargins(0, 0, 0, 0)
        options.setSpacing(theme.SPACE_SM)
        self._remember = QCheckBox("Remember my username")
        self._remember.setCursor(Qt.CursorShape.PointingHandCursor)
        self._remember.toggled.connect(self._on_remember_toggled)
        options.addWidget(self._remember)
        options.addStretch(1)
        body.addLayout(options)

        body.addSpacing(theme.SPACE_XS)
        self._login_button = QPushButton("Sign in")
        self._login_button.setProperty("variant", "primary")
        self._login_button.setMinimumHeight(46)
        self._login_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._login_button.clicked.connect(self._do_login)
        body.addWidget(self._login_button)

        body.addSpacing(theme.SPACE_XS)
        footer = QHBoxLayout()
        footer.setContentsMargins(0, 0, 0, 0)
        footer.setSpacing(0)
        footer.addStretch(1)
        footer.addWidget(label("New to EntertainX?", "muted", wrap=False))
        link = QPushButton("Create an account")
        link.setProperty("variant", "link")
        link.setCursor(Qt.CursorShape.PointingHandCursor)
        link.clicked.connect(self._go_register)
        footer.addWidget(link)
        footer.addStretch(1)
        body.addLayout(footer)

        self._login_user.returnPressed.connect(lambda: self._login_pass.setFocus())
        self._login_pass.returnPressed.connect(self._do_login)
        return card

    # ── Register card ───────────────────────────────────────────────────────
    def _build_register_card(self) -> QFrame:
        card, body = self._base_card()

        body.addWidget(BrandLockup(34, "Your EntertainX profile"))
        body.addSpacing(theme.SPACE_SM)

        body.addWidget(label("Create your account", "h1", wrap=False))
        body.addWidget(
            label(
                "One account for movies, music, games, and everything you save.",
                "muted",
            )
        )
        body.addSpacing(theme.SPACE_SM)

        self._register_error = InlineBanner("error")
        body.addWidget(self._register_error)

        self._reg_user = IconLineEdit("user", "3-20 letters or numbers")
        self._reg_user_field = FormField("Username", self._reg_user)
        body.addWidget(self._reg_user_field)

        self._reg_email = IconLineEdit("mail", "you@example.com")
        self._reg_email_field = FormField("Email", self._reg_email)
        body.addWidget(self._reg_email_field)

        self._reg_pass = PasswordLineEdit("At least 6 characters")
        self._reg_pass_field = FormField(
            "Password", self._reg_pass, hint="Use at least 6 characters."
        )
        body.addWidget(self._reg_pass_field)

        self._reg_confirm = PasswordLineEdit("Repeat your password")
        self._reg_confirm_field = FormField("Confirm password", self._reg_confirm)
        body.addWidget(self._reg_confirm_field)

        body.addSpacing(theme.SPACE_XS)
        self._register_button = QPushButton("Create account")
        self._register_button.setProperty("variant", "primary")
        self._register_button.setMinimumHeight(46)
        self._register_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._register_button.clicked.connect(self._do_register)
        body.addWidget(self._register_button)

        footer = QHBoxLayout()
        footer.setContentsMargins(0, 0, 0, 0)
        footer.setSpacing(0)
        footer.addStretch(1)
        footer.addWidget(label("Already have an account?", "muted", wrap=False))
        link = QPushButton("Sign in")
        link.setProperty("variant", "link")
        link.setCursor(Qt.CursorShape.PointingHandCursor)
        link.clicked.connect(self._go_login)
        footer.addWidget(link)
        footer.addStretch(1)
        body.addLayout(footer)

        return card

    # ── Page switching ──────────────────────────────────────────────────────
    def _switch(self, index: int) -> None:
        self._login_card.setVisible(index == 0)
        self._register_card.setVisible(index == 1)

    def current_page(self) -> int:
        return 0 if not self._login_card.isHidden() else 1

    def _go_login(self) -> None:
        self._clear_banners()
        self._clear_field_errors()
        self._switch(0)
        self._focus_first_empty(0)

    def _go_register(self) -> None:
        self._clear_banners()
        self._clear_field_errors()
        self._switch(1)
        self._focus_first_empty(1)

    def _clear_banners(self) -> None:
        for banner in (
            self._login_success,
            self._login_error,
            self._register_error,
        ):
            banner.clear()

    def _clear_field_errors(self) -> None:
        for field in (
            self._user_field,
            self._pass_field,
            self._reg_user_field,
            self._reg_email_field,
            self._reg_pass_field,
            self._reg_confirm_field,
        ):
            field.clear_error()

    def _focus_first_empty(self, page: int) -> None:
        if page == 0:
            target = self._login_user if not self._login_user.text() else self._login_pass
        else:
            target = self._reg_user
        target.setFocus()

    # ── Remember Me ─────────────────────────────────────────────────────────
    def _restore_remembered(self) -> None:
        username = self._prefs.remembered_username()
        enabled = self._prefs.remember_enabled() and bool(username)
        self._remember.setChecked(enabled)
        if username:
            self._login_user.setText(username)
            self._login_pass.setFocus()
        else:
            self._login_user.setFocus()

    def _on_remember_toggled(self, checked: bool) -> None:
        if not checked:
            self._prefs.clear()

    # ── Login ───────────────────────────────────────────────────────────────
    def _do_login(self) -> None:
        if self._busy:
            return
        self._clear_banners()
        self._clear_field_errors()

        username = self._login_user.text().strip()
        password = self._login_pass.text()
        if not username:
            self._user_field.set_error("Username is required")
            self._login_user.setFocus()
            return

        self._set_busy(True, self._login_button, "Signing in...")
        try:
            ok, result = self._auth.login(username, password)
        finally:
            self._set_busy(False, self._login_button, "Sign in")

        if ok:
            if self._remember.isChecked():
                self._prefs.set_remembered_username(username)
            else:
                self._prefs.clear()
            self._on_success(result)
            return

        self._login_error.show_message(str(result))
        if not password:
            self._pass_field.set_error("Password is required")
        else:
            self._pass_field.set_error("Check your password and try again")
        self._login_pass.selectAll()
        self._login_pass.setFocus()

    # ── Register ────────────────────────────────────────────────────────────
    def _do_register(self) -> None:
        if self._busy:
            return
        self._clear_banners()
        self._clear_field_errors()

        username = self._reg_user.text().strip()
        email = self._reg_email.text().strip()
        password = self._reg_pass.text()

        errors = self._auth.validate_registration(username, email, password)
        if "username" in errors:
            self._reg_user_field.set_error(errors["username"])
        if "email" in errors:
            self._reg_email_field.set_error(errors["email"])
        if "password" in errors:
            self._reg_pass_field.set_error(errors["password"])

        if self._reg_confirm.text() != password:
            self._reg_confirm_field.set_error("Passwords do not match")
        elif not errors:
            self._reg_confirm_field.clear_error()

        if errors or self._reg_confirm_field.has_error:
            self._focus_first_invalid()
            return

        self._set_busy(True, self._register_button, "Creating account...")
        try:
            ok, message = self._auth.register(username, email, password)
        finally:
            self._set_busy(False, self._register_button, "Create account")

        if not ok:
            lowered = message.lower()
            if "username" in lowered:
                self._reg_user_field.set_error(message)
            elif "email" in lowered:
                self._reg_email_field.set_error(message)
            else:
                self._register_error.show_message(message)
            return

        self._on_registered(username)

    def _on_registered(self, username: str) -> None:
        """Clear the register form and land on Login with visible feedback."""
        self._clear_field_errors()
        for field in (self._reg_user, self._reg_email, self._reg_pass, self._reg_confirm):
            field.clear()
        self._reg_pass.set_password_visible(False)
        self._reg_confirm.set_password_visible(False)

        self._switch(0)
        self._login_user.setText(username)
        self._login_error.clear()
        self._login_success.show_message(
            f"Welcome, {username}. Your account is ready - sign in below."
        )
        self._pass_field.clear_error()
        self._login_pass.setFocus()

    def _focus_first_invalid(self) -> None:
        for field in (
            self._reg_user_field,
            self._reg_email_field,
            self._reg_pass_field,
            self._reg_confirm_field,
        ):
            if field.has_error:
                field.field.setFocus()
                return

    # ── Helpers ─────────────────────────────────────────────────────────────
    def _set_busy(self, busy: bool, button: QPushButton, text: str) -> None:
        self._busy = busy
        button.setEnabled(not busy)
        button.setText(text)
        self.setCursor(
            Qt.CursorShape.BusyCursor if busy else Qt.CursorShape.ArrowCursor
        )
