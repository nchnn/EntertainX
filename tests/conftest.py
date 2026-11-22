import os
import sys
import time

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
# Animations are exercised in tests/test_motion.py; everywhere else they would
# only slow the suite down, so the helpers apply their end state immediately.
os.environ.setdefault("ENTERTAINX_REDUCE_MOTION", "1")

from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="session")
def app():
    from theme.theme_manager import apply_theme

    instance = QApplication.instance() or QApplication(sys.argv)
    apply_theme(instance)
    return instance


@pytest.fixture()
def wait_for(app):
    """Pump the event loop until ``condition()`` holds.

    Sign-in and registration hash their password on a worker thread and report
    back through a queued signal, so tests wait for the result instead of
    reading it straight after the click.
    """

    def wait(condition, timeout: float = 10.0) -> bool:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            app.processEvents()
            if condition():
                return True
            time.sleep(0.005)
        return bool(condition())

    return wait


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
