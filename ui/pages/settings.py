from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QWidget,
)

from theme import theme_manager as theme
from ui.components.form_fields import LabeledValue
from ui.components.layout import Card, Divider, SectionLabel, label
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
    """Profile, appearance preview, and session information.

    Logging out is handled via the top navigation profile menu so there is only
    one logout action in the application.
    """

    def __init__(
        self,
        user: dict | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(
            "Settings",
            "Your profile, the application appearance, and the current session.",
            parent=parent,
        )
        user = user or {}

        self.profile_card = self._profile_card(user)
        self.appearance_card = self._appearance_card()
        self.session_card = self._session_card()

        self.add(self.profile_card)
        self.add(self.appearance_card)
        self.add(self.session_card)
        self.add_stretch()

    # ── Sections ────────────────────────────────────────────────────────────
    def _profile_card(self, user: dict) -> Card:
        card = Card()
        card.body.addWidget(SectionLabel("Profile"))
        card.body.addWidget(
            label("This is the account currently signed in to EntertainX.", "muted")
        )
        card.body.addWidget(Divider())
        card.body.addWidget(
            LabeledValue("Username", user.get("username", "Not signed in"))
        )
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
            swatches.addWidget(swatch, 0, Qt.AlignmentFlag.AlignVCenter)
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

    def _session_card(self) -> Card:
        card = Card()
        card.body.addWidget(SectionLabel("Session"))
        card.body.addWidget(
            label(
                "This session stays active until you log out. Use the log out "
                "button in the profile menu at the top navigation bar.",
                "muted",
            )
        )
        return card
