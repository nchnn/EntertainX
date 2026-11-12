from typing import Callable

from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget

from auth.auth_manager import AuthManager
from theme import theme_manager as theme
from ui.content_area import ContentArea
from ui.sidebar import Sidebar


class MainWindow(QWidget):
    """Application shell: sidebar + content area inside the frameless window."""

    def __init__(
        self,
        auth_manager: AuthManager,
        user: dict,
        on_logout: Callable,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._auth = auth_manager
        self._on_logout = on_logout
        self._user = user

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._content = ContentArea(user=user)
        self._sidebar = Sidebar(
            username=user["username"],
            on_category=self._content.show_category,
            on_logout=self._do_logout,
        )

        layout.addWidget(self._sidebar)
        layout.addWidget(self._content, 1)

        self._sidebar.set_active(self._sidebar.active_category())

    @property
    def content(self) -> ContentArea:
        return self._content

    @property
    def sidebar(self) -> Sidebar:
        return self._sidebar

    def _do_logout(self) -> None:
        self._auth.logout()
        self._on_logout()
