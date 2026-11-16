"""Admin-only user management page.

Displays a table of all user accounts (visible only to administrators) with
columns for ID, Username, Email, Role, Password hash (hex), and Created.
Admins can change another user's role via a per-row combo box.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QHeaderView,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from auth.auth_manager import AuthManager
from ui.components.surfaces import InlineBanner
from ui.pages.page_shell import PageShell


_COLUMNS = ("ID", "Username", "Email", "Role", "Password hash (hex)", "Created")
_ROLES = ("user", "admin")


class AdminPage(QWidget):
    """Admin-only user management table.

    Parameters
    ----------
    auth_manager:
        The active ``AuthManager`` whose session must be an admin.
    parent:
        Optional parent widget.
    """

    def __init__(
        self,
        auth_manager: AuthManager,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._auth = auth_manager

        self._shell = PageShell(
            "User Management",
            "View and manage user accounts.",
        )

        # Error / success banner
        self._banner = InlineBanner("error")
        self._shell.add(self._banner)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(len(_COLUMNS))
        self.table.setHorizontalHeaderLabels(list(_COLUMNS))
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)

        # Header stretch
        header = self.table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  # ID
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)           # Username
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)           # Email
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # Role
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)           # Hash
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)  # Created

        self._shell.add(self.table)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._shell)

        self.refresh_users()

    # ── Data ────────────────────────────────────────────────────────────────
    def refresh_users(self) -> None:
        """Reload the table from the auth backend."""
        self._banner.clear()
        ok, result = self._auth.list_users()
        if not ok:
            self._banner.set_tone("error")
            self._banner.show_message(str(result))
            self.table.setRowCount(0)
            return

        records: list[dict] = result
        current_id = (
            self._auth.current_user["id"] if self._auth.current_user else None
        )

        self.table.setRowCount(len(records))
        for row, record in enumerate(records):
            # ID
            id_item = QTableWidgetItem(str(record["id"]))
            id_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 0, id_item)

            # Username
            self.table.setItem(row, 1, QTableWidgetItem(record["username"]))

            # Email
            self.table.setItem(row, 2, QTableWidgetItem(record["email"]))

            # Role — combo box for non-self rows, plain text for self
            if record["id"] == current_id:
                role_item = QTableWidgetItem(record["role"])
                role_item.setFlags(role_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(row, 3, role_item)
            else:
                combo = QComboBox()
                combo.addItems(list(_ROLES))
                combo.setCurrentText(record["role"])
                combo.setProperty("user_id", record["id"])
                combo.currentTextChanged.connect(
                    lambda new_role, uid=record["id"]: self._on_role_change(uid, new_role)
                )
                self.table.setCellWidget(row, 3, combo)

            # Password hash (hex) — selectable text
            hash_item = QTableWidgetItem(record["password_hash_hex"])
            hash_item.setFlags(
                hash_item.flags() | Qt.ItemFlag.ItemIsSelectable
            )
            self.table.setItem(row, 4, hash_item)

            # Created
            self.table.setItem(row, 5, QTableWidgetItem(record.get("created_at", "")))

    def _on_role_change(self, user_id: int, new_role: str) -> None:
        """Handle a role combo box change."""
        ok, message = self._auth.change_user_role(user_id, new_role)
        if ok:
            self._banner.set_tone("success")
            self._banner.show_message(message)
            self.refresh_users()
        else:
            self._banner.set_tone("error")
            self._banner.show_message(message)
            # Restore previous state
            self.refresh_users()
