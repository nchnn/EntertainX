import re
import sqlite3

from auth.auth_manager import AuthManager
from database.db import init_db


ADMIN_PASSWORD = "AdminPass1!"
MEMBER_PASSWORD = "MemberPass1!"


def make_auth_sessions():
    conn = sqlite3.connect(":memory:")
    init_db(conn)
    admin = AuthManager(conn)
    member = AuthManager(conn)

    assert admin.register("admin", "admin@example.com", ADMIN_PASSWORD)[0]
    assert member.register("member", "member@example.com", MEMBER_PASSWORD)[0]
    conn.execute("UPDATE users SET role = ? WHERE username = ?", ("admin", "admin"))
    conn.commit()

    assert admin.login("admin", ADMIN_PASSWORD)[0]
    assert member.login("member", MEMBER_PASSWORD)[0]
    admin_id = admin.current_user["id"]
    member_id = member.current_user["id"]
    return conn, admin, member, admin_id, member_id


def test_admin_lists_hex_hashes_without_salts_or_plaintext():
    conn, admin, _member, _admin_id, _member_id = make_auth_sessions()
    try:
        ok, records = admin.list_users()

        assert ok is True
        assert {record["username"] for record in records} == {"admin", "member"}
        for record in records:
            assert set(record) == {
                "id",
                "username",
                "email",
                "role",
                "password_hash_hex",
                "created_at",
            }
            assert isinstance(record["password_hash_hex"], str)
            assert len(record["password_hash_hex"]) == 64
            assert re.fullmatch(r"[0-9a-f]{64}", record["password_hash_hex"])
            assert "salt" not in record
            assert ADMIN_PASSWORD not in record.values()
            assert MEMBER_PASSWORD not in record.values()
    finally:
        conn.close()


def test_regular_user_cannot_list_users_or_change_roles():
    conn, _admin, member, admin_id, _member_id = make_auth_sessions()
    try:
        listed, _records = member.list_users()
        changed, _message = member.change_user_role(admin_id, "user")

        assert listed is False
        assert changed is False
        role = conn.execute("SELECT role FROM users WHERE id = ?", (admin_id,)).fetchone()[0]
        assert role == "admin"
    finally:
        conn.close()


def test_admin_changes_another_users_role_but_not_own_role():
    conn, admin, member, admin_id, member_id = make_auth_sessions()
    try:
        changed, _message = admin.change_user_role(member_id, "admin")

        assert changed is True
        assert member.current_user["role"] == "user"
        role = conn.execute("SELECT role FROM users WHERE id = ?", (member_id,)).fetchone()[0]
        assert role == "admin"

        member.logout()
        relogged_in, session = member.login("member", MEMBER_PASSWORD)
        assert relogged_in is True
        assert session["role"] == "admin"

        changed, _message = admin.change_user_role(admin_id, "user")
        assert changed is False
        own_role = conn.execute("SELECT role FROM users WHERE id = ?", (admin_id,)).fetchone()[0]
        assert own_role == "admin"
    finally:
        conn.close()


def test_invalid_role_or_unknown_user_does_not_change_any_role():
    conn, admin, _member, _admin_id, member_id = make_auth_sessions()
    try:
        invalid_changed, _message = admin.change_user_role(member_id, "owner")
        unknown_changed, _message = admin.change_user_role(999_999, "admin")

        assert invalid_changed is False
        assert unknown_changed is False
        role = conn.execute("SELECT role FROM users WHERE id = ?", (member_id,)).fetchone()[0]
        assert role == "user"
    finally:
        conn.close()
