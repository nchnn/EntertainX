"""Shared detail layout for game pages whose engines arrive in Phase 6."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from theme import theme_manager as theme
from ui.components.icons import make_icon
from ui.components.layout import Badge, Card, Divider, label
from ui.pages.page_shell import PageShell


class GameDetailPage(PageShell):
    """Description panel plus a clearly-labelled, disabled launch action."""

    def __init__(
        self,
        title: str,
        subtitle: str,
        icon_name: str,
        description: str,
        features: list[str],
        availability: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(
            title,
            subtitle,
            actions=[Badge("In development")],
            parent=parent,
        )

        card = Card()
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(theme.SPACE_XL)

        tile = QFrame()
        tile.setProperty("role", "iconTile")
        tile.setFixedSize(96, 96)
        tile_layout = QVBoxLayout(tile)
        tile_layout.setContentsMargins(0, 0, 0, 0)
        tile_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        glyph = QLabel()
        glyph.setPixmap(make_icon(icon_name, theme.PRIMARY, 40).pixmap(40, 40))
        glyph.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tile_layout.addWidget(glyph)
        row.addWidget(tile, 0, Qt.AlignmentFlag.AlignTop)

        text_column = QVBoxLayout()
        text_column.setContentsMargins(0, 0, 0, 0)
        text_column.setSpacing(theme.SPACE_SM)

        text_column.addWidget(label("About this game", "h2", wrap=False))

        description_label = label(description, "muted")
        description_label.setToolTip(description)
        text_column.addWidget(description_label)

        for feature in features:
            bullet = label(f"•  {feature}", "muted", wrap=False)
            text_column.addWidget(bullet)
        text_column.addStretch(1)

        row.addLayout(text_column, 1)
        card.body.addLayout(row)
        card.body.addWidget(Divider())

        footer = QHBoxLayout()
        footer.setContentsMargins(0, 0, 0, 0)
        footer.setSpacing(theme.SPACE_MD)
        footer.addWidget(label(availability, "caption"), 1)

        play_button = QPushButton("Play")
        play_button.setProperty("variant", "primary")
        play_button.setMinimumWidth(140)
        play_button.setEnabled(False)
        play_button.setToolTip("This game is not playable yet.")
        footer.addWidget(play_button, 0, Qt.AlignmentFlag.AlignRight)
        card.body.addLayout(footer)

        self.add(card)
        self.add_stretch()
