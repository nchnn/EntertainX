# EntertainX — Admin User Management (Design)

Date: 2026-11-17  
Status: approved — owner said “use defaults”

## Intent

Add local administrator accounts to EntertainX. An administrator can view every registered user and change another user's role. This supports the project demonstration of SQLite BLOB password hashing by showing each stored password hash as selectable hexadecimal text, not plaintext.

## Goals

1. Persist `user` or `admin` role on every `users` record. Existing accounts migrate to `user`.
2. Include role in the authenticated session.
3. Show an `Admin` sidebar destination only to administrators.
4. Show ID, username, email, role, readable password-hash hex, and created date in the admin table.
5. Let an administrator promote or demote another existing user.
6. Seed one administrator in the owner’s local `entertainx.db` after source changes are applied, then provide its credentials once.

## Non-goals

- No password reset, deletion, registration from the admin page, audit history, remote administration, or role hierarchy beyond `user` and `admin`.
- No plaintext password, salt, or raw BLOB display in the UI.
- No hardcoded administrator password in application source.

## Security and behavior decisions

- `users.role` is constrained to `user` or `admin` and defaults to `user`.
- Database migration is additive: legacy databases receive the `role` column without replacing existing accounts.
- `AuthManager` enforces admin authorization before listing users or changing roles; hidden navigation alone is not authorization.
- Password hashes are rendered with `bytes.hex()` as 64-character PBKDF2-SHA256 hexadecimal strings.
- The admin may not change their own role, preventing accidental self-lockout. A changed user receives the new access level next sign-in.
- Salt remains stored in SQLite for password verification but is omitted from the table because it is outside the approved display scope.

## Approved layout

Admin-only sidebar item. `User Management` page has one table with a role combobox per row and an inline success/error banner. The hash column is selectable and horizontally scrollable.
