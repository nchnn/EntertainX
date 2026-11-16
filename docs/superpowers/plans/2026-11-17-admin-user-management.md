# Admin User Management Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add local administrator roles, an administrator-only user-management table, safe role changes, and one test administrator account.

**Architecture:** SQLite gains an additive `users.role` migration so existing accounts default to `user`. `AuthManager` is the authorization boundary: it returns session roles, lists safe user records only for the active administrator, and permits role changes only by an administrator other than the target user. `MainWindow` passes authenticated role and manager into navigation; only administrators receive the `AdminPage` table.

**Tech Stack:** Python 3.12, PySide6 6.12, SQLite (`sqlite3`), PBKDF2-HMAC-SHA256 (`hashlib`). No new dependency.

**Spec:** `docs/superpowers/specs/2026-11-17-admin-user-management-design.md`

## Global Constraints

- Preserve PBKDF2-HMAC-SHA256, 600,000 iterations, per-user random salts, and constant-time password comparison.
- Do not store, log, return, or display plaintext passwords or salts.
- Render `password_hash` BLOB only as `bytes.hex()` in the administrator-only table.
- Roles are exactly `user` and `admin`; legacy accounts migrate to `user`.
- All SQL remains parameterized; no new dependency or ORM.
- An admin cannot alter their own role; changed roles take effect at target’s next sign-in.
- Do not commit, push, or merge unless the owner explicitly asks.
- Seed credentials are generated once outside source code; never hardcode the test password.

## Review Focus

1. **Legacy database without `role`:** `init_db()` must add `role` without losing existing rows, and every migrated account must read as `user`.
2. **Regular user calls backend directly:** `AuthManager.list_users()` and `change_user_role()` must deny it even when the UI is bypassed.
3. **Invalid target or role:** unknown IDs, `owner`, empty strings, and self-demotion must make no database change.
4. **Hash disclosure boundary:** table records contain full 64-character hex hashes but omit salt and plaintext password.
5. **Role navigation leak:** a regular session must have no `Admin` sidebar item or page; an admin session must have both.

---

### Task 1: Role Migration and Auth Authorization Boundary

**Files:**
- Modify: `database/db.py:10-27`
- Modify: `auth/auth_manager.py:17-117`
- Modify: `tests/test_db.py:14-49`
- Modify: `tests/test_auth.py:18-89`
- Create: `tests/test_admin_auth.py`

**Interfaces:**
- Consumes: existing SQLite `users` table and `AuthManager.current_user` session state.
- Produces:
  - `init_db(conn: sqlite3.Connection) -> None` creates new `users` tables with `role TEXT NOT NULL DEFAULT 'user' CHECK (role IN ('user', 'admin'))`, and uses `ALTER TABLE` only when existing `users` lacks that column.
  - `AuthManager.login(username: str, password: str) -> tuple[bool, str | dict]` returns `id`, `username`, `email`, and `role` on success.
  - `AuthManager.list_users() -> tuple[bool, list[dict] | str]` returns records with `id`, `username`, `email`, `role`, `password_hash_hex`, and `created_at` only for active admins.
  - `AuthManager.change_user_role(user_id: int, role: str) -> tuple[bool, str]` permits only active admins to change another existing user to `user` or `admin`.

- [ ] **Step 1: Write database migration tests**

Add a legacy `users` table without `role`, insert one known user, run `init_db(conn)`, then assert its role is literal `"user"`. Update schema coverage to require `role`, and assert SQLite rejects an inserted role of literal `"owner"`.

- [ ] **Step 2: Run migration tests and verify RED**

Run: `venv/Scripts/python.exe -m pytest tests/test_db.py -v`

Expected: FAIL because existing schema has no `role` column and no migration.

- [ ] **Step 3: Implement additive role migration in `database/db.py`**

Keep `CREATE TABLE IF NOT EXISTS`; add the constrained `role` column to its new-table definition. After schema creation, inspect `PRAGMA table_info(users)` and execute the one parameter-free migration DDL statement only if `role` is absent. Commit migration transaction with the existing initialization commit.

- [ ] **Step 4: Run migration tests and verify GREEN**

Run: `venv/Scripts/python.exe -m pytest tests/test_db.py -v`

Expected: all database tests pass.

- [ ] **Step 5: Write authorization tests**

In `tests/test_admin_auth.py`, use real in-memory SQLite and real `AuthManager` instances. Cover:

```python
def test_admin_lists_hex_hashes_without_salts_or_plaintext(): ...
def test_regular_user_cannot_list_users_or_change_roles(): ...
def test_admin_changes_another_users_role_but_not_own_role(): ...
def test_invalid_role_or_unknown_user_does_not_change_any_role(): ...
```

Assert each displayed hash is a literal 64-character lowercase hexadecimal string; assert neither `salt` nor supplied plaintext password appears in a returned user record.

- [ ] **Step 6: Run authorization tests and verify RED**

Run: `venv/Scripts/python.exe -m pytest tests/test_admin_auth.py -v`

Expected: FAIL because admin methods do not exist and sessions lack `role`.

- [ ] **Step 7: Implement role-aware `AuthManager` methods**

Make login select and store `role`. Add an internal active-admin predicate. `list_users()` selects only the approved columns, converts each BLOB to `password_hash_hex`, and denies non-admin sessions. `change_user_role()` validates allowed roles, active-admin status, target existence, and non-self target before issuing its parameterized update and committing.

- [ ] **Step 8: Run auth-focused tests and verify GREEN**

Run: `venv/Scripts/python.exe -m pytest tests/test_auth.py tests/test_admin_auth.py -v`

Expected: all selected tests pass.

- [ ] **Step 9: Inspect task diff**

Run: `git diff --check && git diff -- database/db.py auth/auth_manager.py tests/test_db.py tests/test_auth.py tests/test_admin_auth.py`

Expected: no whitespace errors; only migration, role/session, authorization, and tests change.

---

### Task 2: Admin-Only Navigation and User-Management Page

**Files:**
- Create: `ui/pages/admin.py`
- Modify: `ui/sidebar.py:20-93`
- Modify: `ui/content_area.py:15-91`
- Modify: `ui/main_window.py:26-40`
- Modify: `theme/theme_manager.py:529-590`
- Modify: `tests/test_navigation.py:8-143`
- Create: `tests/test_admin_page.py`

**Interfaces:**
- Consumes: an authenticated `user` dictionary containing `role`, and `AuthManager.list_users()` / `change_user_role()` from Task 1.
- Produces:
  - `AdminPage(auth_manager: AuthManager, parent: QWidget | None = None)` with public `table: QTableWidget` and `refresh_users() -> None`.
  - `Sidebar(..., is_admin: bool = False)` includes `Admin` only when true.
  - `ContentArea(user: dict | None = None, auth_manager: AuthManager | None = None, ...)` adds `Admin` only for an admin user with manager access.

- [ ] **Step 1: Write navigation and page tests**

Add behavior tests that a regular `Sidebar` and `ContentArea` do not expose `Admin`; an admin `MainWindow` does. In `tests/test_admin_page.py`, build real in-memory admin/user records, then assert `AdminPage.table` has six columns titled `ID`, `Username`, `Email`, `Role`, `Password hash (hex)`, and `Created`; assert hash cells equal the backend’s full 64-character hex and the current admin role selector is disabled.

- [ ] **Step 2: Run UI tests and verify RED**

Run: `venv/Scripts/python.exe -m pytest tests/test_navigation.py tests/test_admin_page.py -v`

Expected: FAIL because neither admin navigation nor `AdminPage` exists.

- [ ] **Step 3: Implement conditional navigation wiring**

Extend `Sidebar` with an instance-local category list so regular users preserve current navigation. In `MainWindow`, pass admin state from `user["role"]`; in `ContentArea`, create and register `AdminPage` only for the role-qualified session and pass the manager. Preserve all current non-admin constructors and tests.

- [ ] **Step 4: Implement `AdminPage`**

Use `PageShell`, `InlineBanner`, `QTableWidget`, `QTableWidgetItem`, and `QComboBox`. Populate six non-editable columns from `list_users()`. Make the full hash value selectable text. Add one role combobox per non-current row, change via `change_user_role()`, refresh data after success, and restore data plus show an error banner after failure. Do not render salts or plaintext passwords.

- [ ] **Step 5: Add minimal table QSS**

Style table, header, selected cell, and grid borders using existing theme tokens. Do not introduce UI color literals or assets/dependencies.

- [ ] **Step 6: Run UI tests and verify GREEN**

Run: `venv/Scripts/python.exe -m pytest tests/test_navigation.py tests/test_admin_page.py -v`

Expected: all selected tests pass.

- [ ] **Step 7: Inspect task diff**

Run: `git diff --check && git diff -- ui/sidebar.py ui/content_area.py ui/main_window.py ui/pages/admin.py theme/theme_manager.py tests/test_navigation.py tests/test_admin_page.py`

Expected: no whitespace errors; regular-user navigation remains unchanged.

---

### Task 3: Seed and Verify Test Administrator

**Files:**
- Modify at runtime only: target `entertainx.db` after Task 1 migration; no seed script or credential is added to source control.
- Modify: `tests/test_admin_auth.py` only if an untested seed prerequisite is discovered.

**Interfaces:**
- Consumes: `get_connection()`, `init_db(conn)`, `AuthManager.register()`, and the migrated `users.role` schema.
- Produces: one account: username `admin`, email `admin@entertainx.local`, generated password retained only for final owner handoff, role `admin`.

- [ ] **Step 1: Generate test password in memory**

Use `secrets.token_urlsafe()` within one execution session. Do not write it to source, markdown, terminal logs, or the database other than its derived password hash.

- [ ] **Step 2: Run schema migration against target database**

Open target `entertainx.db` through project database code and run `init_db(conn)`. Verify existing user count is unchanged and every pre-existing user has `role = 'user'`.

- [ ] **Step 3: Register and promote seed administrator once**

Use the project `AuthManager.register("admin", "admin@entertainx.local", generated_password)`. In the same local transaction, promote that new record to `admin` with a parameterized statement. If `admin` already exists, stop rather than overwrite credentials or roles.

- [ ] **Step 4: Verify seeded account through production auth path**

Open a fresh connection, log in with generated credentials through `AuthManager.login()`, assert `user["role"] == "admin"`, call `list_users()`, and assert its admin row contains a 64-character hex password hash and no salt field.

- [ ] **Step 5: Inspect database effect without secrets**

Query only `id`, `username`, `email`, `role`, and `length(password_hash)` for the new admin. Expected: `admin`, `admin@entertainx.local`, `admin`, and 32-byte hash.

---

### Task 4: Whole-Feature Verification and Review

**Files:**
- Review: all Task 1–3 files and target SQLite schema.

**Interfaces:**
- Consumes: complete implementation and seeded administrator.
- Produces: verified test evidence and reviewer findings before user handoff.

- [ ] **Step 1: Run full suite**

Run: `venv/Scripts/python.exe -m pytest -v --tb=short tests/`

Expected: all tests pass with no failures.

- [ ] **Step 2: Run source syntax check**

Run: `venv/Scripts/python.exe -m compileall -q auth database ui main.py`

Expected: exit code 0.

- [ ] **Step 3: Review final scope and security boundaries**

Fresh reviewer checks diff against design, specifically authorization enforcement, migration safety, BLOB hex rendering, self-role protection, and whether any password or salt is exposed beyond approved hash hex.

- [ ] **Step 4: Re-run full suite after review fixes**

Run: `venv/Scripts/python.exe -m pytest -v --tb=short tests/`

Expected: all tests pass.

- [ ] **Step 5: Report actual branch and database state**

Report worktree branch, source files changed, full verification result, administrator username/email/password once, and any remaining step required to merge the branch into the original checkout.

## Self-Review

- **Spec coverage:** Task 1 covers roles, legacy migration, backend authorization, and hash serialization. Task 2 covers admin-only page/table and role controls. Task 3 fulfills the requested test account. Task 4 verifies all requested behavior.
- **Type consistency:** All UI consumers use `AuthManager.list_users()` and `change_user_role()` defined in Task 1; `AdminPage` receives manager through `ContentArea` from `MainWindow`.
- **Review-focus coverage:** migration in Task 1 steps 1–4; backend bypass and bad input in Task 1 steps 5–8; hash boundary in Task 1/2 tests; role-navigation leak in Task 2 tests.
- **Proportion:** No new abstraction, dependency, persistent credential file, or audit subsystem. Table renders existing records directly from authentication manager.
