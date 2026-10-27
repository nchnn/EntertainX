from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt
from theme.theme_manager import TEXT_MUTED

_ALIGN = Qt.AlignmentFlag.AlignCenter


class PlaceholderPage(QWidget):
    def __init__(self, icon: str, label: str, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setAlignment(_ALIGN)
        layout.setSpacing(12)

        icon_lbl = QLabel(icon)
        icon_lbl.setAlignment(_ALIGN)
        icon_lbl.setStyleSheet("font-size: 48px; background: transparent;")
        layout.addWidget(icon_lbl)

        name_lbl = QLabel(label)
        name_lbl.setAlignment(_ALIGN)
        name_lbl.setStyleSheet("font-size: 20px; font-weight: bold; background: transparent;")
        layout.addWidget(name_lbl)

        sub_lbl = QLabel("Coming soon")
        sub_lbl.setAlignment(_ALIGN)
        sub_lbl.setStyleSheet(f"font-size: 12px; color: {TEXT_MUTED}; background: transparent;")
        layout.addWidget(sub_lbl)
