"""Theme customizer dialog for EntertainX.

Allows the user to select from curated accent colors or choose a custom color,
instantly recompiling the QSS stylesheet via theme.apply_theme.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QApplication,
    QColorDialog,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from database.db import get_connection
from theme import theme_manager as theme
from ui.components.layout import Card, Divider, label

_PRESETS = [
    ("Rose Quartz", "#E8AAB9"),
    ("Emerald", "#8FC9A8"),
    ("Electric Violet", "#C49BFF"),
    ("Gold Sunset", "#E6C084"),
    ("Crimson", "#E8808C"),
    ("Sky Cyan", "#7DD3FC"),
]


class ThemeDialog(QDialog):
    """Modal dialog to customize primary accent color with live preview."""

    def __init__(self, user_id: int | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Customize Theme")
        self.setFixedWidth(380)
        self._user_id = user_id
        self._current_primary = theme.PRIMARY

        layout = QVBoxLayout(self)
        layout.setContentsMargins(theme.SPACE_LG, theme.SPACE_LG, theme.SPACE_LG, theme.SPACE_LG)
        layout.setSpacing(theme.SPACE_MD)

        title = QLabel("Theme & Appearance")
        title.setProperty("role", "sectionTitle")
        layout.addWidget(title)

        desc = label("Choose a primary accent color for buttons, badges, and glows.", "muted")
        layout.addWidget(desc)

        layout.addWidget(Divider())

        # Presets grid
        preset_title = QLabel("Preset Accents")
        preset_title.setProperty("role", "caption")
        layout.addWidget(preset_title)

        grid = QGridLayout()
        grid.setSpacing(theme.SPACE_SM)

        for i, (name, hex_color) in enumerate(_PRESETS):
            btn = self._build_preset_button(name, hex_color)
            grid.addWidget(btn, i // 2, i % 2)

        layout.addLayout(grid)

        layout.addSpacing(theme.SPACE_SM)

        # Custom color picker button
        custom_btn = QPushButton("Custom Color...")
        custom_btn.setProperty("variant", "subtle")
        custom_btn.setMinimumHeight(theme.CONTROL_HEIGHT)
        custom_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        custom_btn.clicked.connect(self._pick_custom_color)
        layout.addWidget(custom_btn)

        layout.addSpacing(theme.SPACE_SM)
        layout.addWidget(Divider())

        # Close button
        button_row = QHBoxLayout()
        button_row.addStretch(1)
        close_btn = QPushButton("Done")
        close_btn.setProperty("variant", "primary")
        close_btn.setFixedSize(100, theme.CONTROL_HEIGHT)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(self.accept)
        button_row.addWidget(close_btn)
        layout.addLayout(button_row)

    def _build_preset_button(self, name: str, hex_color: str) -> QPushButton:
        btn = QPushButton(f"  {name}")
        btn.setProperty("variant", "subtle")
        btn.setMinimumHeight(38)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)

        # Colored dot icon / indicator
        swatch = QFrame()
        swatch.setFixedSize(14, 14)
        swatch.setStyleSheet(
            f"background-color: {hex_color}; border-radius: 7px; border: 1px solid rgba(255,255,255,0.2);"
        )

        btn.clicked.connect(lambda: self._apply_color(hex_color))
        return btn

    def _pick_custom_color(self) -> None:
        initial = QColor(self._current_primary)
        color = QColorDialog.getColor(initial, self, "Select Accent Color")
        if color.isValid():
            self._apply_color(color.name())

    def _apply_color(self, hex_color: str) -> None:
        self._current_primary = hex_color
        app = QApplication.instance()
        if app is not None:
            theme.apply_theme(app, primary=hex_color)
        self._save_to_db(hex_color)

    def _save_to_db(self, hex_color: str) -> None:
        if self._user_id is None:
            return
        try:
            conn = get_connection()
            conn.execute(
                """
                INSERT INTO user_settings (user_id, primary_color, secondary_color, updated_at)
                VALUES (?, ?, ?, datetime('now'))
                ON CONFLICT(user_id) DO UPDATE SET
                    primary_color = excluded.primary_color,
                    updated_at = datetime('now')
                """,
                (self._user_id, hex_color, hex_color),
            )
            conn.commit()
            conn.close()
        except Exception:
            pass
