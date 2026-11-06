# Phase 2: Main Navigation Structure — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the main application shell — sidebar category nav, sub-page tab bar, and placeholder content pages — that all future API phases plug into.

**Architecture:** `MainWindow` replaces the placeholder after login. Left sidebar holds category buttons (Video, Music, Games, My Lists, Settings). Selecting a category updates a sub-nav tab bar at the top of the content area. Selecting a sub-tab swaps a `QStackedWidget` to the matching placeholder page. No API calls in this phase — every content page is a styled placeholder. Theme is a single dark QSS applied globally; colors use named CSS variables pattern via QSS so Phase 7 (theming) can swap them in one place.

**Tech Stack:** Python 3.12, PySide6 6.12.0 (QMainWindow, QWidget, QStackedWidget, QFrame, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QSizePolicy), QSS for styling.

**Spec:** `EntertainX_GOAL_REVISED.md` sections 6.7, 10; `GOAL.MD` sections 2, 8

## Global Constraints

- Python 3.12, venv (`venv/Scripts/activate`)
- PySide6 only — no extra dependencies
- All nav state kept in `MainWindow`; child pages are dumb widgets
- Sidebar always visible after login; never hidden or collapsed in this phase
- Session + user dict passed from Phase 1 `AuthManager` — `MainWindow` receives `user: dict` and `auth_manager: AuthManager`
- Logout clears session and returns to `LoginWindow` (same as Phase 1 wiring)
- No API calls — placeholder pages only
- QSS defined in `theme/theme_manager.py`; applied once at app level via `QApplication.setStyleSheet()`
- Colors defined as Python constants in `theme/theme_manager.py` so Phase 7 can replace them

## Navigation Structure

```
Sidebar category    Sub-tabs (top of content area)
──────────────────  ──────────────────────────────
Video               YouTube | Movies | TV Shows
Music               (no sub-tabs — single page)
Games               Chess | Fireboy & Watergirl | Browse Games
My Lists            (no sub-tabs — single page)
Settings            (no sub-tabs — single page)
```

## File Structure

- Create: `ui/main_window.py` — `MainWindow(QMainWindow)`: top-level shell, sidebar, content area
- Create: `ui/sidebar.py` — `Sidebar(QWidget)`: category buttons, emits `category_changed(str)` signal
- Create: `ui/content_area.py` — `ContentArea(QWidget)`: sub-tab bar + `QStackedWidget` of pages
- Create: `ui/pages/__init__.py` — empty
- Create: `ui/pages/placeholder.py` — `PlaceholderPage(QWidget)`: reusable "coming soon" page with icon + label
- Create: `ui/pages/video_youtube.py` — placeholder
- Create: `ui/pages/video_movies.py` — placeholder
- Create: `ui/pages/video_tvshows.py` — placeholder
- Create: `ui/pages/music.py` — placeholder
- Create: `ui/pages/games_chess.py` — placeholder
- Create: `ui/pages/games_fireboy.py` — placeholder
- Create: `ui/pages/games_browse.py` — placeholder
- Create: `ui/pages/my_lists.py` — placeholder
- Create: `ui/pages/settings.py` — placeholder
- Create: `theme/__init__.py` — empty
- Create: `theme/theme_manager.py` — QSS string + `apply_theme(app)` function
- Modify: `main.py` — swap placeholder post-login widget with `MainWindow`
- Create: `tests/test_navigation.py` — headless nav state tests

## Review Focus

1. **Category switch resets sub-tab to index 0** — switching Video → Music → Video must restore the last Video sub-tab, not reset it; store last active sub-tab per category
2. **Logout from main window** — Settings page has a Logout button; must call `auth_manager.logout()` and return to `LoginWindow` without crashing
3. **Sidebar active state** — clicking a category must visually mark it active and unmark the previous one; no two categories active at once
4. **Window resize** — sidebar fixed width, content area expands to fill remaining space; test at 800×600 and 1920×1080
5. **User name in sidebar** — sidebar shows logged-in username; must update correctly if a future phase re-authenticates

---

### Task 1: Theme Manager

**Files:**
- Create: `theme/__init__.py`
- Create: `theme/theme_manager.py`

**Interfaces:**
- Consumes: nothing
- Produces:
  - `PRIMARY = "#6C63FF"`
  - `SECONDARY = "#FF6584"`
  - `BG_DARK = "#1a1a2e"`
  - `BG_SIDEBAR = "#16213e"`
  - `BG_CARD = "#0f3460"`
  - `TEXT_PRIMARY = "#e0e0e0"`
  - `TEXT_MUTED = "#a0a0b0"`
  - `apply_theme(app: QApplication) -> None` — calls `app.setStyleSheet(QSS)` with the dark theme string

- [ ] **Step 1: Create `theme/__init__.py`** — empty file

- [ ] **Step 2: Implement `theme/theme_manager.py`**

Define color constants (above). Build `QSS: str` covering:
- `QMainWindow`, `QWidget` background → `BG_DARK`
- `QLabel` color → `TEXT_PRIMARY`
- `QPushButton` — rounded, `PRIMARY` background, white text, hover darkens by ~10%
- `QLineEdit` — dark background, light text, `PRIMARY` border on focus
- `QScrollBar` — thin, dark, minimal

`apply_theme(app)` calls `app.setStyleSheet(QSS)`.

- [ ] **Step 3: Wire into `main.py`**

After `QApplication` created, call `apply_theme(app)` before showing any window.

- [ ] **Step 4: Run app to verify dark theme applies to login screen**

Run: `python main.py`
Expected: login window appears with dark background, styled inputs and button

- [ ] **Step 5: Commit**

```bash
git add theme/ main.py
git commit -m "feat: dark theme manager with QSS"
```

---

### Task 2: Placeholder Page Component

**Files:**
- Create: `ui/pages/__init__.py`
- Create: `ui/pages/placeholder.py`

**Interfaces:**
- Consumes: nothing
- Produces:
  - `PlaceholderPage(icon: str, label: str) -> QWidget` — centered emoji icon (large `QLabel`) + section name label below it + "Coming soon" subtitle

- [ ] **Step 1: Implement `ui/pages/placeholder.py`**

`PlaceholderPage(QWidget)`:
- `__init__(self, icon: str, label: str)`
- Centered `QVBoxLayout` with `Qt.AlignCenter`
- `QLabel(icon)` at ~48pt font
- `QLabel(label)` at ~20pt font, `TEXT_PRIMARY`
- `QLabel("Coming soon")` at ~12pt, `TEXT_MUTED`

- [ ] **Step 2: Visual check**

Instantiate in a throwaway script and verify it renders correctly. No formal test needed.

- [ ] **Step 3: Commit**

```bash
git add ui/pages/
git commit -m "feat: PlaceholderPage reusable component"
```

---

### Task 3: Individual Placeholder Pages

**Files:**
- Create: `ui/pages/video_youtube.py`
- Create: `ui/pages/video_movies.py`
- Create: `ui/pages/video_tvshows.py`
- Create: `ui/pages/music.py`
- Create: `ui/pages/games_chess.py`
- Create: `ui/pages/games_fireboy.py`
- Create: `ui/pages/games_browse.py`
- Create: `ui/pages/my_lists.py`
- Create: `ui/pages/settings.py`

**Interfaces:**
- Consumes: `ui.pages.placeholder.PlaceholderPage`
- Produces: one `QWidget` subclass per file, each wrapping `PlaceholderPage` with appropriate icon + label

| File | Class | Icon | Label |
|------|-------|------|-------|
| `video_youtube.py` | `YouTubePage` | `▶` | `YouTube` |
| `video_movies.py` | `MoviesPage` | `🎬` | `Movies` |
| `video_tvshows.py` | `TVShowsPage` | `📺` | `TV Shows` |
| `music.py` | `MusicPage` | `🎵` | `Music` |
| `games_chess.py` | `ChessPage` | `♟` | `Chess` |
| `games_fireboy.py` | `FireboyPage` | `🔥` | `Fireboy & Watergirl` |
| `games_browse.py` | `BrowseGamesPage` | `🎮` | `Browse Games` |
| `my_lists.py` | `MyListsPage` | `☰` | `My Lists` |
| `settings.py` | `SettingsPage` | `⚙` | `Settings` |

`SettingsPage` also adds a Logout button at bottom; it receives `on_logout: Callable` in `__init__` and connects it.

- [ ] **Step 1: Create all 9 page files** per table above

- [ ] **Step 2: Commit**

```bash
git add ui/pages/
git commit -m "feat: placeholder pages for all nav sections"
```

---

### Task 4: Sidebar

**Files:**
- Create: `ui/sidebar.py`

**Interfaces:**
- Consumes: nothing from project
- Produces:
  - `Sidebar(username: str, on_category: Callable[[str], None]) -> QWidget`
  - Fixed width: 220px
  - Categories (in order): `"Video"`, `"Music"`, `"Games"`, `"My Lists"`, `"Settings"`
  - Calls `on_category(category_name)` when a button is clicked
  - Active button visually distinct (different background, left accent bar)
  - Username shown at top of sidebar
  - App name "EntertainX" shown above username
  - First category (`"Video"`) active by default

- [ ] **Step 1: Write nav state test**

```python
# tests/test_navigation.py
from ui.sidebar import Sidebar
# headless — no QApplication needed for logic tests

def test_sidebar_default_active():
    # Sidebar tracks which category is active
    activated = []
    import sys
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication(sys.argv)
    sb = Sidebar("testuser", lambda c: activated.append(c))
    assert sb.active_category() == "Video"

def test_sidebar_category_change():
    activated = []
    import sys
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication(sys.argv)
    sb = Sidebar("testuser", lambda c: activated.append(c))
    sb.set_active("Music")
    assert sb.active_category() == "Music"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_navigation.py -v`
Expected: FAIL — `ui.sidebar` not found

- [ ] **Step 3: Implement `ui/sidebar.py`**

`Sidebar(QWidget)`:
- `__init__(self, username: str, on_category: Callable[[str], None])`
- Fixed width via `self.setFixedWidth(220)`
- `QVBoxLayout`, no margins on outer, 0 spacing between buttons
- Top section: app name label + username label
- Category buttons: `QPushButton` per category, `checkable=False`, custom QSS for active state
- `_active: str` tracks current category
- `active_category() -> str`
- `set_active(name: str)` — updates `_active`, refreshes button styles, calls `on_category(name)`
- Each button `clicked` → `self.set_active(name)`
- Bottom: stretch to push everything up

Active button QSS: left border 3px `PRIMARY`, background slightly lighter than sidebar bg.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_navigation.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add ui/sidebar.py tests/test_navigation.py
git commit -m "feat: sidebar with active category tracking"
```

---

### Task 5: Content Area

**Files:**
- Create: `ui/content_area.py`

**Interfaces:**
- Consumes: all page classes from `ui/pages/`
- Produces:
  - `ContentArea(on_logout: Callable) -> QWidget`
  - `ContentArea.show_category(name: str) -> None` — switches sub-tab bar and stacked page to the given category; restores last active sub-tab per category
  - Sub-tab bar: `QPushButton` row at top, only shown when category has multiple sub-tabs; hidden for Music, My Lists, Settings
  - `QStackedWidget` fills remaining space

Category → sub-tabs → page class mapping:

```python
CATEGORIES = {
    "Video": [
        ("YouTube",   YouTubePage),
        ("Movies",    MoviesPage),
        ("TV Shows",  TVShowsPage),
    ],
    "Music": [
        ("Music",     MusicPage),
    ],
    "Games": [
        ("Chess",           ChessPage),
        ("Fireboy & Watergirl", FireboyPage),
        ("Browse Games",    BrowseGamesPage),
    ],
    "My Lists": [
        ("My Lists",  MyListsPage),
    ],
    "Settings": [
        ("Settings",  SettingsPage),   # passes on_logout through
    ],
}
```

- [ ] **Step 1: Implement `ui/content_area.py`**

`ContentArea(QWidget)`:
- `__init__(self, on_logout: Callable)`
- Build all page instances once, store in dict keyed by `(category, label)`
- `QStackedWidget` holds all pages (added once at init)
- Sub-tab bar: `QHBoxLayout` of `QPushButton`s; hidden via `setVisible(False)` when only one tab
- `_last_tab: dict[str, int]` — tracks last active sub-tab index per category, defaults to 0
- `show_category(name)` — updates sub-tab bar buttons, restores `_last_tab[name]`, swaps stacked widget
- Active sub-tab button: bold text, `PRIMARY` underline or background

- [ ] **Step 2: Commit**

```bash
git add ui/content_area.py
git commit -m "feat: content area with sub-tab bar and stacked pages"
```

---

### Task 6: Main Window + Wiring

**Files:**
- Create: `ui/main_window.py`
- Modify: `main.py`

**Interfaces:**
- Consumes: `Sidebar`, `ContentArea`, `AuthManager`, `user: dict`
- Produces:
  - `MainWindow(auth_manager: AuthManager, user: dict) -> QMainWindow`
  - Horizontal split: `Sidebar` (left, fixed 220px) + `ContentArea` (right, expanding)
  - Logout flow: `auth_manager.logout()` → emit signal or call callback → `main.py` swaps back to `LoginWindow`

- [ ] **Step 1: Implement `ui/main_window.py`**

`MainWindow(QMainWindow)`:
- `__init__(self, auth_manager, user, on_logout: Callable)`
- Central widget: `QWidget` with `QHBoxLayout`, no spacing, no margins
- Left: `Sidebar(username=user["username"], on_category=self._on_category)`
- Right: `ContentArea(on_logout=self._do_logout)`
- Separator: 1px `QFrame(QFrame.VLine)` between sidebar and content
- `_on_category(name)` → calls `content_area.show_category(name)`
- `_do_logout()` → `auth_manager.logout()` → `on_logout()`
- Default category on show: `"Video"`

- [ ] **Step 2: Modify `main.py`**

Replace `_on_login_success` placeholder with:
```python
def _on_login_success(self, user: dict) -> None:
    main_win = MainWindow(self._auth, user, on_logout=self._show_login)
    self.setCentralWidget(main_win)
```

- [ ] **Step 3: Manual integration test**

Run: `python main.py`
1. Login → MainWindow appears with dark sidebar and content area
2. Click each sidebar category → content area updates, sub-tab bar shows/hides correctly
3. Click sub-tabs within Video and Games → page swaps
4. Switch category away and back → last sub-tab restored
5. Settings → click Logout → returns to login screen
6. Resize window → sidebar stays fixed, content expands

- [ ] **Step 4: Commit**

```bash
git add ui/main_window.py main.py
git commit -m "feat: main window shell with sidebar and content area wired"
```

---

### Task 7: Full Test Suite Pass

**Files:**
- Modify: `tests/test_navigation.py` — add sub-tab restore test

**Interfaces:**
- Consumes: `ContentArea`

- [ ] **Step 1: Add sub-tab restore test**

```python
def test_content_area_restores_last_subtab():
    import sys
    from PySide6.QtWidgets import QApplication
    from ui.content_area import ContentArea
    app = QApplication.instance() or QApplication(sys.argv)
    ca = ContentArea(on_logout=lambda: None)
    ca.show_category("Video")
    ca._switch_subtab(2)  # switch to TV Shows (index 2)
    ca.show_category("Music")
    ca.show_category("Video")
    assert ca._last_tab["Video"] == 2
```

- [ ] **Step 2: Run full test suite**

Run: `python -m pytest tests/ -v`
Expected: all 17+ tests PASS

- [ ] **Step 3: Final commit**

```bash
git add .
git commit -m "feat: phase 2 complete — main navigation shell"
```
