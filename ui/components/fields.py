"""Form field widgets shared by the auth screens and the content pages."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

from theme import theme_manager as theme
from ui.components.icons import make_icon


class IconLineEdit(QLineEdit):
    """A line edit with a leading painted icon."""

    def __init__(
        self,
        icon_name: str = "",
        placeholder: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setPlaceholderText(placeholder)
        self.setMinimumHeight(44)
        self.setClearButtonEnabled(False)
        self._leading_action = None
        if icon_name:
            self._leading_action = self.addAction(
                make_icon(icon_name, theme.TEXT_MUTED, 18),
                QLineEdit.ActionPosition.LeadingPosition,
            )


class PasswordLineEdit(IconLineEdit):
    """Password input with a lock icon and an eye toggle that keeps the text."""

    def __init__(self, placeholder: str = "Password", parent: QWidget | None = None) -> None:
        super().__init__("lock", placeholder, parent)
        self.setEchoMode(QLineEdit.EchoMode.Password)

        self.toggle_action = self.addAction(
            make_icon("eye", theme.TEXT_MUTED, 18),
            QLineEdit.ActionPosition.TrailingPosition,
        )
        self.toggle_action.setCheckable(True)
        self.toggle_action.setToolTip("Show password")
        self.toggle_action.triggered.connect(self._on_toggle)

    # ── Behaviour ───────────────────────────────────────────────────────────
    def is_password_visible(self) -> bool:
        return self.echoMode() == QLineEdit.EchoMode.Normal

    def set_password_visible(self, visible: bool) -> None:
        self.toggle_action.setChecked(visible)
        self._apply_visibility(visible)

    def _on_toggle(self, checked: bool) -> None:
        self._apply_visibility(checked)

    def _apply_visibility(self, visible: bool) -> None:
        text = self.text()
        self.setEchoMode(
            QLineEdit.EchoMode.Normal if visible else QLineEdit.EchoMode.Password
        )
        self.setText(text)  # echo-mode changes never clear text; this guarantees it
        self.toggle_action.setIcon(
            make_icon("eye-off" if visible else "eye", theme.TEXT_MUTED, 18)
        )
        self.toggle_action.setToolTip("Hide password" if visible else "Show password")
        self.setFocus()


class FormField(QWidget):
    """Label + input + validation message, stacked with consistent spacing."""

    def __init__(
        self,
        label: str,
        field: QWidget,
        hint: str | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.field = field
        self._hint = hint or ""
        self._error = ""

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(theme.SPACE_XS + 2)

        self._label = QLabel(label)
        self._label.setProperty("role", "fieldLabel")
        self._label.setBuddy(field)
        layout.addWidget(self._label)

        layout.addWidget(field)

        self._message = QLabel(self._hint)
        self._message.setProperty("role", "muted")
        self._message.setWordWrap(True)
        self._message.setVisible(bool(self._hint))
        layout.addWidget(self._message)

    # ── State ───────────────────────────────────────────────────────────────
    @property
    def has_error(self) -> bool:
        return bool(self._error)

    def set_error(self, message: str) -> None:
        self._error = message
        self._message.setText(message)
        self._message.setProperty("role", "error")
        self._message.setVisible(True)
        self.field.setProperty("error", True)
        theme.restyle(self._message)
        theme.restyle(self.field)

    def clear_error(self) -> None:
        self._error = ""
        self._message.setProperty("role", "muted")
        self._message.setText(self._hint)
        self._message.setVisible(bool(self._hint))
        self.field.setProperty("error", False)
        theme.restyle(self._message)
        theme.restyle(self.field)

    def set_hint(self, text: str) -> None:
        self._hint = text
        if not self._error:
            self._message.setText(text)
            self._message.setVisible(bool(text))

    def set_enabled(self, enabled: bool) -> None:
        self.field.setEnabled(enabled)
        self._label.setEnabled(enabled)


class LabeledValue(QWidget):
    """Read-only label/value pair used on the Settings page."""

    def __init__(self, label: str, value: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(theme.SPACE_MD)

        key = QLabel(label)
        key.setProperty("role", "muted")
        key.setMinimumWidth(110)
        row.addWidget(key)

        self.value_label = QLabel(value)
        self.value_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        row.addWidget(self.value_label, 1)
