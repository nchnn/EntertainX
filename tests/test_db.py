import os, sqlite3
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
    init_db(conn)
    cur = conn.execute("PRAGMA table_info(users)")
    cols = {r[1] for r in cur.fetchall()}
    assert cols == {"id", "username", "email", "password_hash", "salt", "created_at"}
    conn.close()

def test_init_db_idempotent():
    conn = get_connection(DB_PATH)
    init_db(conn)
    init_db(conn)  # must not raise
    conn.close()

def test_email_unique_case_insensitive():
    conn = get_connection(DB_PATH)
    init_db(conn)
    conn.execute("INSERT INTO users (username, email, password_hash, salt) VALUES (?, ?, ?, ?)",
                 ("user1", "Test@Mail.com", b"hash1", b"salt1"))
    try:
        conn.execute("INSERT INTO users (username, email, password_hash, salt) VALUES (?, ?, ?, ?)",
                     ("user2", "test@mail.com", b"hash2", b"salt2"))
        conn.commit()
        assert False, "Should reject duplicate email"
    except sqlite3.IntegrityError:
        pass
    conn.close()
