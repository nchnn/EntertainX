from ui.login_window import LoginWindow


def _window(auth, prefs, on_success=None):
    return LoginWindow(auth, on_success or (lambda user: None), preferences=prefs)


def _fill_register(window, username, email, password, confirm=None):
    window._reg_user.setText(username)
    window._reg_email.setText(email)
    window._reg_pass.setText(password)
    window._reg_confirm.setText(password if confirm is None else confirm)


def test_login_page_is_default(auth_env, app):
    auth, prefs = auth_env
    window = _window(auth, prefs)
    assert window.current_page() == 0
    assert not window._login_card.isHidden()


def test_login_requires_username(auth_env, app):
    auth, prefs = auth_env
    window = _window(auth, prefs)

    window._do_login()
    assert window._user_field.has_error
    assert window._login_error.isHidden()


def test_registration_lands_on_login_with_success_banner(auth_env, app):
    auth, prefs = auth_env
    window = _window(auth, prefs)

    window._go_register()
    assert window.current_page() == 1
    _fill_register(window, "newuser", "new@example.com", "secret123")
    window._do_register()

    assert window.current_page() == 0
    assert not window._login_success.isHidden()
    assert "newuser" in window._login_success.text
    assert window._login_user.text() == "newuser"
    assert window._reg_user.text() == ""
    assert window._register_button.isEnabled()
    assert not window._login_button.isHidden()


def test_registration_highlights_every_invalid_field(auth_env, app):
    auth, prefs = auth_env
    calls = []
    original = auth.register

    def spy(*args, **kwargs):
        calls.append(args)
        return original(*args, **kwargs)

    auth.register = spy
    window = _window(auth, prefs)
    window._go_register()
    _fill_register(window, "ab", "nope", "123", confirm="456")
    window._do_register()

    assert window._reg_user_field.has_error
    assert window._reg_email_field.has_error
    assert window._reg_pass_field.has_error
    assert window._reg_confirm_field.has_error
    assert calls == []
    assert not window._busy


def test_registration_reports_taken_username_on_the_field(auth_env, app):
    auth, prefs = auth_env
    assert auth.register("taken", "taken@example.com", "secret123")[0]

    window = _window(auth, prefs)
    window._go_register()
    _fill_register(window, "taken", "other@example.com", "secret123")
    window._do_register()

    assert window.current_page() == 1
    assert window._reg_user_field.has_error
    assert "username" in window._reg_user_field._message.text().lower()


def test_failed_login_shows_generic_error(auth_env, app):
    auth, prefs = auth_env
    assert auth.register("chris", "chris@example.com", "secret123")[0]

    window = _window(auth, prefs)
    window._login_user.setText("chris")
    window._login_pass.setText("wrong-password")
    window._do_login()

    assert not window._login_error.isHidden()
    assert window._login_error.text == "Invalid username or password"
    assert window._pass_field.has_error


def test_password_toggles_are_independent(auth_env, app):
    auth, prefs = auth_env
    window = _window(auth, prefs)
    window._go_register()
    window._reg_pass.setText("secret123")
    window._reg_confirm.setText("secret123")

    window._reg_pass.toggle_action.trigger()
    assert window._reg_pass.is_password_visible()
    assert not window._reg_confirm.is_password_visible()
    assert window._reg_pass.text() == "secret123"

    window._reg_confirm.toggle_action.trigger()
    assert window._reg_confirm.is_password_visible()
    window._reg_pass.toggle_action.trigger()
    assert not window._reg_pass.is_password_visible()
    assert window._reg_confirm.is_password_visible()


def test_registration_resets_password_visibility(auth_env, app):
    auth, prefs = auth_env
    window = _window(auth, prefs)
    window._go_register()
    _fill_register(window, "resetuser", "reset@example.com", "secret123", confirm="mismatch")
    window._reg_pass.toggle_action.trigger()
    window._reg_confirm.toggle_action.trigger()
    assert window._reg_pass.is_password_visible()

    window._reg_confirm.setText("secret123")
    window._do_register()

    assert not window._reg_pass.is_password_visible()
    assert not window._reg_confirm.is_password_visible()


def test_remember_me_saves_username_after_successful_login(auth_env, app):
    auth, prefs = auth_env
    assert auth.register("chris", "chris@example.com", "secret123")[0]

    signed_in = []
    window = _window(auth, prefs, signed_in.append)
    window._login_user.setText("chris")
    window._login_pass.setText("secret123")
    window._remember.setChecked(True)
    window._do_login()

    assert signed_in and signed_in[-1]["username"] == "chris"
    assert prefs.remember_enabled()
    assert prefs.remembered_username() == "chris"


def test_remember_me_restores_and_unchecking_clears(auth_env, app):
    auth, prefs = auth_env
    prefs.set_remembered_username("chris")

    window = _window(auth, prefs)
    assert window._remember.isChecked()
    assert window._login_user.text() == "chris"

    window._remember.setChecked(False)
    assert not prefs.remember_enabled()
    assert prefs.remembered_username() == ""


def test_double_submit_is_ignored(auth_env, app):
    auth, prefs = auth_env
    calls = []
    auth.register = lambda *args, **kwargs: calls.append(args) or (True, "ok")

    window = _window(auth, prefs)
    window._go_register()
    _fill_register(window, "fastuser", "fast@example.com", "secret123")
    window._busy = True
    window._do_register()

    assert calls == []
    assert window.current_page() == 1
