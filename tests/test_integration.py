import os
from database.db import get_connection, init_db
from auth.auth_manager import AuthManager

DB_PATH = "test_integration.db"

def teardown_function():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

def test_full_auth_cycle():
    conn = get_connection(DB_PATH)
    init_db(conn)
    auth = AuthManager(conn)

    # Register
    ok, _ = auth.register("demo", "demo@test.com", "DemoPass123!")
    assert ok

    # Login
    ok, user = auth.login("demo", "DemoPass123!")
    assert ok
    assert user["username"] == "demo"
    assert auth.is_logged_in()

    # Logout
    auth.logout()
    assert not auth.is_logged_in()

    # Re-login
    ok, user = auth.login("demo", "DemoPass123!")
    assert ok
    assert auth.current_user["id"] == user["id"]

    conn.close()

def test_sql_injection_attempt():
    conn = get_connection(DB_PATH)
    init_db(conn)
    auth = AuthManager(conn)

    # This should be stored literally or rejected, never executed
    ok, _ = auth.register("'; DROP TABLE users;--", "hack@test.com", "pass123")
    # Whether it succeeds or fails, users table must still exist
    cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
    assert cur.fetchone() is not None
    conn.close()
