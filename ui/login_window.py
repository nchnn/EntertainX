from __future__ import annotations

from PySide6.QtCore import QEvent, Qt, QTimer
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedLayout,
    QVBoxLayout,
    QWidget,
)

from auth.auth_manager import AuthManager
from auth.background import run_in_background
from auth.preferences import LoginPreferences
from theme import theme_manager as theme
from ui.components import motion
from ui.components.auth.controls import (
    AnimatedCheckBox,
    LoadingButton,
    SegmentSwitch,
    letter_spaced,
)
from ui.components.auth.stage import AuthStage
from ui.components.form_fields import (
    FormField,
    IconLineEdit,
    PasswordLineEdit,
    PasswordStrength,
)
from ui.components.icons import make_icon
from ui.components.layout import InlineBanner, label

FORM_WIDTH = 408
MOTION_PAD = 28  # room beside and below the form so sliding content is not clipped
SPLIT_MIN_WIDTH = 1040
SUCCESS_HOLD_MS = 420  # let the check mark land before the window fades out
EXIT_FADE_MS = 260
REMEMBER_HINT = "Stays signed in for 30 days"
REMEMBER_TIP = (
    "Stay signed in on this device for 30 days. Signing out ends it, "
    "and your password is never stored."
)

# (eyebrow, title, supporting line) for each mode.
COPY = {
    "login": (
        "SIGN IN TO ENTERTAINX",
        "Welcome back.",
        "Your lists, ratings, and playlists are right where you left them.",
    ),
    "register": (
        "JOIN ENTERTAINX",
        "Start your collection.",
        "One free account for every film, album, and game you keep.",
    ),
}


class LoginWindow(QWidget):
    """Sign-in and registration surface with a shared split layout.

    Wide windows show the brand stage beside the form; narrow windows drop the
    stage and centre the same form so the window minimum size stays usable.

    ``notice`` is an optional line shown above the sign-in form, used when a
    remembered session could not be resumed.
    """

    def __init__(
        self,
        auth_manager: AuthManager,
        on_login_success,
        preferences: LoginPreferences | None = None,
        notice: str = "",
    ) -> None:
        super().__init__()
        self._auth = auth_manager
        self._on_success = on_login_success
        self._prefs = preferences if preferences is not None else LoginPreferences()
        self._busy = False
        self._split: bool | None = None
        self._page = 0
        self._pending: tuple | None = None
        self._intro_played = False
        self._exit_user: dict | None = None
        self._blur_checks: dict[QWidget, object] = {}

        self._exit_timer = QTimer(self)
        self._exit_timer.setSingleShot(True)
        self._exit_timer.timeout.connect(self._fade_out)

        self.setObjectName("AuthBackdrop")
        self._build()
        self._restore_remembered()
        if notice:
            self._login_info.show_message(notice)
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
            theme.SPACE_XL, theme.SPACE_XL, theme.SPACE_XL, theme.SPACE_LG
        )
        column.setSpacing(0)
        self._host_layout = column

        # A widget's painting is clipped to its parent, so the column is wider
        # than the form by MOTION_PAD each side (and below) to give the
        # slide-fade somewhere to travel.
        self._form_column = QWidget()
        self._form_column.setFixedWidth(FORM_WIDTH + 2 * MOTION_PAD)
        self._form_column.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Maximum
        )
        stack = QVBoxLayout(self._form_column)
        stack.setContentsMargins(MOTION_PAD, 0, MOTION_PAD, MOTION_PAD)
        stack.setSpacing(0)

        self._tabs = self._build_tabs()
        self._login_card = self._build_login_card()
        self._register_card = self._build_register_card()

        # A stacked layout is as tall as its tallest page, so the mode switch
        # above never jumps when the pages differ in height.
        self._pages = QWidget()
        self._pages_layout = QStackedLayout(self._pages)
        self._pages_layout.setContentsMargins(0, 0, 0, 0)
        self._pages_layout.addWidget(self._login_card)
        self._pages_layout.addWidget(self._register_card)
        self._pages_layout.setCurrentIndex(0)

        stack.addWidget(self._tabs)
        stack.addSpacing(theme.SPACE_XL + 4)
        stack.addWidget(self._pages)

        column.addStretch(1)
        column.addWidget(
            self._form_column,
            0,
            Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter,
        )
        column.addStretch(1)
        self._footer = self._build_footer()
        column.addWidget(self._footer)
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
    def _heading(eyebrow: str, title: str, support: str) -> QWidget:
        block = QWidget()
        stack = QVBoxLayout(block)
        stack.setContentsMargins(0, 0, 0, 0)
        stack.setSpacing(0)

        stack.addWidget(letter_spaced(label(eyebrow, "authEyebrow", wrap=False), 2.0))
        stack.addSpacing(theme.SPACE_SM + 2)

        # A fixed-height title can't be squeezed by the scroll host on short
        # windows; word-wrapped labels otherwise lose their descenders.
        title_label = label(title, "authTitle", wrap=False)
        title_label.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed
        )
        stack.addWidget(title_label)
        stack.addSpacing(theme.SPACE_SM)
        stack.addWidget(label(support, "authSupport"))
        return block

    @staticmethod
    def _row(*widgets: QWidget, stretch_after: int | None = None) -> QWidget:
        """Group widgets into one horizontal row that behaves as a single item."""
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(theme.SPACE_XS)
        for index, widget in enumerate(widgets):
            layout.addWidget(widget, 0, Qt.AlignmentFlag.AlignVCenter)
            if stretch_after is not None and index == stretch_after:
                layout.addStretch(1)
        return row

    def _switch_prompt(self, prompt: str, action: str, handler) -> tuple[QWidget, QPushButton]:
        """"New here? Create an account" style line under a form."""
        button = QPushButton(action)
        button.setProperty("variant", "link")
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.clicked.connect(handler)

        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(theme.SPACE_XS)
        layout.addStretch(1)
        layout.addWidget(label(prompt, "muted", wrap=False), 0, Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(button, 0, Qt.AlignmentFlag.AlignVCenter)
        layout.addStretch(1)
        return row, button

    # ── Mode switch ─────────────────────────────────────────────────────────
    def _build_tabs(self) -> SegmentSwitch:
        tabs = SegmentSwitch()
        self._login_tab = tabs.add_segment("Sign in", self._go_login)
        self._register_tab = tabs.add_segment("Create account", self._go_register)
        return tabs

    def _sync_tabs(self, index: int) -> None:
        self._tabs.set_active(index, animate=self._tabs.isVisible())

    # ── Login form ──────────────────────────────────────────────────────────
    def _build_login_card(self) -> QWidget:
        form, body = self._form()

        body.addWidget(self._heading(*COPY["login"]))
        body.addSpacing(theme.SPACE_SM)

        self._login_info = InlineBanner("info")
        self._login_success = InlineBanner("success")
        self._login_error = InlineBanner("error")
        body.addWidget(self._login_info)
        body.addWidget(self._login_success)
        body.addWidget(self._login_error)

        self._login_user = IconLineEdit("user", "Your username")
        self._user_field = FormField("Username", self._login_user)
        body.addWidget(self._user_field)

        self._login_pass = PasswordLineEdit("Your password")
        self._pass_field = FormField("Password", self._login_pass)
        body.addWidget(self._pass_field)

        self._remember = AnimatedCheckBox("Remember me")
        self._remember.setToolTip(REMEMBER_TIP)
        self._remember.toggled.connect(self._on_remember_toggled)
        self._remember_hint = label("", "caption", wrap=False)
        self._remember_hint.setToolTip(REMEMBER_TIP)
        self._options_row = self._row(
            self._remember, self._remember_hint, stretch_after=0
        )
        body.addWidget(self._options_row)

        body.addSpacing(theme.SPACE_XS)
        self._login_button = LoadingButton("Sign in")
        self._login_button.setProperty("variant", "hero")
        self._login_button.setMinimumHeight(50)
        self._login_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._login_button.clicked.connect(self._do_login)
        body.addWidget(self._login_button)

        self._to_register_row, self._to_register_link = self._switch_prompt(
            "New to EntertainX?", "Create an account", self._go_register
        )
        body.addWidget(self._to_register_row)
        body.addStretch(1)

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

        body.addWidget(self._heading(*COPY["register"]))
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
        self._register_button = LoadingButton("Create account")
        self._register_button.setProperty("variant", "hero")
        self._register_button.setMinimumHeight(50)
        self._register_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._register_button.clicked.connect(self._do_register)
        body.addWidget(self._register_button)

        self._to_login_row, self._to_login_link = self._switch_prompt(
            "Already have an account?", "Sign in", self._go_login
        )
        body.addWidget(self._to_login_row)
        body.addStretch(1)

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
    def _switch(self, index: int, then=None) -> None:
        """Move to a form with a slide-fade; ``then`` runs once it is in place."""
        direction = 1 if index > self._page else -1
        changed = index != self._pages_layout.currentIndex()
        self._page = index
        self._sync_tabs(index)
        self._stage.set_mode(index)

        def apply() -> None:
            self._pages_layout.setCurrentIndex(index)
            self._scroll.verticalScrollBar().setValue(0)
            self._pin_height()
            if then is not None:
                then()

        if not changed:
            apply()
            return
        motion.swap(
            self._pages,
            apply,
            out_ms=130,
            in_ms=320,
            dx_out=-18.0 * direction,
            dx_in=18.0 * direction,
        )

    def current_page(self) -> int:
        return self._page

    def _go_login(self) -> None:
        self._clear_banners()
        self._clear_field_errors()
        self._switch(0, then=lambda: self._focus_first_empty(0))

    def _go_register(self) -> None:
        self._clear_banners()
        self._clear_field_errors()
        self._switch(1, then=lambda: self._focus_first_empty(1))

    def _clear_banners(self) -> None:
        for banner in (
            self._login_info,
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

    def _flash(self, banner: InlineBanner, text: str) -> None:
        """Show feedback with a soft entrance rather than popping in."""
        banner.show_message(text)
        motion.reveal(banner, duration=280, rise=6.0)
        self._pin_height()

    # ── Responsive composition ──────────────────────────────────────────────
    def _apply_layout_mode(self, width: int) -> None:
        split = width >= SPLIT_MIN_WIDTH
        if split == self._split:
            return
        self._split = split
        self._stage.setVisible(split)
        self._pane.setProperty("split", split)
        theme.restyle(self._pane)
        side = theme.SPACE_XXL if split else theme.SPACE_XL
        self._host_layout.setContentsMargins(
            side, theme.SPACE_XL, side, theme.SPACE_LG
        )
        self._pin_height()

    def _pin_height(self) -> None:
        """Pin the page stack to the height its tallest form needs.

        The host layout sizes a Maximum-policy column to its minimum hint, which
        squeezes wrapped headings by a few pixels. Measuring each form at the
        fixed column width keeps every label at its full height.
        """
        tallest = max(
            self._form_height(self._login_card),
            self._form_height(self._register_card),
        )
        self._pages.setMinimumHeight(tallest)

    @staticmethod
    def _form_height(form: QWidget) -> int:
        """Height a form needs at its fixed width, wrapped headings included."""
        hint = form.sizeHint().height()
        if form.hasHeightForWidth():
            hint = max(hint, form.heightForWidth(FORM_WIDTH))
        return hint

    def resizeEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        super().resizeEvent(event)
        self._apply_layout_mode(self.width())
        self._pin_height()

    def showEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        super().showEvent(event)
        # Fonts and stylesheets are polished on first show; recompute once the
        # forms report their final size hints.
        self._pin_height()
        if not self._intro_played:
            self._intro_played = True
            self._play_intro()

    def _play_intro(self) -> None:
        """Bring the form in item by item once, the first time it is shown."""
        page = self._pages_layout.currentWidget()
        targets = [self._tabs]
        layout = page.layout()
        for index in range(layout.count()):
            widget = layout.itemAt(index).widget()
            if widget is not None and not widget.isHidden():
                targets.append(widget)
        targets.append(self._footer)
        motion.cascade(targets, start=140, step=55, duration=520, rise=16)

    # ── Remember Me ─────────────────────────────────────────────────────────
    def _restore_remembered(self) -> None:
        username = self._prefs.remembered_username()
        enabled = self._prefs.remember_enabled() and bool(username)
        self._remember.setChecked(enabled)
        self._remember_hint.setText(REMEMBER_HINT if enabled else "")
        if username:
            self._login_user.setText(username)
            self._login_pass.setFocus()
        else:
            self._login_user.setFocus()

    def _on_remember_toggled(self, checked: bool) -> None:
        text = REMEMBER_HINT if checked else ""
        if self._remember_hint.text() != text:
            motion.swap(
                self._remember_hint,
                lambda: self._remember_hint.setText(text),
                out_ms=90,
                in_ms=200,
                rise_in=4.0,
            )
        if not checked:
            self._forget_remembered()

    def _forget_remembered(self) -> None:
        """Unticking Remember me ends the saved session as well as the username."""
        token = self._prefs.remember_token()
        if token:
            self._auth.revoke_remember_token(token)
        self._prefs.clear()

    def _store_remember_choice(self, user: dict) -> None:
        """Apply the checkbox after a successful sign-in."""
        stale = self._prefs.remember_token()
        if stale:
            self._auth.revoke_remember_token(stale)

        if self._remember.isChecked():
            token = self._auth.issue_remember_token(user["id"])
            self._prefs.set_remembered_username(user["username"])
            self._prefs.set_remember_token(token)
        else:
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
            motion.shake(self._login_card)
            return

        # The account lookup is a quick read on this thread; the deliberately
        # slow password hash runs on a worker so the button keeps animating.
        record = self._auth.begin_login(username)
        self._pending = (record, bool(password))
        self._set_busy(True, self._login_button, "Signing in\u2026")
        run_in_background(
            lambda: self._auth.verify_login(record, password),
            self._on_login_checked,
            self._on_task_failed,
        )

    def _on_login_checked(self, ok: bool) -> None:
        record, had_password = self._pending or (None, False)
        self._pending = None

        if not ok or record is None:
            self._set_busy(False, self._login_button, "Sign in")
            self._reject_login(had_password)
            return

        user = self._auth.complete_login(record)
        self._store_remember_choice(user)
        self._begin_exit(user)

    def _reject_login(self, had_password: bool) -> None:
        self._flash(self._login_error, "Invalid username or password")
        if not had_password:
            self._pass_field.set_error("Password is required")
        else:
            self._pass_field.set_error("Check your password and try again")
        self._login_pass.selectAll()
        self._login_pass.setFocus()
        motion.shake(self._login_card)

    def _begin_exit(self, user: dict) -> None:
        """Confirm the sign-in, then fade out and hand over to the app."""
        self._login_button.set_state(LoadingButton.SUCCESS, "Welcome back")
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self._exit_user = user
        if not motion.motion_enabled():
            self._on_success(user)
            return
        self._exit_timer.start(SUCCESS_HOLD_MS)

    def _fade_out(self) -> None:
        user = self._exit_user
        motion.conceal(
            self,
            duration=EXIT_FADE_MS,
            drop=0.0,
            on_finished=lambda: self._on_success(user),
        )

    def _on_task_failed(self, _message: str) -> None:
        """A worker raised unexpectedly; never leave the form stuck busy."""
        self._pending = None
        self._set_busy(False, self._login_button, "Sign in")
        self._set_busy(False, self._register_button, "Create account")
        error = self._register_error if self._page else self._login_error
        self._flash(error, "Something went wrong. Please try again.")

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
            motion.shake(self._register_card)
            return

        self._pending = (username, email)
        self._set_busy(True, self._register_button, "Creating account\u2026")
        run_in_background(
            lambda: self._auth.hash_credentials(password),
            self._on_hashed,
            self._on_task_failed,
        )

    def _on_hashed(self, credentials) -> None:
        username, email = self._pending or ("", "")
        self._pending = None
        pw_hash, salt = credentials

        ok, message = self._auth.store_registration(username, email, pw_hash, salt)
        self._set_busy(False, self._register_button, "Create account")

        if not ok:
            lowered = message.lower()
            if "username" in lowered:
                self._reg_user_field.set_error(message)
            elif "email" in lowered:
                self._reg_email_field.set_error(message)
            else:
                self._flash(self._register_error, message)
            motion.shake(self._register_card)
            return

        self._on_registered(username)

    def _on_registered(self, username: str) -> None:
        """Clear the register form and land on Login with visible feedback."""
        self._clear_field_errors()
        for field in (self._reg_user, self._reg_email, self._reg_pass, self._reg_confirm):
            field.clear()
        self._reg_pass.set_password_visible(False)
        self._reg_confirm.set_password_visible(False)

        self._login_user.setText(username)
        self._login_error.clear()
        self._login_success.show_message(
            f"Welcome, {username}. Your account is ready - sign in below."
        )
        self._pass_field.clear_error()
        self._switch(0, then=self._login_pass.setFocus)

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
    def _set_busy(self, busy: bool, button: LoadingButton, text: str) -> None:
        self._busy = busy
        button.set_state(
            LoadingButton.LOADING if busy else LoadingButton.IDLE, text
        )
        self.setCursor(
            Qt.CursorShape.BusyCursor if busy else Qt.CursorShape.ArrowCursor
        )
