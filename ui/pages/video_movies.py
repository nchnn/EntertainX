from PySide6.QtWidgets import QWidget, QVBoxLayout
from ui.pages.placeholder import PlaceholderPage


class MoviesPage(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        QVBoxLayout(self).addWidget(PlaceholderPage("🎬", "Movies"))
