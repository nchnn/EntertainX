from PySide6.QtWidgets import QLineEdit

from ui.components.fields import FormField, IconLineEdit, PasswordLineEdit


def test_icon_field_has_leading_action(app):
    field = IconLineEdit("user", "Username")
    assert field.actions()
    assert field.placeholderText() == "Username"


def test_password_toggle_preserves_text(app):
    field = PasswordLineEdit()
    field.setText("s3cret pass")
    assert field.echoMode() == QLineEdit.EchoMode.Password

    field.toggle_action.trigger()
    assert field.is_password_visible()
    assert field.echoMode() == QLineEdit.EchoMode.Normal
    assert field.text() == "s3cret pass"

    field.toggle_action.trigger()
    assert not field.is_password_visible()
    assert field.text() == "s3cret pass"


def test_password_visibility_setter_keeps_text(app):
    field = PasswordLineEdit()
    field.setText("abc123")
    field.set_password_visible(True)
    assert field.text() == "abc123"
    assert field.toggle_action.isChecked()


def test_form_field_error_round_trip(app):
    field = IconLineEdit("user", "Username")
    wrapper = FormField("Username", field, hint="Pick a name")

    assert not wrapper.has_error
    wrapper.set_error("Username is required")
    assert wrapper.has_error
    assert field.property("error") is True
    assert wrapper._message.text() == "Username is required"
    assert not wrapper._message.isHidden()

    wrapper.clear_error()
    assert not wrapper.has_error
    assert field.property("error") is False
    assert wrapper._message.text() == "Pick a name"


def test_form_field_without_hint_hides_message(app):
    wrapper = FormField("Email", IconLineEdit("mail", "you@example.com"))
    assert wrapper._message.isHidden()
