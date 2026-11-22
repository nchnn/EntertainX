"""Form field widgets shared by the auth screens and the content pages."""

from __future__ import annotations

import re

from PySide6.QtCore import QEasingCurve, QEvent, QRect, QRectF, Qt, QVariantAnimation
from PySide6.QtGui import QColor, QIcon, QPainter, QPen
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QSizePolicy,
    QToolTip,
    QVBoxLayout,
    QWidget,
)

from theme import theme_manager as theme
from ui.components import motion
from ui.components.icons import make_icon

ICON_SIZE = 18
ICON_INSET = 16
ICON_GAP = 10
TEXT_INSET = ICON_INSET + ICON_SIZE + ICON_GAP


class IconLineEdit(QLineEdit):
    """A line edit whose leading icon is painted at a fixed inset.

    ``QLineEdit`` parks action icons against the frame, which reads cramped on
    tall fields. Painting the glyph keeps one inset shared by every input.
    """

    def __init__(
        self,
        icon_name: str = "",
        placeholder: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setProperty("iconField", True)
        self.setMinimumHeight(46)
        self.setClearButtonEnabled(False)
        self.setPlaceholderText(placeholder)
        self._icon_name = icon_name
        self._icon_idle = (
            make_icon(icon_name, theme.TEXT_MUTED, ICON_SIZE) if icon_name else None
        )
        self._icon_active = (
            make_icon(icon_name, theme.TEXT_SECONDARY, ICON_SIZE) if icon_name else None
        )
        self._leading_action = None
        if icon_name:
            # The action keeps the public API (and its tests); the glyph itself
            # is painted below so it can sit at ICON_INSET, not on the border.
            action = self.addAction(
                self._icon_idle, QLineEdit.ActionPosition.LeadingPosition
            )
            action.setVisible(False)
            self._leading_action = action
        self._apply_text_margins()

        # The accent edge eases in on focus; QSS can only switch it instantly.
        self._focus_level = 0.0
        self._focus_anim = QVariantAnimation(self)
        self._focus_anim.setDuration(180)
        self._focus_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._focus_anim.valueChanged.connect(self._set_focus_level)

    # ── Painting ────────────────────────────────────────────────────────────
    def _apply_text_margins(self) -> None:
        left = TEXT_INSET if self._icon_idle is not None else 12
        self.setTextMargins(left, 0, 12, 0)

    def _leading_icon_rect(self) -> QRect:
        return QRect(
            ICON_INSET, (self.height() - ICON_SIZE) // 2, ICON_SIZE, ICON_SIZE
        )

    def _set_focus_level(self, value) -> None:
        self._focus_level = float(value)
        self.update()

    def _glide_focus(self, target: float) -> None:
        self._focus_anim.stop()
        if not motion.motion_enabled() or not self.isVisible():
            self._set_focus_level(target)
            return
        self._focus_anim.setStartValue(self._focus_level)
        self._focus_anim.setEndValue(target)
        self._focus_anim.start()

    def focusInEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        super().focusInEvent(event)
        self._glide_focus(1.0)

    def focusOutEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        super().focusOutEvent(event)
        self._glide_focus(0.0)

    def _paint_focus_edge(self, painter: QPainter) -> None:
        level = self._focus_level
        if level <= 0.0:
            return
        color = QColor(theme.DANGER if self.property("error") else theme.PRIMARY)
        radius = float(theme.RADIUS_MD)
        edge = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)

        glow = QColor(color)
        glow.setAlphaF(0.16 * level)
        painter.setPen(QPen(glow, 3.0))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(edge.adjusted(1.5, 1.5, -1.5, -1.5), radius - 1, radius - 1)

        line = QColor(color)
        line.setAlphaF(level)
        painter.setPen(QPen(line, 1.0))
        painter.drawRoundedRect(edge, radius, radius)

    def paintEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        self._paint_focus_edge(painter)
        if self._icon_idle is not None:
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
            icon: QIcon = self._icon_active if self.hasFocus() else self._icon_idle
            icon.paint(painter, self._leading_icon_rect())
        painter.end()


class PasswordLineEdit(IconLineEdit):
    """Password input with a lock icon and an eye toggle that keeps the text."""

    def __init__(self, placeholder: str = "Password", parent: QWidget | None = None) -> None:
        super().__init__("lock", placeholder, parent)
        self.setEchoMode(QLineEdit.EchoMode.Password)
        self._eye_hover = False
        self._eye_cache: dict[tuple[str, str], QIcon] = {}

        self.toggle_action = self.addAction(
            make_icon("eye", theme.TEXT_MUTED, ICON_SIZE),
            QLineEdit.ActionPosition.TrailingPosition,
        )
        self.toggle_action.setCheckable(True)
        self.toggle_action.setToolTip("Show password")
        self.toggle_action.setVisible(False)
        self.toggle_action.triggered.connect(self._on_toggle)

    # ── Layout ──────────────────────────────────────────────────────────────
    def _apply_text_margins(self) -> None:
        left = TEXT_INSET if self._icon_idle is not None else 12
        self.setTextMargins(left, 0, TEXT_INSET, 0)

    def _eye_rect(self) -> QRect:
        return QRect(
            self.width() - ICON_INSET - ICON_SIZE,
            (self.height() - ICON_SIZE) // 2,
            ICON_SIZE,
            ICON_SIZE,
        )

    def _eye_icon(self) -> QIcon:
        name = "eye-off" if self.is_password_visible() else "eye"
        color = theme.PRIMARY if self._eye_hover else theme.TEXT_MUTED
        key = (name, color)
        if key not in self._eye_cache:
            self._eye_cache[key] = make_icon(name, color, ICON_SIZE)
        return self._eye_cache[key]

    def paintEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        self._eye_icon().paint(painter, self._eye_rect())
        painter.end()

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
        self.toggle_action.setToolTip("Hide password" if visible else "Show password")
        self.update()
        self.setFocus()

    # ── Pointer affordances ─────────────────────────────────────────────────
    def mousePressEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        if (
            event.button() == Qt.MouseButton.LeftButton
            and self._eye_rect().contains(event.position().toPoint())
        ):
            self.toggle_action.trigger()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        hover = self._eye_rect().contains(event.position().toPoint())
        if hover != self._eye_hover:
            self._eye_hover = hover
            self.setCursor(
                Qt.CursorShape.PointingHandCursor
                if hover
                else Qt.CursorShape.IBeamCursor
            )
            self.update()
        super().mouseMoveEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        if self._eye_hover:
            self._eye_hover = False
            self.unsetCursor()
            self.update()
        super().leaveEvent(event)

    def event(self, event) -> bool:
        if event.type() == QEvent.Type.ToolTip and self._eye_rect().contains(
            event.pos()
        ):
            QToolTip.showText(event.globalPos(), self.toggle_action.toolTip(), self)
            return True
        return super().event(event)


class _StrengthBars(QWidget):
    """Three-segment bar that fills as a password gets stronger."""

    HEIGHT = 6
    WIDTH = 104
    GAP = 4.0

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(self.WIDTH, self.HEIGHT)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._filled = 0
        self._color = theme.BORDER

    def set_state(self, filled: int, color: str) -> None:
        filled = max(0, min(3, filled))
        if (filled, color) == (self._filled, self._color):
            return
        self._filled, self._color = filled, color
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setPen(Qt.PenStyle.NoPen)
        segment = (self.width() - self.GAP * 2) / 3
        for index in range(3):
            painter.setBrush(
                QColor(self._color if index < self._filled else theme.BORDER)
            )
            painter.drawRoundedRect(
                QRectF(index * (segment + self.GAP), 0, segment, self.height()),
                self.HEIGHT / 2,
                self.HEIGHT / 2,
            )
        painter.end()


class PasswordStrength(QWidget):
    """Live strength read-out for a password field.

    It watches a source input so callers do not have to rewire it every time
    the password is cleared or replaced.
    """

    RULES = (r"[a-z]", r"[A-Z]", r"\d", r"[^A-Za-z0-9]")

    def __init__(
        self,
        source: QLineEdit | None = None,
        minimum: int = 6,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._minimum = minimum
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(theme.SPACE_SM)

        self._bars = _StrengthBars()
        row.addWidget(self._bars, 0, Qt.AlignmentFlag.AlignVCenter)

        self._caption = QLabel("")
        self._caption.setProperty("role", "muted")
        self._caption.setWordWrap(True)
        row.addWidget(self._caption, 1)

        if source is not None:
            source.textChanged.connect(self.set_password)
        self.set_password(source.text() if source is not None else "")

    # ── State ───────────────────────────────────────────────────────────────
    @property
    def caption(self) -> str:
        return self._caption.text()

    def set_password(self, text: str) -> None:
        """Update the bars and caption from ``text``.

        The meter stays visible while empty so the form reserves its height and
        the guidance reads before the first keystroke.
        """
        filled, color, role, caption = self._describe(text or "")
        self._bars.set_state(filled, color)
        self._caption.setText(caption)
        if self._caption.property("role") != role:
            self._caption.setProperty("role", role)
            theme.restyle(self._caption)

    def _describe(self, text: str) -> tuple[int, str, str, str]:
        if not text:
            return (
                0,
                theme.BORDER,
                "muted",
                f"Use at least {self._minimum} characters",
            )

        if len(text) < self._minimum:
            return (
                1,
                theme.DANGER,
                "error",
                f"Too short - use at least {self._minimum} characters",
            )

        variety = sum(1 for pattern in self.RULES if re.search(pattern, text))
        if len(text) >= 12 and variety >= 3:
            return 3, theme.SUCCESS, "success", "Strong password"
        if len(text) >= 8 and variety >= 2:
            return 2, theme.SUCCESS, "success", "Good password"
        return 1, theme.WARNING, "warning", "Weak - mix letters, numbers, or symbols"


class FormField(QWidget):
    """Label + input + validation message, stacked with consistent spacing."""

    def __init__(
        self,
        label: str,
        field: QWidget,
        hint: str | None = None,
        accessory: QWidget | None = None,
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

        self._accessory = accessory
        if accessory is not None:
            layout.addWidget(accessory)

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
