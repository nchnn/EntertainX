import re
import sqlite3
import sys

import pytest
from PySide6.QtWidgets import QApplication, QComboBox

app = QApplication.instance() or QApplication(sys.argv)

from auth.auth_manager import AuthManager
from database.db import init_db
from ui.pages.admin import AdminPage


ADMIN_PASSWORD = "AdminPass1!"
MEMBER_PASSWORD = "MemberPass1!"


def make_admin_page():
    """Create an AdminPage with one admin and one regular user."""
    conn = sqlite3.connect(":memory:")
    init_db(conn)
    auth = AuthManager(conn)

    assert auth.register("admin", "admin@example.com", ADMIN_PASSWORD)[0]
    assert auth.register("member", "member@example.com", MEMBER_PASSWORD)[0]
    conn.execute("UPDATE users SET role = 'admin' WHERE username = 'admin'")
    conn.commit()
    assert auth.login("admin", ADMIN_PASSWORD)[0]

    page = AdminPage(auth_manager=auth)
    return conn, auth, page


def test_admin_page_table_has_correct_columns():
    conn, auth, page = make_admin_page()
    try:
        expected = ["ID", "Username", "Email", "Role", "Password hash (hex)", "Created"]
        actual = [
            page.table.horizontalHeaderItem(i).text()
            for i in range(page.table.columnCount())
        ]
        assert actual == expected
        assert page.table.columnCount() == 6
    finally:
        conn.close()


def test_admin_page_table_shows_all_users():
    conn, auth, page = make_admin_page()
    try:
        assert page.table.rowCount() == 2
        usernames = {
            page.table.item(row, 1).text()
            for row in range(page.table.rowCount())
        }
        assert usernames == {"admin", "member"}
    finally:
        conn.close()


def test_admin_page_hash_cells_are_64_char_hex():
    conn, auth, page = make_admin_page()
    try:
        for row in range(page.table.rowCount()):
            hash_text = page.table.item(row, 4).text()
            assert isinstance(hash_text, str)
            assert len(hash_text) == 64
            assert re.fullmatch(r"[0-9a-f]{64}", hash_text)
    finally:
        conn.close()


def test_admin_own_role_is_not_combo():
    """The current admin's role cell should be a plain item, not a combo box."""
    conn, auth, page = make_admin_page()
    try:
        admin_id = auth.current_user["id"]
        for row in range(page.table.rowCount()):
            row_id = int(page.table.item(row, 0).text())
            if row_id == admin_id:
                # Should be a text item, not a combo widget
                assert page.table.cellWidget(row, 3) is None
                assert page.table.item(row, 3).text() == "admin"
                break
        else:
            pytest.fail("Admin row not found")
    finally:
        conn.close()


def test_member_role_has_combo():
    """Non-admin rows should have a combo box for role changes."""
    conn, auth, page = make_admin_page()
    try:
        admin_id = auth.current_user["id"]
        for row in range(page.table.rowCount()):
            row_id = int(page.table.item(row, 0).text())
            if row_id != admin_id:
                combo = page.table.cellWidget(row, 3)
                assert isinstance(combo, QComboBox)
                assert combo.currentText() == "user"
                break
        else:
            pytest.fail("Member row not found")
    finally:
        conn.close()
