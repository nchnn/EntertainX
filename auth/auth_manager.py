import hmac
import hashlib
import re
import secrets
import sqlite3

from theme.theme_manager import PRIMARY, SECONDARY

USERNAME_MIN = 3
USERNAME_MAX = 20
PASSWORD_MIN = 6

_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9]+$")


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

    # ── Registration / login ────────────────────────────────────────────────
    def register(self, username: str, email: str, password: str) -> tuple[bool, str]:
        username = username.strip()
        email = email.strip()

        errors = self.validate_registration(username, email, password)
        if errors:
            return False, next(iter(errors.values()))

        salt = secrets.token_bytes(16)
        pw_hash = self._hash_password(password, salt)
        try:
            cursor = self._conn.execute(
                "INSERT INTO users (username, email, password_hash, salt) VALUES (?, ?, ?, ?)",
                (username, email, pw_hash, salt),
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

    def login(self, username: str, password: str) -> tuple[bool, str | dict]:
        row = self._conn.execute(
            "SELECT id, username, email, password_hash, salt FROM users WHERE username = ?",
            (username.strip(),),
        ).fetchone()
        if row is None:
            return False, "Invalid username or password"
        uid, uname, email, stored_hash, salt = row
        candidate = self._hash_password(password, salt)
        if not hmac.compare_digest(candidate, stored_hash):
            return False, "Invalid username or password"
        self.current_user = {"id": uid, "username": uname, "email": email}
        return True, self.current_user

    def logout(self) -> None:
        self.current_user = None

    def is_logged_in(self) -> bool:
        return self.current_user is not None
