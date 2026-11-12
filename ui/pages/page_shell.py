"""Shared page scaffolding: scrollable canvas, header, search, card grid.

The content here is static sample data (see :mod:`ui.pages.sample_data`).
Phases 3-6 replace the data sources; the layout stays.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from theme import theme_manager as theme
from ui.components.fields import IconLineEdit
from ui.components.media_card import CardGrid, MediaCard
from ui.components.surfaces import Badge, EmptyState, PageHeader


class PageShell(QWidget):
    """A scrollable page with a consistent header and padding."""

    def __init__(
        self,
        title: str,
        subtitle: str = "",
        actions: list[QWidget] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        outer.addWidget(scroll)

        canvas = QWidget()
        self.content = QVBoxLayout(canvas)
        self.content.setContentsMargins(
            theme.SPACE_XXL, theme.SPACE_XL, theme.SPACE_XXL, theme.SPACE_XXL
        )
        self.content.setSpacing(theme.SPACE_XL)

        self.header = PageHeader(title, subtitle, actions)
        self.content.addWidget(self.header)
        self.content.addStretch(1)  # permanent trailing spacer

        scroll.setWidget(canvas)

    # ── Content helpers ─────────────────────────────────────────────────────
    def add(self, widget: QWidget) -> None:
        self.content.insertWidget(self.content.count() - 1, widget)

    def add_layout(self, layout) -> None:
        self.content.insertLayout(self.content.count() - 1, layout)

    def add_stretch(self) -> None:
        self.content.insertStretch(self.content.count() - 1, 1)

    @property
    def title(self) -> str:
        return self.header.title


def preview_badge(text: str = "Preview") -> Badge:
    badge = Badge(text)
    badge.setToolTip("Sample content until the live integration lands.")
    return badge


def search_field(placeholder: str = "Search") -> IconLineEdit:
    field = IconLineEdit("search", placeholder)
    field.setMaximumWidth(340)
    field.setMinimumWidth(200)
    return field


class GridPage(PageShell):
    """Header + search + responsive card grid, with a built-in empty state."""

    def __init__(
        self,
        title: str,
        subtitle: str,
        cards: list[MediaCard],
        search_placeholder: str = "Search",
        badge: str = "Preview",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(
            title,
            subtitle,
            actions=[preview_badge(badge)] if badge else None,
            parent=parent,
        )

        self.search = search_field(search_placeholder)
        self.toolbar = QHBoxLayout()
        self.toolbar.setContentsMargins(0, 0, 0, 0)
        self.toolbar.setSpacing(theme.SPACE_MD)
        self.toolbar.addWidget(self.search)
        self.toolbar.addStretch(1)
        self.add_layout(self.toolbar)

        self.grid = CardGrid(cards)
        self.add(self.grid)

        self.empty_state = EmptyState(
            "search",
            "Nothing matches that search",
            "Try a different title, artist, or genre.",
            hint="Clear the search field to see everything again.",
        )
        self.empty_state.setVisible(False)
        self.add(self.empty_state)

        self.search.textChanged.connect(self.apply_filter)
        self.apply_filter()

    # ── Filtering ───────────────────────────────────────────────────────────
    def active_category(self) -> str:
        """Extra filter dimension; subclasses may override."""
        return ""

    def apply_filter(self) -> None:
        query = self.search.text()
        category = self.active_category()
        any_visible = False
        for card in self.grid.cards:
            visible = card.matches(query) and (
                not category or card.category == category
            )
            card.setVisible(visible)
            any_visible = any_visible or visible
        self.empty_state.setVisible(not any_visible)

    def visible_titles(self) -> list[str]:
        return [card.title for card in self.grid.cards if not card.isHidden()]

    # ── Toolbar extension point ─────────────────────────────────────────────
    def add_toolbar_widget(self, widget: QWidget) -> None:
        self.toolbar.insertWidget(self.toolbar.count() - 1, widget)
