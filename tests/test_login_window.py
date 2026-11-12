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


def test_failed_login_error_clears_when_the_password_is_retried(auth_env, app):
    auth, prefs = auth_env
    assert auth.register("chris", "chris@example.com", "secret123")[0]

    window = _window(auth, prefs)
    window._login_user.setText("chris")
    window._login_pass.setText("wrong-password")
    window._do_login()
    assert window._pass_field.has_error

    window._login_pass.setText("")
    assert not window._pass_field.has_error


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


def test_brand_stage_hides_below_split_width(auth_env, app):
    auth, prefs = auth_env
    window = _window(auth, prefs)

    window.resize(1240, 820)
    window.show()
    assert window._stage.isVisible()
    assert window._pane.property("split") is True

    window.resize(1000, 700)
    assert window._stage.isHidden()
    assert window._pane.property("split") is False

    window.resize(1240, 820)
    assert window._stage.isVisible()


def test_mode_switch_marks_the_active_segment(auth_env, app):
    auth, prefs = auth_env
    window = _window(auth, prefs)
    assert window._login_tab.property("active") is True
    assert window._register_tab.property("active") is False

    window._register_tab.click()
    assert window.current_page() == 1
    assert window._login_tab.property("active") is False
    assert window._register_tab.property("active") is True

    window._login_tab.click()
    assert window.current_page() == 0
    assert window._login_tab.property("active") is True
    assert window._register_tab.property("active") is False


def test_segment_indicator_follows_the_active_tab(auth_env, app):
    auth, prefs = auth_env
    window = _window(auth, prefs)
    window.resize(900, 700)
    window.show()

    window._tabs.set_active(1)
    assert window._tabs._indicator.geometry() == window._register_tab.geometry()

    window._tabs.set_active(0)
    assert window._tabs._indicator.geometry() == window._login_tab.geometry()


def test_poster_fan_hover_hits_side_cards_and_centre(app):
    from PySide6.QtCore import QPointF
    from PySide6.QtGui import QTransform

    from ui.components.auth_stage import MediaFan

    fan = MediaFan()
    fan.resize(420, 420)
    fan.show()
    cards, card_w, card_h = fan._layout()

    def world(index, local):
        origin, angle, *_ = cards[index]
        transform = QTransform()
        transform.translate(origin.x(), origin.y())
        transform.rotate(angle)
        transform.translate(-card_w / 2, -card_h / 2)
        return transform.map(QPointF(*local))

    assert fan._card_at(world(0, (8, card_h / 2))) == 0
    assert fan._card_at(world(1, (card_w - 8, card_h / 2))) == 1
    assert fan._card_at(world(2, (card_w / 2, card_h / 2))) == 2

    fan._set_hover(0)
    assert fan._hover == 0
    assert fan._animations[0].endValue() == 1.0
    assert fan._animations[2].endValue() == 0.0


def test_enter_in_register_form_submits(auth_env, app):
    auth, prefs = auth_env
    window = _window(auth, prefs)
    window._go_register()
    _fill_register(window, "enteruser", "enter@example.com", "secret123")

    window._reg_confirm.returnPressed.emit()

    assert window.current_page() == 0
    assert not window._login_success.isHidden()
    assert "enteruser" in window._login_success.text


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


def test_register_strength_meter_resets_after_success(auth_env, app):
    auth, prefs = auth_env
    window = _window(auth, prefs)
    window._go_register()
    _fill_register(window, "meteruser", "meter@example.com", "secret123")
    assert window._strength.caption in ("Good password", "Strong password")

    window._do_register()

    assert window.current_page() == 0
    assert window._strength.caption == "Use at least 6 characters"


def test_confirm_password_validates_on_blur(auth_env, app):
    from PySide6.QtCore import QEvent
    from PySide6.QtWidgets import QApplication

    auth, prefs = auth_env
    window = _window(auth, prefs)
    window._go_register()
    window._reg_pass.setText("secret123")
    window._reg_confirm.setText("secret12")

    QApplication.sendEvent(window._reg_confirm, QEvent(QEvent.Type.FocusOut))

    assert window._reg_confirm_field.has_error
    assert window._reg_confirm_field._message.text() == "Passwords do not match"

    window._reg_confirm.setText("secret123")
    assert not window._reg_confirm_field.has_error


def test_username_blur_reports_the_rule_that_failed(auth_env, app):
    from PySide6.QtCore import QEvent
    from PySide6.QtWidgets import QApplication

    auth, prefs = auth_env
    window = _window(auth, prefs)
    window._go_register()
    window._reg_user.setText("a b")

    QApplication.sendEvent(window._reg_user, QEvent(QEvent.Type.FocusOut))
    assert window._reg_user_field.has_error
    assert "letters and numbers" in window._reg_user_field._message.text().lower()

    window._reg_user.setText("chris")
    assert not window._reg_user_field.has_error


def test_empty_fields_do_not_nag_on_blur(auth_env, app):
    from PySide6.QtCore import QEvent
    from PySide6.QtWidgets import QApplication

    auth, prefs = auth_env
    window = _window(auth, prefs)
    window._go_register()

    for field, wrapper in (
        (window._reg_user, window._reg_user_field),
        (window._reg_email, window._reg_email_field),
        (window._reg_pass, window._reg_pass_field),
        (window._reg_confirm, window._reg_confirm_field),
    ):
        QApplication.sendEvent(field, QEvent(QEvent.Type.FocusOut))
        assert not wrapper.has_error


def test_register_fields_hint_their_rules(auth_env, app):
    auth, prefs = auth_env
    window = _window(auth, prefs)

    assert "3-20" in window._reg_user_field._hint
    assert "at least 6" in window._strength.caption
