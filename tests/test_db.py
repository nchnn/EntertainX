import os
import sqlite3

import pytest

from database.db import get_connection, init_db

DB_PATH = "test_entertainx.db"


def setup_function():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)


def teardown_function():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)


def test_init_db_creates_tables():
    conn = get_connection(DB_PATH)
    init_db(conn)
    cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [r[0] for r in cur.fetchall()]
    assert "users" in tables
    assert "user_settings" in tables
    conn.close()


def test_users_table_has_correct_columns():
    conn = get_connection(DB_PATH)
    try:
        init_db(conn)
        cur = conn.execute("PRAGMA table_info(users)")
        cols = {r[1] for r in cur.fetchall()}
        assert cols == {"id", "username", "email", "password_hash", "salt", "role", "created_at"}
    finally:
        conn.close()


def test_init_db_migrates_legacy_users_to_user_role():
    conn = sqlite3.connect(":memory:")
    try:
        conn.execute("""
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL COLLATE NOCASE,
                password_hash BLOB NOT NULL,
                salt BLOB NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)
        conn.execute(
            "INSERT INTO users (username, email, password_hash, salt) VALUES (?, ?, ?, ?)",
            ("legacy", "legacy@example.com", b"hash", b"salt"),
        )
        conn.commit()

        init_db(conn)

        columns = {row[1] for row in conn.execute("PRAGMA table_info(users)")}
        assert "role" in columns
        role = conn.execute("SELECT role FROM users WHERE username = ?", ("legacy",)).fetchone()[0]
        assert role == "user"
    finally:
        conn.close()


def test_users_table_rejects_invalid_role():
    conn = sqlite3.connect(":memory:")
    try:
        init_db(conn)

        columns = {row[1] for row in conn.execute("PRAGMA table_info(users)")}
        assert "role" in columns
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO users (username, email, password_hash, salt, role) VALUES (?, ?, ?, ?, ?)",
                ("user1", "user1@example.com", b"hash1", b"salt1", "owner"),
            )
    finally:
        conn.close()


def test_init_db_idempotent():
    conn = get_connection(DB_PATH)
    init_db(conn)
    init_db(conn)  # must not raise
    conn.close()


def test_email_unique_case_insensitive():
    conn = get_connection(DB_PATH)
    init_db(conn)
    conn.execute(
        "INSERT INTO users (username, email, password_hash, salt) VALUES (?, ?, ?, ?)",
        ("user1", "Test@Mail.com", b"hash1", b"salt1"),
    )
    try:
        conn.execute(
            "INSERT INTO users (username, email, password_hash, salt) VALUES (?, ?, ?, ?)",
            ("user2", "test@mail.com", b"hash2", b"salt2"),
        )
        conn.commit()
        assert False, "Should reject duplicate email"
    except sqlite3.IntegrityError:
        pass
    conn.close()
