from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QEvent, QPropertyAnimation, Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from auth.auth_manager import AuthManager
from auth.preferences import LoginPreferences
from theme import theme_manager as theme
from ui.components.auth_stage import AuthStage
from ui.components.fields import (
    FormField,
    IconLineEdit,
    PasswordLineEdit,
    PasswordStrength,
)
from ui.components.icons import make_icon
from ui.components.surfaces import InlineBanner, label

FORM_MAX_WIDTH = 392
SPLIT_MIN_WIDTH = 1040


class _SegmentSwitch(QFrame):
    """Two-state switch whose indicator slides to the active segment."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setProperty("role", "segmented")
        self._buttons: list[QPushButton] = []
        self._index = 0

        self._indicator = QFrame(self)
        self._indicator.setProperty("role", "segmentIndicator")
        self._indicator.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents, True
        )

        self._row = QHBoxLayout(self)
        inset = theme.SPACE_XS - 1
        self._row.setContentsMargins(inset, inset, inset, inset)
        self._row.setSpacing(theme.SPACE_XS - 2)

        self._slide = QPropertyAnimation(self._indicator, b"geometry", self)
        self._slide.setDuration(170)
        self._slide.setEasingCurve(QEasingCurve.Type.OutCubic)

    def add_segment(self, text: str, handler) -> QPushButton:
        button = QPushButton(text)
        button.setProperty("variant", "segment")
        button.setProperty("active", False)
        button.setMinimumHeight(32)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.clicked.connect(handler)
        self._buttons.append(button)
        self._row.addWidget(button, 1)
        return button

    def set_active(self, index: int, animate: bool = False) -> None:
        self._index = index
        for position, button in enumerate(self._buttons):
            button.setProperty("active", position == index)
            theme.restyle(button)

        target = self._segment_rect(index)
        self._slide.stop()
        if animate and self.isVisible() and target.isValid():
            self._slide.setStartValue(self._indicator.geometry())
            self._slide.setEndValue(target)
            self._slide.start()
        else:
            self._indicator.setGeometry(target)

    def _segment_rect(self, index: int):
        if not 0 <= index < len(self._buttons):
            return self._indicator.geometry()
        return self._buttons[index].geometry()

    def resizeEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        super().resizeEvent(event)
        self._slide.stop()
        self._indicator.setGeometry(self._segment_rect(self._index))


class LoginWindow(QWidget):
    """Sign-in and registration surface with a shared split layout.

    Wide windows show the brand stage beside the form; narrow windows drop the
    stage and centre the same form so the window minimum size stays usable.
    """

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
        self._split: bool | None = None
        self._blur_checks: dict[QWidget, object] = {}

        self.setObjectName("AuthBackdrop")
        self._build()
        self._restore_remembered()
        self._apply_layout_mode(self.width())

    # ── Layout ──────────────────────────────────────────────────────────────
    def _build(self) -> None:
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._stage = AuthStage()
        root.addWidget(self._stage, 11)

        self._pane = QFrame()
        self._pane.setProperty("role", "authPane")
        self._pane.setProperty("split", False)
        self._pane.setFrameShape(QFrame.Shape.NoFrame)
        root.addWidget(self._pane, 9)

        pane = QVBoxLayout(self._pane)
        pane.setContentsMargins(0, 0, 0, 0)
        pane.setSpacing(0)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self._scroll.viewport().setAutoFillBackground(False)
        pane.addWidget(self._scroll)

        host = QWidget()
        host.setObjectName("AuthFormHost")
        host.setAutoFillBackground(False)
        column = QVBoxLayout(host)
        column.setContentsMargins(
            theme.SPACE_XXL, theme.SPACE_XL, theme.SPACE_XXL, theme.SPACE_XL
        )
        column.setSpacing(0)
        self._host_layout = column

        self._form_column = QWidget()
        self._form_column.setFixedWidth(FORM_MAX_WIDTH)
        self._form_column.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Maximum
        )
        stack = QVBoxLayout(self._form_column)
        stack.setContentsMargins(0, 0, 0, 0)
        stack.setSpacing(0)

        self._tabs = self._build_tabs()
        self._login_card = self._build_login_card()
        self._register_card = self._build_register_card()
        self._register_card.setVisible(False)

        stack.addWidget(self._tabs)
        stack.addSpacing(theme.SPACE_XL + 6)
        stack.addWidget(self._login_card)
        stack.addWidget(self._register_card)

        column.addWidget(
            self._form_column,
            0,
            Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter,
        )
        column.addStretch(1)
        column.addWidget(self._build_footer())
        self._scroll.setWidget(host)

        self._sync_tabs(0)

    def _build_footer(self) -> QFrame:
        """Quiet trust line pinned to the bottom of the form host."""
        footer = QFrame()
        footer.setProperty("role", "authFooter")
        row = QHBoxLayout(footer)
        row.setContentsMargins(0, theme.SPACE_MD, 0, 0)
        row.setSpacing(theme.SPACE_SM)

        glyph = QLabel()
        glyph.setPixmap(make_icon("lock", theme.TEXT_MUTED, 13).pixmap(13, 13))
        glyph.setFixedSize(13, 13)

        row.addStretch(1)
        row.addWidget(glyph, 0, Qt.AlignmentFlag.AlignVCenter)
        row.addWidget(
            label("Your account and lists stay on this device.", "muted", wrap=False)
        )
        row.addStretch(1)
        return footer

    def _form(self) -> tuple[QWidget, QVBoxLayout]:
        """A form block: full-width fields on the pane ground, no nested card."""
        form = QWidget()
        form.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        body = QVBoxLayout(form)
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(theme.SPACE_MD + 2)
        return form, body

    @staticmethod
    def _heading(title: str, support: str) -> QWidget:
        block = QWidget()
        stack = QVBoxLayout(block)
        stack.setContentsMargins(0, 0, 0, 0)
        stack.setSpacing(0)

        rule = QFrame()
        rule.setProperty("role", "accentRule")
        rule.setFixedSize(36, 3)
        stack.addWidget(rule)
        stack.addSpacing(theme.SPACE_MD)

        # A fixed-height title can't be squeezed by the scroll host on short
        # windows; word-wrapped labels otherwise lose their descenders.
        title_label = label(title, "h1", wrap=False)
        title_label.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed
        )
        stack.addWidget(title_label)
        stack.addSpacing(theme.SPACE_XS + 2)
        stack.addWidget(label(support, "muted"))
        return block

    # ── Mode switch ─────────────────────────────────────────────────────────
    def _build_tabs(self) -> _SegmentSwitch:
        tabs = _SegmentSwitch()
        self._login_tab = tabs.add_segment("Sign in", self._go_login)
        self._register_tab = tabs.add_segment("Create account", self._go_register)
        return tabs

    def _sync_tabs(self, index: int) -> None:
        self._tabs.set_active(index, animate=self._tabs.isVisible())
        self._scroll.verticalScrollBar().setValue(0)

    # ── Login form ──────────────────────────────────────────────────────────
    def _build_login_card(self) -> QWidget:
        form, body = self._form()

        body.addWidget(
            self._heading(
                "Welcome back",
                "Your lists and ratings are right where you left them.",
            )
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
        self._login_button.setMinimumHeight(48)
        self._login_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._login_button.clicked.connect(self._do_login)
        body.addWidget(self._login_button)

        self._login_user.returnPressed.connect(lambda: self._login_pass.setFocus())
        self._login_pass.returnPressed.connect(self._do_login)

        # A failed attempt describes what was submitted, so drop the field
        # errors as soon as the user edits them instead of leaving them red.
        self._login_user.textChanged.connect(
            lambda _text: self._user_field.clear_error()
        )
        self._login_pass.textChanged.connect(
            lambda _text: self._pass_field.clear_error()
        )
        return form

    # ── Register form ───────────────────────────────────────────────────────
    def _build_register_card(self) -> QWidget:
        form, body = self._form()

        body.addWidget(
            self._heading(
                "Create your account",
                "One account for the movies, music, and games you keep.",
            )
        )
        body.addSpacing(theme.SPACE_SM)

        self._register_error = InlineBanner("error")
        body.addWidget(self._register_error)

        self._reg_user = IconLineEdit("user", "Choose a username")
        self._reg_user_field = FormField(
            "Username", self._reg_user, hint="3-20 letters or numbers."
        )
        body.addWidget(self._reg_user_field)

        self._reg_email = IconLineEdit("mail", "you@example.com")
        self._reg_email_field = FormField("Email", self._reg_email)
        body.addWidget(self._reg_email_field)

        self._reg_pass = PasswordLineEdit("Choose a password")
        self._strength = PasswordStrength(self._reg_pass, minimum=6)
        self._reg_pass_field = FormField(
            "Password", self._reg_pass, accessory=self._strength
        )
        body.addWidget(self._reg_pass_field)

        self._reg_confirm = PasswordLineEdit("Repeat your password")
        self._reg_confirm_field = FormField("Confirm password", self._reg_confirm)
        body.addWidget(self._reg_confirm_field)

        body.addSpacing(theme.SPACE_XS)
        self._register_button = QPushButton("Create account")
        self._register_button.setProperty("variant", "primary")
        self._register_button.setMinimumHeight(48)
        self._register_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._register_button.clicked.connect(self._do_register)
        body.addWidget(self._register_button)

        for field in (
            self._reg_user,
            self._reg_email,
            self._reg_pass,
            self._reg_confirm,
        ):
            field.returnPressed.connect(self._do_register)
        self._wire_register_validation()
        return form

    # ── Live validation ─────────────────────────────────────────────────────
    def _wire_register_validation(self) -> None:
        """Validate on blur, and drop stale errors as soon as a fix lands.

        ``FocusOut`` is used instead of ``editingFinished`` because the latter
        also fires on Enter, which would clear the errors a failed submit just
        set (e.g. "Username already taken").
        """
        for widget, field, validator in (
            (self._reg_user, self._reg_user_field, self._auth.validate_username),
            (self._reg_email, self._reg_email_field, self._auth.validate_email),
            (self._reg_pass, self._reg_pass_field, self._auth.validate_password),
        ):
            self._blur_checks[widget] = (
                lambda w=widget, f=field, v=validator: self._check_on_blur(w, f, v)
            )
            widget.installEventFilter(self)
            widget.textChanged.connect(
                lambda _text, w=widget, f=field, v=validator: self._clear_if_fixed(
                    w, f, v
                )
            )

        self._blur_checks[self._reg_confirm] = self._check_confirm_on_blur
        self._reg_confirm.installEventFilter(self)
        self._reg_confirm.textChanged.connect(self._clear_confirm_if_fixed)
        self._reg_pass.textChanged.connect(lambda _text: self._clear_confirm_if_fixed())

    def _check_on_blur(self, widget, wrapper, validator) -> None:
        text = widget.text().strip()
        if not text:
            wrapper.clear_error()
            return
        error = validator(text)
        if error:
            wrapper.set_error(error)
        else:
            wrapper.clear_error()

    def _clear_if_fixed(self, widget, wrapper, validator) -> None:
        if not wrapper.has_error:
            return
        text = widget.text().strip()
        if not text or not validator(text):
            wrapper.clear_error()

    def _check_confirm_on_blur(self) -> None:
        confirm = self._reg_confirm.text()
        if not confirm:
            self._reg_confirm_field.clear_error()
        elif confirm != self._reg_pass.text():
            self._reg_confirm_field.set_error("Passwords do not match")
        else:
            self._reg_confirm_field.clear_error()

    def _clear_confirm_if_fixed(self) -> None:
        if not self._reg_confirm_field.has_error:
            return
        confirm = self._reg_confirm.text()
        if not confirm or confirm == self._reg_pass.text():
            self._reg_confirm_field.clear_error()

    def eventFilter(self, obj, event) -> bool:  # noqa: N802 (Qt naming)
        check = self._blur_checks.get(obj)
        if check is not None and event.type() == QEvent.Type.FocusOut:
            check()
        return super().eventFilter(obj, event)

    # ── Page switching ──────────────────────────────────────────────────────
    def _switch(self, index: int) -> None:
        self._login_card.setVisible(index == 0)
        self._register_card.setVisible(index == 1)
        self._sync_tabs(index)
        self._update_vertical_rhythm()

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

    # ── Responsive composition ──────────────────────────────────────────────
    def _apply_layout_mode(self, width: int) -> None:
        split = width >= SPLIT_MIN_WIDTH
        if split == self._split:
            return
        self._split = split
        self._stage.setVisible(split)
        self._pane.setProperty("split", split)
        theme.restyle(self._pane)
        self._update_vertical_rhythm()

    def _update_vertical_rhythm(self) -> None:
        """Keep the mode switch at one height in both forms.

        The login form is shorter than the register form, so centring each one
        separately would make the tab strip jump on every switch. The offset is
        derived from the taller form instead, clamped to 24-96px. The form
        column is also pinned to the visible form's measured height so the
        scroll host cannot squeeze wrapped headings on short windows.
        """
        chrome = self._tabs.sizeHint().height() + theme.SPACE_XL + 6
        tallest = chrome + max(
            self._form_height(self._login_card),
            self._form_height(self._register_card),
        )
        available = max(self.height(), 1)
        offset = max(
            theme.SPACE_XL,
            min(theme.SPACE_XXL * 3, (available - tallest) // 2),
        )
        side = theme.SPACE_XXL if self._split else theme.SPACE_XL
        self._host_layout.setContentsMargins(
            side, offset, side, theme.SPACE_XL
        )

        # The host layout sizes a Maximum-policy column to its minimum hint,
        # which squeezes wrapped headings by a few pixels. Pin the column to
        # what the visible form actually needs so no label is compressed.
        visible = self._register_card if self.current_page() else self._login_card
        self._form_column.setMinimumHeight(chrome + self._form_height(visible))

    @staticmethod
    def _form_height(form: QWidget) -> int:
        """Height a form needs at its fixed width, wrapped headings included."""
        hint = form.sizeHint().height()
        if form.hasHeightForWidth():
            hint = max(hint, form.heightForWidth(FORM_MAX_WIDTH))
        return hint

    def resizeEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        super().resizeEvent(event)
        self._apply_layout_mode(self.width())
        self._update_vertical_rhythm()

    def showEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        super().showEvent(event)
        # Fonts and stylesheets are polished on first show; recompute once the
        # forms report their final size hints.
        self._update_vertical_rhythm()

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
