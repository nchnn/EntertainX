from PySide6.QtCore import QSettings

from auth.preferences import LoginPreferences


def _prefs(tmp_path):
    return LoginPreferences(
        QSettings(str(tmp_path / "prefs.ini"), QSettings.Format.IniFormat)
    )


def test_remembered_username_round_trip(tmp_path):
    prefs = _prefs(tmp_path)
    assert prefs.remembered_username() == ""
    assert not prefs.remember_enabled()

    prefs.set_remembered_username("chris")
    assert prefs.remember_enabled()
    assert prefs.remembered_username() == "chris"

    # A brand new instance reads the same backing store.
    assert _prefs(tmp_path).remembered_username() == "chris"


def test_clear_forgets_username_and_flag(tmp_path):
    prefs = _prefs(tmp_path)
    prefs.set_remembered_username("chris")
    prefs.clear()

    reloaded = _prefs(tmp_path)
    assert reloaded.remembered_username() == ""
    assert not reloaded.remember_enabled()


def test_setting_empty_username_clears(tmp_path):
    prefs = _prefs(tmp_path)
    prefs.set_remembered_username("chris")
    prefs.set_remembered_username("   ")

    assert prefs.remembered_username() == ""
    assert not prefs.remember_enabled()


def test_username_is_trimmed_and_password_never_stored(tmp_path):
    prefs = _prefs(tmp_path)
    prefs.set_remembered_username("  chris  ")
    assert prefs.remembered_username() == "chris"

    settings = QSettings(str(tmp_path / "prefs.ini"), QSettings.Format.IniFormat)
    keys = set(settings.allKeys())
    assert keys == {"auth/remember_enabled", "auth/remembered_username"}
