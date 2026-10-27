from PySide6.QtWidgets import QApplication

# Color constants — Phase 7 swaps these via user settings
PRIMARY = "#6C63FF"
SECONDARY = "#FF6584"
BG_DARK = "#1a1a2e"
BG_SIDEBAR = "#16213e"
BG_CARD = "#0f3460"
TEXT_PRIMARY = "#e0e0e0"
TEXT_MUTED = "#a0a0b0"

QSS = f"""
QMainWindow, QWidget {{
    background-color: {BG_DARK};
    color: {TEXT_PRIMARY};
    font-family: "Segoe UI", Arial, sans-serif;
    font-size: 13px;
}}

QLabel {{
    color: {TEXT_PRIMARY};
    background: transparent;
}}

QPushButton {{
    background-color: {PRIMARY};
    color: #ffffff;
    border: none;
    border-radius: 6px;
    padding: 8px 18px;
    font-size: 13px;
}}
QPushButton:hover {{
    background-color: #5a52d5;
}}
QPushButton:pressed {{
    background-color: #4a43c0;
}}
QPushButton:disabled {{
    background-color: #3a3a5a;
    color: {TEXT_MUTED};
}}

QLineEdit {{
    background-color: {BG_CARD};
    color: {TEXT_PRIMARY};
    border: 1px solid #2a2a4a;
    border-radius: 6px;
    padding: 8px 12px;
    font-size: 13px;
}}
QLineEdit:focus {{
    border: 1px solid {PRIMARY};
}}
QLineEdit::placeholder {{
    color: {TEXT_MUTED};
}}

QScrollBar:vertical {{
    background: {BG_DARK};
    width: 8px;
    border-radius: 4px;
}}
QScrollBar::handle:vertical {{
    background: #3a3a5a;
    border-radius: 4px;
    min-height: 24px;
}}
QScrollBar::handle:vertical:hover {{
    background: {PRIMARY};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}
QScrollBar:horizontal {{
    background: {BG_DARK};
    height: 8px;
    border-radius: 4px;
}}
QScrollBar::handle:horizontal {{
    background: #3a3a5a;
    border-radius: 4px;
    min-width: 24px;
}}
QScrollBar::handle:horizontal:hover {{
    background: {PRIMARY};
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0px;
}}

QFrame[frameShape="5"] {{
    color: #2a2a4a;
}}
"""


def apply_theme(app: QApplication) -> None:
    app.setStyleSheet(QSS)
