import os
import sys

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="session")
def app():
    from theme.theme_manager import apply_theme

    instance = QApplication.instance() or QApplication(sys.argv)
    apply_theme(instance)
    return instance


@pytest.fixture()
def auth_env(tmp_path):
    """In-memory auth manager plus an INI-backed preference store."""
    import sqlite3

    from PySide6.QtCore import QSettings

    from auth.auth_manager import AuthManager
    from auth.preferences import LoginPreferences
    from database.db import init_db

    conn = sqlite3.connect(":memory:")
    init_db(conn)
    prefs = LoginPreferences(
        QSettings(str(tmp_path / "prefs.ini"), QSettings.Format.IniFormat)
    )
    yield AuthManager(conn), prefs
    conn.close()
