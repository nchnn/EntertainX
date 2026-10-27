from typing import Callable
from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton
from PySide6.QtCore import Qt
from ui.pages.placeholder import PlaceholderPage


class SettingsPage(QWidget):
    def __init__(self, on_logout: Callable, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.addWidget(PlaceholderPage("⚙", "Settings"))

        logout_btn = QPushButton("Logout")
        logout_btn.setFixedWidth(160)
        logout_btn.clicked.connect(on_logout)
        layout.addWidget(logout_btn, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addSpacing(24)
