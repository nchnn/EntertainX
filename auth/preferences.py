"""Local login preferences (Remember Me) stored with ``QSettings``.

Only the username is ever remembered. Passwords are never written to disk and
no automatic login is performed.
"""

from __future__ import annotations

from PySide6.QtCore import QSettings

ORGANISATION = "EntertainX"
APPLICATION = "EntertainX"

_REMEMBER_KEY = "auth/remember_enabled"
_USERNAME_KEY = "auth/remembered_username"


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

    # ── Writes ──────────────────────────────────────────────────────────────
    def set_remembered_username(self, username: str) -> None:
        username = username.strip()
        if not username:
            self.clear()
            return
        self._settings.setValue(_REMEMBER_KEY, True)
        self._settings.setValue(_USERNAME_KEY, username)
        self._settings.sync()

    def clear(self) -> None:
        self._settings.remove(_USERNAME_KEY)
        self._settings.remove(_REMEMBER_KEY)
        self._settings.sync()
