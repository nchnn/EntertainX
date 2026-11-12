from PySide6.QtWidgets import QWidget

from ui.components.surfaces import EmptyState
from ui.pages.page_shell import PageShell


class MyListsPage(PageShell):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(
            "My Lists",
            "Everything you have rated or saved, gathered in one place.",
            parent=parent,
        )
        self.add_stretch()
        self.empty_state = EmptyState(
            "list",
            "No saved titles yet",
            "Ratings, watchlists, and saved albums will appear here once the "
            "personal library lands.",
            hint="Personal lists arrive in Phase 7 of the build.",
        )
        self.add(self.empty_state)
        self.add_stretch()
