"""Remember me: persistent sign-in across restarts, and how it ends."""

import sqlite3

import pytest
from PySide6.QtCore import QSettings

from auth.auth_manager import AuthManager
from auth.preferences import LoginPreferences
from database.db import get_connection, init_db
from ui.login_window import LoginWindow


def _prefs(tmp_path):
    return LoginPreferences(
        QSettings(str(tmp_path / "prefs.ini"), QSettings.Format.IniFormat)
    )


def _user(auth):
    assert auth.register("chris", "chris@example.com", "secret123")[0]
    ok, user = auth.login("chris", "secret123")
    assert ok
    auth.logout()
    return user


# ── AuthManager: tokens ─────────────────────────────────────────────────────
def test_token_signs_the_user_back_in():
    conn = get_connection(":memory:")
    init_db(conn)
    auth = AuthManager(conn)
    user = _user(auth)

    token = auth.issue_remember_token(user["id"])
    ok, result = auth.login_with_token(token)

    assert ok
    assert result["username"] == "chris"
    assert auth.is_logged_in()
    assert auth.current_user["id"] == user["id"]


def test_only_a_hash_of_the_token_is_stored():
    conn = get_connection(":memory:")
    init_db(conn)
    auth = AuthManager(conn)
    token = auth.issue_remember_token(_user(auth)["id"])
    selector, _, validator = token.partition(".")

    stored = conn.execute("SELECT selector, token_hash FROM remember_tokens").fetchone()
    assert stored[0] == selector
    assert validator.encode() not in stored[1]
    assert len(stored[1]) == 32  # SHA-256 digest


def test_wrong_validator_fails_and_retires_the_token():
    conn = get_connection(":memory:")
    init_db(conn)
    auth = AuthManager(conn)
    token = auth.issue_remember_token(_user(auth)["id"])
    selector = token.partition(".")[0]

    ok, _ = auth.login_with_token(f"{selector}.not-the-validator")
    assert not ok
    assert not auth.is_logged_in()
    # The real token no longer works either: guessing is not allowed to continue.
    assert not auth.login_with_token(token)[0]


@pytest.mark.parametrize("token", ["", "garbage", "only.", ".only", "a.b.c"])
def test_malformed_tokens_are_rejected(token):
    conn = get_connection(":memory:")
    init_db(conn)
    auth = AuthManager(conn)
    _user(auth)

    assert not auth.login_with_token(token)[0]
    assert not auth.is_logged_in()


def test_expired_token_is_rejected_and_removed():
    conn = get_connection(":memory:")
    init_db(conn)
    auth = AuthManager(conn)
    token = auth.issue_remember_token(_user(auth)["id"])
    conn.execute("UPDATE remember_tokens SET expires_at = '2000-01-01 00:00:00'")
    conn.commit()

    ok, message = auth.login_with_token(token)

    assert not ok
    assert "expired" in message
    assert conn.execute("SELECT COUNT(*) FROM remember_tokens").fetchone()[0] == 0


def test_using_a_token_extends_it():
    conn = get_connection(":memory:")
    init_db(conn)
    auth = AuthManager(conn)
    token = auth.issue_remember_token(_user(auth)["id"])
    conn.execute("UPDATE remember_tokens SET expires_at = datetime('now', '+1 day')")
    conn.commit()

    assert auth.login_with_token(token)[0]

    days = conn.execute(
        "SELECT julianday(expires_at) - julianday('now') FROM remember_tokens"
    ).fetchone()[0]
    assert days > 29


def test_revoking_a_token_ends_the_session():
    conn = get_connection(":memory:")
    init_db(conn)
    auth = AuthManager(conn)
    token = auth.issue_remember_token(_user(auth)["id"])

    auth.revoke_remember_token(token)
    auth.revoke_remember_token("not-a-token")  # unknown tokens are ignored

    assert not auth.login_with_token(token)[0]


def test_revoke_all_ends_every_device():
    conn = get_connection(":memory:")
    init_db(conn)
    auth = AuthManager(conn)
    user = _user(auth)
    tokens = [auth.issue_remember_token(user["id"]) for _ in range(3)]

    auth.revoke_all_remember_tokens(user["id"])

    assert all(not auth.login_with_token(token)[0] for token in tokens)


def test_deleting_the_account_removes_its_tokens():
    conn = get_connection(":memory:")
    init_db(conn)
    auth = AuthManager(conn)
    user = _user(auth)
    auth.issue_remember_token(user["id"])

    conn.execute("DELETE FROM user_settings WHERE user_id = ?", (user["id"],))
    conn.execute("DELETE FROM users WHERE id = ?", (user["id"],))
    conn.commit()

    assert conn.execute("SELECT COUNT(*) FROM remember_tokens").fetchone()[0] == 0


def test_token_login_reflects_the_current_role():
    conn = get_connection(":memory:")
    init_db(conn)
    auth = AuthManager(conn)
    user = _user(auth)
    token = auth.issue_remember_token(user["id"])
    conn.execute("UPDATE users SET role = 'admin' WHERE id = ?", (user["id"],))
    conn.commit()

    ok, result = auth.login_with_token(token)

    assert ok and result["role"] == "admin"


def test_old_databases_gain_the_token_table():
    conn = sqlite3.connect(":memory:")
    conn.executescript(
        "CREATE TABLE users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL,"
        " email TEXT UNIQUE NOT NULL, password_hash BLOB NOT NULL, salt BLOB NOT NULL,"
        " created_at TEXT NOT NULL DEFAULT (datetime('now')));"
    )
    init_db(conn)
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert "remember_tokens" in tables


def test_split_login_steps_match_login():
    conn = get_connection(":memory:")
    init_db(conn)
    auth = AuthManager(conn)
    assert auth.register("chris", "chris@example.com", "secret123")[0]

    record = auth.begin_login("chris")
    assert auth.verify_login(record, "secret123")
    assert not auth.verify_login(record, "nope-nope")
    assert not auth.verify_login(None, "secret123")  # unknown user never passes
    assert auth.complete_login(record)["username"] == "chris"


# ── LoginPreferences: token storage ─────────────────────────────────────────
def test_token_round_trip_and_clear(tmp_path):
    prefs = _prefs(tmp_path)
    assert prefs.remember_token() == ""

    prefs.set_remembered_username("chris")
    prefs.set_remember_token("abc.def")
    assert _prefs(tmp_path).remember_token() == "abc.def"

    prefs.clear_token()
    reloaded = _prefs(tmp_path)
    assert reloaded.remember_token() == ""
    assert reloaded.remembered_username() == "chris"  # the pre-fill survives


def test_clear_forgets_the_token_too(tmp_path):
    prefs = _prefs(tmp_path)
    prefs.set_remembered_username("chris")
    prefs.set_remember_token("abc.def")
    prefs.clear()

    reloaded = _prefs(tmp_path)
    assert reloaded.remember_token() == ""
    assert not reloaded.remember_enabled()


def test_token_is_ignored_when_remember_me_is_off(tmp_path):
    prefs = _prefs(tmp_path)
    prefs.set_remember_token("abc.def")
    prefs._settings.setValue("auth/remember_enabled", False)

    assert prefs.remember_token() == ""


def test_only_the_username_and_token_are_ever_written(tmp_path):
    prefs = _prefs(tmp_path)
    prefs.set_remembered_username("chris")
    prefs.set_remember_token("abc.def")

    keys = set(QSettings(str(tmp_path / "prefs.ini"), QSettings.Format.IniFormat).allKeys())
    assert keys == {
        "auth/remember_enabled",
        "auth/remembered_username",
        "auth/remember_token",
    }


# ── LoginWindow: the checkbox ───────────────────────────────────────────────
def _sign_in(window, wait_for, username="chris", password="secret123"):
    window._login_user.setText(username)
    window._login_pass.setText(password)
    window._do_login()


def test_remember_me_keeps_you_signed_in(auth_env, app, wait_for):
    auth, prefs = auth_env
    assert auth.register("chris", "chris@example.com", "secret123")[0]

    signed_in = []
    window = LoginWindow(auth, signed_in.append, preferences=prefs)
    window._remember.setChecked(True)
    _sign_in(window, wait_for)
    assert wait_for(lambda: bool(signed_in))

    assert prefs.remember_enabled()
    assert prefs.remembered_username() == "chris"
    token = prefs.remember_token()
    assert token

    # A fresh start (new manager state) resumes straight from the token.
    auth.logout()
    ok, user = auth.login_with_token(token)
    assert ok and user["username"] == "chris"


def test_signing_in_without_remember_me_stores_nothing(auth_env, app, wait_for):
    auth, prefs = auth_env
    assert auth.register("chris", "chris@example.com", "secret123")[0]

    signed_in = []
    window = LoginWindow(auth, signed_in.append, preferences=prefs)
    _sign_in(window, wait_for)
    assert wait_for(lambda: bool(signed_in))

    assert not prefs.remember_enabled()
    assert prefs.remember_token() == ""
    assert prefs.remembered_username() == ""


def test_a_new_sign_in_replaces_the_old_token(auth_env, app, wait_for):
    auth, prefs = auth_env
    assert auth.register("chris", "chris@example.com", "secret123")[0]
    first = []
    window = LoginWindow(auth, first.append, preferences=prefs)
    window._remember.setChecked(True)
    _sign_in(window, wait_for)
    assert wait_for(lambda: bool(first))
    old_token = prefs.remember_token()

    second = []
    window = LoginWindow(auth, second.append, preferences=prefs)
    window._login_pass.setText("secret123")
    window._do_login()
    assert wait_for(lambda: bool(second))

    new_token = prefs.remember_token()
    assert new_token and new_token != old_token
    assert not auth.login_with_token(old_token)[0]
    assert auth.login_with_token(new_token)[0]


def test_unticking_remember_me_ends_the_saved_session(auth_env, app, wait_for):
    auth, prefs = auth_env
    user = _user(auth)
    token = auth.issue_remember_token(user["id"])
    prefs.set_remembered_username("chris")
    prefs.set_remember_token(token)

    window = LoginWindow(auth, lambda u: None, preferences=prefs)
    assert window._remember.isChecked()
    window._remember.setChecked(False)

    assert prefs.remember_token() == ""
    assert not prefs.remember_enabled()
    assert not auth.login_with_token(token)[0]


def test_failed_sign_in_never_saves_anything(auth_env, app, wait_for):
    auth, prefs = auth_env
    assert auth.register("chris", "chris@example.com", "secret123")[0]

    window = LoginWindow(auth, lambda u: None, preferences=prefs)
    window._remember.setChecked(True)
    _sign_in(window, wait_for, password="wrong-password")
    assert wait_for(lambda: not window._busy)

    assert prefs.remember_token() == ""
    assert prefs.remembered_username() == "" or not prefs.remember_token()


def test_remember_hint_follows_the_checkbox(auth_env, app):
    auth, prefs = auth_env
    window = LoginWindow(auth, lambda u: None, preferences=prefs)
    assert window._remember_hint.text() == ""

    window._remember.setChecked(True)
    assert "30 days" in window._remember_hint.text()

    window._remember.setChecked(False)
    assert window._remember_hint.text() == ""


def test_prefilled_username_focuses_the_password(auth_env, app):
    auth, prefs = auth_env
    prefs.set_remembered_username("chris")
    window = LoginWindow(auth, lambda u: None, preferences=prefs)
    window.show()

    assert window._login_user.text() == "chris"
    assert window._remember.isChecked()
    assert window._remember_hint.text() != ""
    assert window.focusWidget() is window._login_pass


def test_notice_is_shown_above_the_sign_in_form(auth_env, app):
    auth, prefs = auth_env
    window = LoginWindow(
        auth, lambda u: None, preferences=prefs, notice="Your saved sign-in has expired."
    )

    assert not window._login_info.isHidden()
    assert "expired" in window._login_info.text
    window._go_register()
    window._go_login()
    assert window._login_info.isHidden()  # navigating away dismisses it
