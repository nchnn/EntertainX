"""Reusable surfaces: cards, headers, banners, badges, empty states."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from theme import theme_manager as theme
from ui.components.icons import brand_pixmap, make_icon


def label(
    text: str = "",
    role: str = "",
    parent: QWidget | None = None,
    wrap: bool = True,
) -> QLabel:
    """Create a ``QLabel`` that follows the theme's role selectors."""
    widget = QLabel(text, parent)
    if role:
        widget.setProperty("role", role)
    widget.setWordWrap(wrap)
    return widget


class ElidedLabel(QLabel):
    """Single-line label that ellipsises instead of clipping.

    ``full_text()`` always returns the untruncated string so search filters can
    match on it.
    """

    def __init__(self, text: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._full = ""
        self.setWordWrap(False)
        self.set_full_text(text)

    def full_text(self) -> str:
        return self._full

    def set_full_text(self, text: str) -> None:
        self._full = text
        self._apply_elide()

    def resizeEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        super().resizeEvent(event)
        self._apply_elide()

    def _apply_elide(self) -> None:
        width = self.width()
        if width <= 0:
            elided = self._full
        else:
            elided = self.fontMetrics().elidedText(
                self._full, Qt.TextElideMode.ElideRight, max(width - 2, 0)
            )
        if elided != super().text():
            super().setText(elided)


class Card(QFrame):
    """Rounded panel on the card surface."""

    def __init__(self, role: str = "card", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setProperty("role", role)
        self.body = QVBoxLayout(self)
        self.body.setContentsMargins(
            theme.SPACE_XL, theme.SPACE_XL, theme.SPACE_XL, theme.SPACE_XL
        )
        self.body.setSpacing(theme.SPACE_LG)


class Divider(QFrame):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setProperty("role", "divider")
        self.setFixedHeight(1)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)


class SectionLabel(QLabel):
    def __init__(self, text: str, parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self.setProperty("role", "h3")


class Badge(QLabel):
    """Small accent pill, e.g. "In development"."""

    def __init__(self, text: str, parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self.setProperty("role", "pill")
        self.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)


class InlineBanner(QFrame):
    """Single-line feedback area for errors, successes, and hints."""

    TONES = ("error", "success", "info")

    def __init__(self, tone: str = "error", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        if tone not in self.TONES:
            tone = "info"
        self._tone = tone
        self.setProperty("banner", tone)

        row = QHBoxLayout(self)
        row.setContentsMargins(theme.SPACE_MD, theme.SPACE_SM, theme.SPACE_MD, theme.SPACE_SM)
        row.setSpacing(theme.SPACE_SM)

        self.message_label = QLabel("")
        self.message_label.setProperty("bannerText", tone)
        self.message_label.setWordWrap(True)
        row.addWidget(self.message_label, 1)

        self.setVisible(False)

    # ── API used by the auth screens ────────────────────────────────────────
    @property
    def text(self) -> str:
        return self.message_label.text()

    def show_message(self, text: str) -> None:
        self.message_label.setText(text)
        self.setVisible(bool(text))

    def clear(self) -> None:
        self.message_label.setText("")
        self.setVisible(False)

    def set_tone(self, tone: str) -> None:
        if tone not in self.TONES or tone == self._tone:
            return
        self._tone = tone
        self.setProperty("banner", tone)
        self.message_label.setProperty("bannerText", tone)
        theme.restyle(self)
        theme.restyle(self.message_label)


class PageHeader(QWidget):
    """Page title, supporting line, and optional trailing actions."""

    def __init__(
        self,
        title: str,
        subtitle: str = "",
        actions: list[QWidget] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(theme.SPACE_LG)

        text_column = QVBoxLayout()
        text_column.setContentsMargins(0, 0, 0, 0)
        text_column.setSpacing(theme.SPACE_XS)

        self.title_label = label(title, "h1", wrap=False)
        text_column.addWidget(self.title_label)

        self.subtitle_label = label(subtitle, "muted")
        self.subtitle_label.setVisible(bool(subtitle))
        text_column.addWidget(self.subtitle_label)

        row.addLayout(text_column, 1)

        for action in actions or []:
            row.addWidget(action, 0, Qt.AlignmentFlag.AlignVCenter)

    @property
    def title(self) -> str:
        return self.title_label.text()


class EmptyState(QWidget):
    """Centred icon + explanation for sections without content yet."""

    def __init__(
        self,
        icon_name: str,
        title: str,
        body: str,
        hint: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        column = QVBoxLayout(self)
        column.setContentsMargins(
            theme.SPACE_XXL, theme.SPACE_XXL, theme.SPACE_XXL, theme.SPACE_XXL
        )
        column.setSpacing(theme.SPACE_MD)
        column.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # A fixed-width inner card keeps wrapped text predictable; without it
        # QLabel shrinks to its size hint and clips the last line.
        inner = QWidget()
        inner.setFixedWidth(480)
        stack = QVBoxLayout(inner)
        stack.setContentsMargins(0, 0, 0, 0)
        stack.setSpacing(theme.SPACE_MD)

        tile = QFrame()
        tile.setProperty("role", "iconTile")
        tile.setFixedSize(84, 84)
        tile_layout = QVBoxLayout(tile)
        tile_layout.setContentsMargins(0, 0, 0, 0)
        tile_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        glyph = QLabel()
        glyph.setPixmap(make_icon(icon_name, theme.PRIMARY, 34).pixmap(34, 34))
        glyph.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tile_layout.addWidget(glyph)
        stack.addWidget(tile, 0, Qt.AlignmentFlag.AlignHCenter)

        self.title_label = label(title, "h2")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        stack.addWidget(self.title_label)

        self.body_label = label(body, "muted")
        self.body_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        stack.addWidget(self.body_label)

        if hint:
            hint_label = label(hint, "caption")
            hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            stack.addWidget(hint_label)

        column.addWidget(inner, 0, Qt.AlignmentFlag.AlignHCenter)


class BrandLockup(QWidget):
    """Mark + wordmark used on the auth cards."""

    def __init__(self, size: int = 36, tagline: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(theme.SPACE_MD)

        mark = QLabel()
        mark.setPixmap(brand_pixmap(size))
        mark.setFixedSize(size, size)
        row.addWidget(mark, 0, Qt.AlignmentFlag.AlignVCenter)

        text_column = QVBoxLayout()
        text_column.setContentsMargins(0, 0, 0, 0)
        text_column.setSpacing(0)

        wordmark = label("EntertainX", "brand", wrap=False)
        text_column.addWidget(wordmark)

        if tagline:
            subtitle = label(tagline, "caption", wrap=False)
            text_column.addWidget(subtitle)

        row.addLayout(text_column)
        row.addStretch(1)
