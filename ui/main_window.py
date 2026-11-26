from __future__ import annotations

from typing import Callable

from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import QApplication, QHBoxLayout, QWidget

from auth.auth_manager import AuthManager
from theme import theme_manager as theme
from ui.content_area import ContentArea
from ui.sidebar import Sidebar


class MainWindow(QWidget):
    """Application shell: icon-only auto-hiding sidebar + content area."""

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
        self.setMouseTracking(True)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._content = ContentArea(
            user=user,
            auth_manager=auth_manager,
            on_theme=self.open_theme_dialog,
            on_logout=self.do_logout,
        )
        self._content.setMouseTracking(True)
        self._sidebar = Sidebar(
            username=user.get("username", ""),
            on_category=self._content.show_category,
            on_logout=self.do_logout,
            is_admin=user.get("role") == "admin",
        )

        layout.addWidget(self._sidebar)
        layout.addWidget(self._content, 1)

        self._content.category_changed.connect(self._sidebar.mark_active)
        self._sidebar.set_active(self._sidebar.active_category())

        # Track mouse globally over the app so child widgets never block
        # left-edge hover detection for the auto-hiding sidebar.
        app = QApplication.instance()
        if app is not None:
            app.installEventFilter(self)

    @property
    def content(self) -> ContentArea:
        return self._content

    @property
    def sidebar(self) -> Sidebar:
        return self._sidebar

    @property
    def user(self) -> dict:
        return self._user

    def eventFilter(self, watched, event: QEvent) -> bool:
        if event.type() == QEvent.Type.MouseMove and self.isVisible():
            local_pos = self.mapFromGlobal(QCursor.pos())
            if 0 <= local_pos.y() <= self.height():
                if 0 <= local_pos.x() <= 14:
                    self._sidebar.expand()
                elif local_pos.x() > Sidebar.EXPANDED_WIDTH + 8 and not self._sidebar.underMouse():
                    self._sidebar.collapse()
        return False

    def open_theme_dialog(self) -> None:
        """Open the interactive Theme Customizer dialog."""
        from ui.components.theme_dialog import ThemeDialog

        dlg = ThemeDialog(user_id=self._user.get("id"), parent=self.window())
        dlg.exec()

    def do_logout(self) -> None:
        """Clear user session and redirect to login."""
        self._auth.logout()
        self._on_logout()

    _do_logout = do_logout
