# EntertainX Grey/Pink Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild EntertainX's visual layer as a frameless, grey-dominant desktop app with pink accents, real page shells, and a centralized theme.

**Architecture:** `theme_manager.py` generates the full QSS from tokens; widgets opt into looks through dynamic properties (`variant`, `role`). A reusable `FramelessWindow` in `ui/frameless.py` owns the custom title bar and native window behaviour, and `main.py` swaps only the body between auth and main views.

**Tech Stack:** Python 3, PySide6 6.12, sqlite3, pytest, QSettings.

**Spec:** `docs/superpowers/specs/2026-11-12-entertainx-grey-pink-redesign-design.md`

## Global Constraints

- Palette: `BG #242326`, `SIDEBAR #303034`, `CARD #3B393F`, `ELEVATED #454249`, `BORDER #504C53`, `ACCENT #E8AAB9`, `ACCENT_HOVER #F2C6D0`, `TEXT #F4F1F2`, `TEXT_MUTED #B8B2B5`.
- No colour literals outside `theme/theme_manager.py` (icons may derive from tokens).
- No new dependencies; no binary assets.
- SQLite schema unchanged; `AuthManager` public API unchanged.
- Tests must stay green: `python -m pytest -q`.

## Review Focus

- Shrinking the window below the register card's height must keep it usable (scroll, not clip).
- Toggling password visibility must preserve typed text and the caret.
- Registration success must still be visible after the switch to Login.
- Remember Me unchecked + restart must not restore a stale username.
- Maximized window must not resize from edges, and restore must return to the previous size.

---

### Task 1: Theme tokens and QSS generator

**Files:** Modify `theme/theme_manager.py`; Test `tests/test_theme.py` (create).

**Interfaces:**
- Produces: tokens `BG`, `BG_SIDEBAR`, `BG_CARD`, `BG_ELEVATED`, `BORDER`, `PRIMARY`, `ACCENT_HOVER`, `ACCENT_PRESSED`, `ACCENT_SOFT`, `TEXT_PRIMARY`, `TEXT_MUTED`, `DANGER`, `SUCCESS`, `RADIUS_*`, `SPACE_*`, `FONT_*`; `build_stylesheet(accent=None, accent_hover=None, mode="dark") -> str`; `apply_theme(app, **overrides) -> None`; `restyle(widget) -> None`; `QSS`; `SECONDARY`.
- Keeps: `BG_DARK` alias, `TEXT_SECONDARY` alias, `apply_theme(app)` signature.

- [ ] Test `build_stylesheet()` contains every token colour and the `QPushButton[variant="primary"]` selector.
- [ ] Test `apply_theme` sets a non-empty `app.styleSheet()`.
- [ ] Run `pytest tests/test_theme.py -q` → pass.

### Task 2: Painted icon set

**Files:** Create `ui/components/__init__.py`, `ui/components/icons.py`; Test `tests/test_icons.py`.

**Interfaces:** `make_icon(name: str, color: str, size: int = 18, active_color: str | None = None) -> QIcon` for names `user`, `lock`, `eye`, `eye-off`, `search`, `play`, `star`, `plus`, `chevron`; `brand_pixmap(size: int) -> QPixmap`; `app_icon() -> QIcon`.

- [ ] Test each name returns a non-null `QIcon`; unknown name raises `KeyError`.
- [ ] Test `app_icon()` pixmap is non-null at 16/32/64.

### Task 3: Auth field widgets

**Files:** Create `ui/components/fields.py`; Test `tests/test_fields.py`.

**Interfaces:** `IconLineEdit(icon_name: str, placeholder: str)`; `PasswordLineEdit(label=None)` with `toggle_action`, `echoMode()` toggling between `Password` and `Normal`, text preserved; `FormField(label, widget)` with `set_error(msg)`, `clear_error()`, `has_error`.

- [ ] Test password text survives two toggles.
- [ ] Test `FormField.set_error` sets the input property `error=True` and shows the message; `clear_error` reverses it.

### Task 4: Surfaces and banners

**Files:** Create `ui/components/surfaces.py`; Test `tests/test_surfaces.py`.

**Interfaces:** `Card(variant="card")`, `PageHeader(title, subtitle="", actions=None)`, `EmptyState(icon, title, body, hint=None)`, `Badge(text, tone="accent")`, `InlineBanner(tone="error"|"success"|"info")` with `show_message(text)` / `clear()`, `SectionLabel(text)`.

- [ ] Test `InlineBanner.show_message` makes it visible and stores text; `clear()` hides it.
- [ ] Test `PageHeader` exposes `title` text.

### Task 5: Media cards and grid

**Files:** Create `ui/components/media_card.py`; Test `tests/test_media_card.py`.

**Interfaces:** `MediaCard(icon, title, subtitle, meta=None, footer=None)`; `CardGrid(cards, min_width=210)` with `add_card`, `clear`.

- [ ] Test `MediaCard` renders title/subtitle and exposes them as attributes.
- [ ] Test `CardGrid` reflows without error at width 300 and 1200.

### Task 6: Frameless window and title bar

**Files:** Create `ui/frameless.py`; Test `tests/test_frameless.py`.

**Interfaces:** `TitleBar(parent=None)` signals `minimize_requested`, `maximize_requested`, `close_requested`; `set_maximized(bool)`; `FramelessWindow(QMainWindow)` with `set_content(widget)`, `content`, `toggle_maximize()`, `is_maximized()`.

- [ ] Test `set_content` replaces and reparents the body widget.
- [ ] Test `toggle_maximize` flips `is_maximized()` (offscreen-safe).

### Task 7: Theme application + login/register redesign

**Files:** Modify `ui/login_window.py`; Modify `auth/preferences.py` (create); Modify `auth/auth_manager.py`; Test `tests/test_preferences.py`, `tests/test_login_window.py`.

**Interfaces:**
- `LoginPreferences(settings: QSettings | None = None)` with `remembered_username()`, `set_remembered_username(name)`, `remember_enabled()`.
- `AuthManager.register` validates username/email/password per GOAL and inserts a `user_settings` row; `login` returns `"Invalid username or password"`.

- [ ] Test remember/forget round-trip with an INI temp file.
- [ ] Test registration success banner survives switching to Login (widget test).
- [ ] Test Remember Me prefill on construction and clearing on uncheck.
- [ ] Test validation: short username, bad email, short password, mismatch confirm, double submit guard.

### Task 8: Sidebar, content area, main window

**Files:** Modify `ui/sidebar.py`, `ui/content_area.py`, `ui/main_window.py`; Test extension in `tests/test_navigation.py`.

- [ ] Test sidebar active state uses `isChecked()` and still calls the category callback.
- [ ] Test logout from sidebar reaches the callback.
- [ ] Test content area still restores the last subtab (existing test).

### Task 9: Real page shells

**Files:** Create `ui/pages/sample_data.py`; Modify all `ui/pages/*.py`; Test `tests/test_pages.py`.

- [ ] Test every page instantiates and exposes a `PageHeader` title.
- [ ] Test search field filters visible cards on the movie page (`_visible_titles`).
- [ ] Test My Lists shows an `EmptyState`.

### Task 10: Entry point, settings page, verification

**Files:** Modify `main.py`, `ui/pages/settings.py`, `GOAL.MD` (phase/checklist notes only if required).

- [ ] Run `python -m pytest -q` → all pass.
- [ ] Run `QT_QPA_PLATFORM=offscreen python -c "..."` smoke script: build `FramelessWindow`, swap login → main → login.
- [ ] Manually visual-check on Windows desktop.
