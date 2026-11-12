from PySide6.QtWidgets import QLineEdit

from ui.components.fields import (
    FormField,
    IconLineEdit,
    PasswordLineEdit,
    PasswordStrength,
)


def test_icon_field_has_leading_action(app):
    field = IconLineEdit("user", "Username")
    assert field.actions()
    assert field.placeholderText() == "Username"


def test_icon_field_keeps_the_glyph_off_the_border(app):
    field = IconLineEdit("user", "Username")
    assert field.textMargins().left() >= 40

    password = PasswordLineEdit()
    assert password.textMargins().left() >= 40
    assert password.textMargins().right() >= 40


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


def test_password_eye_click_toggles_visibility(app):
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest

    field = PasswordLineEdit()
    field.resize(392, 46)
    field.show()
    field.setText("secret123")

    QTest.mouseClick(
        field, Qt.MouseButton.LeftButton, pos=field._eye_rect().center()
    )
    assert field.is_password_visible()

    QTest.mouseClick(
        field, Qt.MouseButton.LeftButton, pos=field._eye_rect().center()
    )
    assert not field.is_password_visible()


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


def test_password_strength_tracks_the_source_field(app):
    field = PasswordLineEdit()
    meter = PasswordStrength(field, minimum=6)

    assert meter.caption == "Use at least 6 characters"
    assert meter._bars._filled == 0

    field.setText("abc")
    assert "Too short" in meter.caption
    assert meter._bars._filled == 1

    field.setText("secret123")
    assert meter.caption in ("Good password", "Strong password")
    assert meter._bars._filled >= 2

    field.setText("")
    assert meter.caption == "Use at least 6 characters"
    assert meter._bars._filled == 0


def test_strength_meter_caption_is_not_colour_only(app):
    """Strength is readable from the caption, not just the bar colour."""
    field = PasswordLineEdit()
    meter = PasswordStrength(field)

    field.setText("aaaaaaaa")
    assert "Weak" in meter.caption

    field.setText("A longer Passw0rd!")
    assert meter.caption == "Strong password"


def test_form_field_places_the_accessory_between_input_and_message(app):
    field = PasswordLineEdit()
    meter = PasswordStrength(field)
    wrapper = FormField("Password", field, hint="Hint", accessory=meter)

    order = [
        wrapper.layout().itemAt(index).widget() for index in range(wrapper.layout().count())
    ]
    assert order == [wrapper._label, field, meter, wrapper._message]
