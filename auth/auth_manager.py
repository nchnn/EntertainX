import hashlib
import secrets
import sqlite3


class AuthManager:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn
        self.current_user: dict | None = None

    def _hash_password(self, password: str, salt: bytes) -> bytes:
        return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 600_000)

    def register(self, username: str, email: str, password: str) -> tuple[bool, str]:
        if not username.strip():
            return False, "Username is required"
        if not email.strip():
            return False, "Email is required"
        if not password:
            return False, "Password is required"
        salt = secrets.token_bytes(16)
        pw_hash = self._hash_password(password, salt)
        try:
            self._conn.execute(
                "INSERT INTO users (username, email, password_hash, salt) VALUES (?, ?, ?, ?)",
                (username, email, pw_hash, salt),
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
            (username,),
        ).fetchone()
        if row is None:
            return False, "Invalid credentials"
        uid, uname, email, stored_hash, salt = row
        if self._hash_password(password, salt) != stored_hash:
            return False, "Invalid credentials"
        self.current_user = {"id": uid, "username": uname, "email": email}
        return True, self.current_user

    def logout(self) -> None:
        self.current_user = None

    def is_logged_in(self) -> bool:
        return self.current_user is not None
