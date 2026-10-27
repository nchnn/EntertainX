from typing import Callable
from PySide6.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QFrame
from auth.auth_manager import AuthManager
from ui.sidebar import Sidebar
from ui.content_area import ContentArea


class MainWindow(QMainWindow):
    def __init__(self, auth_manager: AuthManager, user: dict, on_logout: Callable, parent=None) -> None:
        super().__init__(parent)
        self._auth = auth_manager
        self._on_logout = on_logout

        central = QWidget()
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._content = ContentArea(on_logout=self._do_logout)
        self._sidebar = Sidebar(
            username=user["username"],
            on_category=self._content.show_category,
        )

        layout.addWidget(self._sidebar)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setFixedWidth(1)
        sep.setStyleSheet("color: #2a2a4a;")
        layout.addWidget(sep)

        layout.addWidget(self._content)

        self.setCentralWidget(central)

    def _do_logout(self) -> None:
        self._auth.logout()
        self._on_logout()
