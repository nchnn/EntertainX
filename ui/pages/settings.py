from __future__ import annotations

from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QPushButton,
    QWidget,
)

from theme import theme_manager as theme
from ui.components.fields import LabeledValue
from ui.components.surfaces import Card, Divider, SectionLabel, label
from ui.pages.page_shell import PageShell

_SWATCHES = [
    ("Background", theme.BG),
    ("Sidebar", theme.BG_SIDEBAR),
    ("Card", theme.BG_CARD),
    ("Elevated", theme.BG_ELEVATED),
    ("Border", theme.BORDER),
    ("Accent", theme.PRIMARY),
]


class SettingsPage(PageShell):
    def __init__(
        self,
        on_logout: Callable,
        user: dict | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(
            "Settings",
            "Your profile, the application appearance, and the current session.",
            parent=parent,
        )
        user = user or {}

        self.add(self._profile_card(user))
        self.add(self._appearance_card())
        self.add(self._session_card(on_logout))
        self.add_stretch()

    # ── Sections ────────────────────────────────────────────────────────────
    def _profile_card(self, user: dict) -> Card:
        card = Card()
        card.body.addWidget(SectionLabel("Profile"))
        card.body.addWidget(
            label("This is the account currently signed in to EntertainX.", "muted")
        )
        card.body.addWidget(Divider())
        card.body.addWidget(LabeledValue("Username", user.get("username", "Not signed in")))
        card.body.addWidget(LabeledValue("Email", user.get("email", "Not available")))
        return card

    def _appearance_card(self) -> Card:
        card = Card()
        card.body.addWidget(SectionLabel("Appearance"))
        card.body.addWidget(
            label(
                "EntertainX uses a grey-dominant palette with light pink accents.",
                "muted",
            )
        )

        swatches = QHBoxLayout()
        swatches.setContentsMargins(0, 0, 0, 0)
        swatches.setSpacing(theme.SPACE_SM)
        for name, color in _SWATCHES:
            swatch = QFrame()
            swatch.setFixedSize(30, 30)
            swatch.setToolTip(f"{name}  ·  {color}")
            swatch.setStyleSheet(
                f"background-color: {color};"
                f"border: 1px solid {theme.BORDER_STRONG};"
                f"border-radius: {theme.RADIUS_SM}px;"
            )
            swatches.addWidget(swatch)
        swatches.addStretch(1)
        card.body.addLayout(swatches)

        card.body.addWidget(
            label(
                "Custom accent colours and a light mode arrive in Phase 8, "
                "saved per account.",
                "caption",
            )
        )
        return card

    def _session_card(self, on_logout: Callable) -> Card:
        card = Card()
        card.body.addWidget(SectionLabel("Session"))

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(theme.SPACE_MD)
        row.addWidget(
            label("Signing out clears the session and returns to the login screen.", "muted"),
            1,
        )

        self.logout_button = QPushButton("Log out")
        self.logout_button.setProperty("variant", "subtle")
        self.logout_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.logout_button.clicked.connect(on_logout)
        row.addWidget(self.logout_button, 0, Qt.AlignmentFlag.AlignRight)
        card.body.addLayout(row)
        return card
