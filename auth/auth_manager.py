import hmac
import hashlib
import re
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import NamedTuple

from theme.theme_manager import PRIMARY, SECONDARY

USERNAME_MIN = 3
USERNAME_MAX = 20
PASSWORD_MIN = 6
REMEMBER_DAYS = 30

_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9]+$")

# Hashing against this when the username is unknown keeps "no such user" and
# "wrong password" equally slow, so timing does not reveal which accounts exist.
_DUMMY_SALT = b"\x00" * 16


class LoginRecord(NamedTuple):
    """What the sign-in check needs about an account, read once on the GUI thread."""

    user_id: int
    username: str
    email: str
    password_hash: bytes
    salt: bytes
    role: str


class AuthManager:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn
        self.current_user: dict | None = None

    def _hash_password(self, password: str, salt: bytes) -> bytes:
        return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 600_000)

    # ── Validation ──────────────────────────────────────────────────────────
    @staticmethod
    def validate_username(username: str) -> str | None:
        username = username.strip()
        if not username:
            return "Username is required"
        if len(username) < USERNAME_MIN:
            return f"Username must be at least {USERNAME_MIN} characters"
        if len(username) > USERNAME_MAX:
            return f"Username must be {USERNAME_MAX} characters or fewer"
        if not _USERNAME_PATTERN.match(username):
            return "Username can only contain letters and numbers"
        return None

    @staticmethod
    def validate_email(email: str) -> str | None:
        email = email.strip()
        if not email:
            return "Email is required"
        if not _EMAIL_PATTERN.match(email):
            return "Enter a valid email address"
        return None

    @staticmethod
    def validate_password(password: str) -> str | None:
        if not password:
            return "Password is required"
        if len(password) < PASSWORD_MIN:
            return f"Password must be at least {PASSWORD_MIN} characters"
        return None

    def validate_registration(
        self, username: str, email: str, password: str
    ) -> dict[str, str]:
        """Return ``{field: message}`` for every invalid registration field."""
        errors: dict[str, str] = {}
        for field, error in (
            ("username", self.validate_username(username)),
            ("email", self.validate_email(email)),
            ("password", self.validate_password(password)),
        ):
            if error:
                errors[field] = error
        return errors

    # ── Registration ────────────────────────────────────────────────────────
    # ``register`` is split so a GUI can run the slow, database-free hashing on
    # a worker thread and then store the result on the thread that owns the
    # SQLite connection.
    def hash_credentials(self, password: str) -> tuple[bytes, bytes]:
        """Return ``(password_hash, salt)``. Safe to call from any thread."""
        salt = secrets.token_bytes(16)
        return self._hash_password(password, salt), salt

    def store_registration(
        self, username: str, email: str, pw_hash: bytes, salt: bytes
    ) -> tuple[bool, str]:
        """Insert an account whose password is already hashed."""
        try:
            cursor = self._conn.execute(
                "INSERT INTO users (username, email, password_hash, salt) VALUES (?, ?, ?, ?)",
                (username.strip(), email.strip(), pw_hash, salt),
            )
            self._conn.execute(
                "INSERT OR IGNORE INTO user_settings "
                "(user_id, primary_color, secondary_color) VALUES (?, ?, ?)",
                (cursor.lastrowid, PRIMARY, SECONDARY),
            )
            self._conn.commit()
            return True, "Registration successful"
        except sqlite3.IntegrityError as e:
            msg = str(e).lower()
            if "username" in msg:
                return False, "Username already taken"
            return False, "Email already registered"

    def register(self, username: str, email: str, password: str) -> tuple[bool, str]:
        username = username.strip()
        email = email.strip()

        errors = self.validate_registration(username, email, password)
        if errors:
            return False, next(iter(errors.values()))

        pw_hash, salt = self.hash_credentials(password)
        return self.store_registration(username, email, pw_hash, salt)

    # ── Login ───────────────────────────────────────────────────────────────
    # Same split as registration: read on the GUI thread, hash anywhere.
    def begin_login(self, username: str) -> LoginRecord | None:
        """Look the account up. ``None`` means no such user."""
        row = self._conn.execute(
            "SELECT id, username, email, password_hash, salt, role FROM users WHERE username = ?",
            (username.strip(),),
        ).fetchone()
        return LoginRecord(*row) if row is not None else None

    def verify_login(self, record: LoginRecord | None, password: str) -> bool:
        """Check ``password`` against ``record``. Safe to call from any thread."""
        candidate = self._hash_password(
            password, record.salt if record is not None else _DUMMY_SALT
        )
        if record is None:
            return False
        return hmac.compare_digest(candidate, record.password_hash)

    def complete_login(self, record: LoginRecord) -> dict:
        """Start the session for an account that passed :meth:`verify_login`."""
        self.current_user = {
            "id": record.user_id,
            "username": record.username,
            "email": record.email,
            "role": record.role,
        }
        return self.current_user

    def login(self, username: str, password: str) -> tuple[bool, str | dict]:
        record = self.begin_login(username)
        if not self.verify_login(record, password):
            return False, "Invalid username or password"
        return True, self.complete_login(record)

    # ── Remember Me ─────────────────────────────────────────────────────────
    # A token is "<selector>.<validator>". The selector is a public lookup key;
    # only a SHA-256 hash of the validator is stored, so a copy of the database
    # cannot be turned into a signed-in session.
    @staticmethod
    def _utc_stamp(moment: datetime) -> str:
        return moment.strftime("%Y-%m-%d %H:%M:%S")

    def _expiry(self) -> str:
        return self._utc_stamp(datetime.now(timezone.utc) + timedelta(days=REMEMBER_DAYS))

    def issue_remember_token(self, user_id: int) -> str:
        """Create a session token for ``user_id`` and return it for local storage."""
        selector = secrets.token_hex(8)
        validator = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(validator.encode("utf-8")).digest()

        self._conn.execute(
            "DELETE FROM remember_tokens WHERE expires_at <= datetime('now')"
        )
        self._conn.execute(
            "INSERT INTO remember_tokens (selector, user_id, token_hash, expires_at) "
            "VALUES (?, ?, ?, ?)",
            (selector, user_id, token_hash, self._expiry()),
        )
        self._conn.commit()
        return f"{selector}.{validator}"

    def login_with_token(self, token: str) -> tuple[bool, str | dict]:
        """Sign in from a stored token. Extends it by 30 days on success."""
        selector, separator, validator = (token or "").partition(".")
        if not separator or not selector or not validator:
            return False, "Your saved sign-in is not valid."

        row = self._conn.execute(
            "SELECT t.token_hash, t.expires_at > datetime('now'), "
            "       u.id, u.username, u.email, u.role "
            "FROM remember_tokens t JOIN users u ON u.id = t.user_id "
            "WHERE t.selector = ?",
            (selector,),
        ).fetchone()
        if row is None:
            return False, "Your saved sign-in has ended."

        token_hash, unexpired, user_id, username, email, role = row
        if not unexpired:
            self._drop_selector(selector)
            return False, "Your saved sign-in has expired."

        candidate = hashlib.sha256(validator.encode("utf-8")).digest()
        if not hmac.compare_digest(candidate, token_hash):
            # A known selector with the wrong validator means the token was
            # tampered with or copied; retire it rather than allow more guesses.
            self._drop_selector(selector)
            return False, "Your saved sign-in is not valid."

        self._conn.execute(
            "UPDATE remember_tokens SET expires_at = ? WHERE selector = ?",
            (self._expiry(), selector),
        )
        self._conn.commit()
        self.current_user = {
            "id": user_id,
            "username": username,
            "email": email,
            "role": role,
        }
        return True, self.current_user

    def _drop_selector(self, selector: str) -> None:
        self._conn.execute("DELETE FROM remember_tokens WHERE selector = ?", (selector,))
        self._conn.commit()

    def revoke_remember_token(self, token: str) -> None:
        """End the session a token belongs to. Unknown tokens are ignored."""
        selector = (token or "").partition(".")[0]
        if selector:
            self._drop_selector(selector)

    def revoke_all_remember_tokens(self, user_id: int) -> None:
        """End every remembered session of one account (e.g. after a password change)."""
        self._conn.execute("DELETE FROM remember_tokens WHERE user_id = ?", (user_id,))
        self._conn.commit()

    # ── Admin ───────────────────────────────────────────────────────────────
    def _is_active_admin(self) -> bool:
        return self.current_user is not None and self.current_user.get("role") == "admin"

    def list_users(self) -> tuple[bool, list[dict] | str]:
        if not self._is_active_admin():
            return False, "Administrator access required"

        rows = self._conn.execute(
            "SELECT id, username, email, role, password_hash, created_at FROM users ORDER BY id"
        ).fetchall()
        return True, [
            {
                "id": user_id,
                "username": username,
                "email": email,
                "role": role,
                "password_hash_hex": password_hash.hex(),
                "created_at": created_at,
            }
            for user_id, username, email, role, password_hash, created_at in rows
        ]

    def change_user_role(self, user_id: int, role: str) -> tuple[bool, str]:
        if not self._is_active_admin():
            return False, "Administrator access required"
        if role not in ("user", "admin"):
            return False, "Invalid role"
        if self._conn.execute("SELECT 1 FROM users WHERE id = ?", (user_id,)).fetchone() is None:
            return False, "User not found"
        current_user = self.current_user
        if current_user is None:
            return False, "Administrator access required"
        if user_id == current_user["id"]:
            return False, "Administrators cannot change their own role"

        self._conn.execute("UPDATE users SET role = ? WHERE id = ?", (role, user_id))
        self._conn.commit()
        return True, "User role updated"

    def logout(self) -> None:
        self.current_user = None

    def is_logged_in(self) -> bool:
        return self.current_user is not None
