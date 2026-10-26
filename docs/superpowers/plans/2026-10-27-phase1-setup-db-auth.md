# Phase 1: Project Setup + Database + Authentication — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Scaffold EntertainX as a venv-based PySide6 project with SQLite database, user registration, login, logout, and session management.

**Architecture:** PySide6 desktop app using Python 3.12 venv. SQLite via `sqlite3` stdlib. Password hashing via `hashlib.pbkdf2_hmac` with per-user random salt. Auth state held in-memory as a session object; UI shows login/register screen when logged out, blocks app content until authenticated.

**Tech Stack:** Python 3.12, PySide6, sqlite3 (stdlib), hashlib (stdlib), os/secrets (stdlib for salt generation)

**Spec:** `EntertainX_GOAL_REVISED.md` sections 6.1, 6.2, 9.1, 11; `GOAL.MD` sections 1, 10

## Global Constraints

- Python 3.12 via venv (`py -3.12 -m venv venv`)
- PySide6 as GUI framework (LGPL) — only third-party dependency for this phase
- SQLite via stdlib `sqlite3` — no ORM, no cloud DB
- Password hashing: `hashlib.pbkdf2_hmac("sha256", ...)` with 16-byte `secrets.token_bytes` salt, 600_000 iterations
- Never store plain-text passwords; never log/display passwords, salts, or hashes
- Parameterized SQL queries only — no string formatting/interpolation for SQL
- API keys never hardcoded; `.env` excluded from git via `.gitignore`
- Windows primary dev platform
- All user-facing error messages must not reveal whether a username exists

## Review Focus

1. **SQL injection via username/email** — registration and login must use parameterized queries; a username containing `'; DROP TABLE users;--` must be stored literally or rejected, never executed
2. **Empty/whitespace-only credentials** — register and login must reject blank username, blank email, blank password with a clear message before touching the DB
3. **Duplicate email with different case** — `user@Mail.com` and `user@mail.com` must be treated as the same email; use case-insensitive comparison or normalize before insert
4. **Password with unicode/emoji** — `hashlib.pbkdf2_hmac` takes bytes; password must be encoded to UTF-8 before hashing; a password like `pässwörd🔑` must round-trip through register→login
5. **DB file missing or corrupt on startup** — `init_db()` must create tables if not exist; a missing `.db` file must not crash the app

---

### Task 1: Project Skeleton + Virtual Environment

**Files:**
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `.gitignore`
- Create: `README.md`
- Create: `main.py`

**Interfaces:**
- Consumes: nothing
- Produces: runnable venv with PySide6 installed; `main.py` that opens an empty PySide6 window titled "EntertainX"

- [ ] **Step 1: Create venv and install PySide6**

```bash
cd C:/Users/chris/OneDrive/Desktop/EntertainX
py -3.12 -m venv venv
venv/Scripts/activate
pip install PySide6
pip freeze > requirements.txt
```

- [ ] **Step 2: Create `.gitignore`**

Must include: `venv/`, `.env`, `__pycache__/`, `*.pyc`, `.idea/`, `.vscode/`

Note: `*.db` is NOT gitignored — the SQLite database file stays in the repo so the project is portable.

- [ ] **Step 3: Create `.env.example`**

```
# API keys go here (none needed for Phase 1)
# TMDB_API_KEY=
# RAWG_API_KEY=
```

- [ ] **Step 4: Create `README.md`**

Project name, one-line description, setup instructions:
```
py -3.12 -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

- [ ] **Step 5: Create `main.py`**

Minimal PySide6 app: `QApplication` + `QMainWindow` with title "EntertainX", size 1200×800. Show window and exec app. Import nothing from project yet.

- [ ] **Step 6: Run to verify window opens**

Run: `python main.py`
Expected: window titled "EntertainX" appears and can be closed cleanly

- [ ] **Step 7: Init git and commit**

```bash
git init
git add .
git commit -m "chore: project skeleton with venv and PySide6"
```

---

### Task 2: Database Layer

**Files:**
- Create: `database/__init__.py` (empty)
- Create: `database/db.py`
- Create: `tests/test_db.py`

**Interfaces:**
- Consumes: nothing
- Produces:
  - `get_connection() -> sqlite3.Connection` — returns connection to `entertainx.db`, with foreign keys enabled
  - `init_db() -> None` — creates `users` and `user_settings` tables if not exist
  - `users` table: `id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL, email TEXT UNIQUE NOT NULL COLLATE NOCASE, password_hash BLOB NOT NULL, salt BLOB NOT NULL, created_at TEXT NOT NULL DEFAULT (datetime('now'))`
  - `user_settings` table: `user_id INTEGER PRIMARY KEY REFERENCES users(id), primary_color TEXT NOT NULL DEFAULT '#6C63FF', secondary_color TEXT NOT NULL DEFAULT '#FF6584', updated_at TEXT NOT NULL DEFAULT (datetime('now'))`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_db.py
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_db.py -v`
Expected: FAIL — `database.db` module not found

- [ ] **Step 3: Implement `database/db.py`**

- `get_connection(db_path="entertainx.db")` — opens SQLite, enables `PRAGMA foreign_keys = ON`, returns connection
- `init_db(conn)` — executes `CREATE TABLE IF NOT EXISTS` for `users` and `user_settings` with the schema above
- Email column uses `COLLATE NOCASE` for case-insensitive uniqueness

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_db.py -v`
Expected: all 4 PASS

- [ ] **Step 5: Commit**

```bash
git add database/ tests/
git commit -m "feat: database layer with users and user_settings tables"
```

---

### Task 3: Auth Manager — Registration & Login Logic

**Files:**
- Create: `auth/__init__.py` (empty)
- Create: `auth/auth_manager.py`
- Create: `tests/test_auth.py`

**Interfaces:**
- Consumes: `database.db.get_connection`, `database.db.init_db`
- Produces:
  - `AuthManager(conn: sqlite3.Connection)`
  - `AuthManager.register(username: str, email: str, password: str) -> tuple[bool, str]` — returns `(True, "Registration successful")` or `(False, "error message")`
  - `AuthManager.login(username: str, password: str) -> tuple[bool, str | dict]` — returns `(True, {"id": int, "username": str, "email": str})` or `(False, "Invalid credentials")`
  - `AuthManager.current_user` — `dict | None`, the logged-in user
  - `AuthManager.logout() -> None` — clears `current_user`
  - `AuthManager.is_logged_in() -> bool`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_auth.py
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_auth.py -v`
Expected: FAIL — `auth.auth_manager` not found

- [ ] **Step 3: Implement `auth/auth_manager.py`**

- `__init__(self, conn)` — stores connection
- `_hash_password(password: str, salt: bytes) -> bytes` — `hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 600_000)`
- `register()` — validate non-empty/whitespace fields, generate 16-byte salt via `secrets.token_bytes(16)`, hash password, INSERT with parameterized query, catch `IntegrityError` for duplicate username/email
- `login()` — SELECT by username (parameterized), compare hash, set `current_user` dict on success, return generic "Invalid credentials" on any failure
- `logout()` — set `current_user = None`
- `is_logged_in()` — `return self.current_user is not None`

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_auth.py -v`
Expected: all 9 PASS

- [ ] **Step 5: Commit**

```bash
git add auth/ tests/test_auth.py
git commit -m "feat: auth manager with register, login, logout"
```

---

### Task 4: Login & Register UI

**Files:**
- Create: `ui/__init__.py` (empty)
- Create: `ui/login_window.py`
- Modify: `main.py`

**Interfaces:**
- Consumes: `auth.auth_manager.AuthManager`
- Produces:
  - `LoginWindow(auth_manager: AuthManager, on_login_success: Callable)` — QWidget with login/register forms
  - Signal/callback: calls `on_login_success(user_dict)` after successful login
  - `main.py` initializes DB, creates `AuthManager`, shows `LoginWindow`, transitions to a placeholder main window on login

- [ ] **Step 1: Implement `ui/login_window.py`**

`LoginWindow(QWidget)`:
- Stacked layout with two "pages": Login and Register
- **Login page:** username + password fields (`QLineEdit`, password echoed as `Password`), Login button, "Don't have an account? Register" link label
- **Register page:** username + email + password + confirm password fields, Register button, "Already have an account? Login" link label
- On Login click: call `auth_manager.login()`, show error in `QLabel` if failed, call `on_login_success` if ok
- On Register click: validate confirm password matches, call `auth_manager.register()`, show error/success, auto-switch to login page on success
- Clear error label on page switch
- All fields have placeholder text

- [ ] **Step 2: Modify `main.py` to wire auth flow**

- `main.py` creates `get_connection()`, calls `init_db()`, creates `AuthManager`
- Shows `LoginWindow` as central widget
- `on_login_success` swaps to a placeholder `QLabel("Welcome, {username}! Main app goes here.")` with a Logout button
- Logout button calls `auth_manager.logout()` and swaps back to `LoginWindow`

- [ ] **Step 3: Manual test — register flow**

Run: `python main.py`
1. Click "Register" link → register form appears
2. Fill username/email/password/confirm → click Register → success message, switches to login
3. Try duplicate username → error message shown
4. Try mismatched passwords → error message shown

- [ ] **Step 4: Manual test — login/logout flow**

1. Login with registered credentials → placeholder main screen with welcome message
2. Click Logout → returns to login screen
3. Login with wrong password → error message, stays on login
4. Close and reopen app → must login again (no persistent session)

- [ ] **Step 5: Commit**

```bash
git add ui/ main.py
git commit -m "feat: login and register UI with auth flow"
```

---

### Task 5: Integration Test + Cleanup

**Files:**
- Create: `tests/__init__.py` (empty)
- Create: `tests/test_integration.py`
- Modify: `README.md` (add test instructions)

**Interfaces:**
- Consumes: `database.db.*`, `auth.auth_manager.AuthManager`
- Produces: full integration test covering register → login → logout → re-login cycle

- [ ] **Step 1: Write integration test**

```python
# tests/test_integration.py
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
```

- [ ] **Step 2: Run all tests**

Run: `python -m pytest tests/ -v`
Expected: all tests PASS

- [ ] **Step 3: Update `README.md`**

Add testing section:
```
## Testing
venv\Scripts\activate
python -m pytest tests/ -v
```

- [ ] **Step 4: Final commit**

```bash
git add .
git commit -m "feat: integration tests and README update — phase 1 complete"
```
