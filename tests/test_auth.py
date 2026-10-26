import os
from database.db import get_connection, init_db
from auth.auth_manager import AuthManager

DB_PATH = "test_auth.db"

def get_auth():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    conn = get_connection(DB_PATH)
    init_db(conn)
    return AuthManager(conn), conn

def teardown_function():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

def test_register_success():
    auth, conn = get_auth()
    ok, msg = auth.register("alice", "alice@example.com", "StrongPass1!")
    assert ok is True
    conn.close()

def test_register_duplicate_username():
    auth, conn = get_auth()
    auth.register("alice", "alice@example.com", "StrongPass1!")
    ok, msg = auth.register("alice", "alice2@example.com", "StrongPass1!")
    assert ok is False
    assert "username" in msg.lower() or "already" in msg.lower()
    conn.close()

def test_register_duplicate_email_case_insensitive():
    auth, conn = get_auth()
    auth.register("alice", "Alice@Example.com", "StrongPass1!")
    ok, msg = auth.register("bob", "alice@example.com", "StrongPass1!")
    assert ok is False
    conn.close()

def test_register_empty_fields():
    auth, conn = get_auth()
    ok, _ = auth.register("", "a@b.com", "pass")
    assert ok is False
    ok, _ = auth.register("alice", "", "pass")
    assert ok is False
    ok, _ = auth.register("alice", "a@b.com", "")
    assert ok is False
    conn.close()

def test_login_success():
    auth, conn = get_auth()
    auth.register("alice", "alice@example.com", "StrongPass1!")
    ok, result = auth.login("alice", "StrongPass1!")
    assert ok is True
    assert result["username"] == "alice"
    assert auth.is_logged_in()
    assert auth.current_user["username"] == "alice"
    conn.close()

def test_login_wrong_password():
    auth, conn = get_auth()
    auth.register("alice", "alice@example.com", "StrongPass1!")
    ok, msg = auth.login("alice", "WrongPass!")
    assert ok is False
    assert "invalid" in msg.lower() or "credentials" in msg.lower()
    conn.close()

def test_login_nonexistent_user():
    auth, conn = get_auth()
    ok, msg = auth.login("ghost", "pass")
    assert ok is False
    # message must NOT reveal that user doesn't exist
    conn.close()

def test_logout():
    auth, conn = get_auth()
    auth.register("alice", "alice@example.com", "StrongPass1!")
    auth.login("alice", "StrongPass1!")
    auth.logout()
    assert auth.is_logged_in() is False
    assert auth.current_user is None
    conn.close()

def test_unicode_password():
    auth, conn = get_auth()
    ok, _ = auth.register("uni", "uni@test.com", "pässwörd🔑")
    assert ok is True
    ok, _ = auth.login("uni", "pässwörd🔑")
    assert ok is True
    conn.close()
