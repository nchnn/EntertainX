"""Local login preferences (Remember Me) stored with ``QSettings``.

Remember Me keeps two things on this device:

* the username, so the sign-in form is pre-filled, and
* a random session token, so the app can sign the user straight back in.

The password is never written anywhere. The token is worthless on its own to
anyone reading the database: ``AuthManager`` only stores its SHA-256 hash, and
signing out revokes it.
"""

from __future__ import annotations

from PySide6.QtCore import QSettings

ORGANISATION = "EntertainX"
APPLICATION = "EntertainX"

_REMEMBER_KEY = "auth/remember_enabled"
_USERNAME_KEY = "auth/remembered_username"
_TOKEN_KEY = "auth/remember_token"


class LoginPreferences:
    """Thin wrapper around ``QSettings`` so tests can inject their own store."""

    def __init__(self, settings: QSettings | None = None) -> None:
        self._settings = settings if settings is not None else QSettings(ORGANISATION, APPLICATION)

    # ── Reads ───────────────────────────────────────────────────────────────
    def remember_enabled(self) -> bool:
        return bool(self._settings.value(_REMEMBER_KEY, False, type=bool))

    def remembered_username(self) -> str:
        if not self.remember_enabled():
            return ""
        return self._settings.value(_USERNAME_KEY, "", type=str) or ""

    def remember_token(self) -> str:
        if not self.remember_enabled():
            return ""
        return self._settings.value(_TOKEN_KEY, "", type=str) or ""

    # ── Writes ──────────────────────────────────────────────────────────────
    def set_remembered_username(self, username: str) -> None:
        username = username.strip()
        if not username:
            self.clear()
            return
        self._settings.setValue(_REMEMBER_KEY, True)
        self._settings.setValue(_USERNAME_KEY, username)
        self._settings.sync()

    def set_remember_token(self, token: str) -> None:
        """Store the session token; only meaningful while Remember Me is on."""
        if not token:
            self.clear_token()
            return
        self._settings.setValue(_REMEMBER_KEY, True)
        self._settings.setValue(_TOKEN_KEY, token)
        self._settings.sync()

    def clear_token(self) -> None:
        """Forget the session token but keep the pre-filled username."""
        self._settings.remove(_TOKEN_KEY)
        self._settings.sync()

    def clear(self) -> None:
        """Forget everything Remember Me stored."""
        self._settings.remove(_USERNAME_KEY)
        self._settings.remove(_TOKEN_KEY)
        self._settings.remove(_REMEMBER_KEY)
        self._settings.sync()
