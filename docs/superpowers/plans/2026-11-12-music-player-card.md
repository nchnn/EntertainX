# Music Player Card Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the Music page's generic media cards with mini-player cards: painted album art, a play disc, and a progress/time row driven by a visual preview animation.

**Architecture:** A new `ui/components/music_card.py` holds three focused units — `AlbumArt` (painted sleeve + vinyl), `PlayerProgress` (3px bar), and `MusicPlayerCard` (card shell + labels + play state). `MusicPage` builds them, keeps search/filter working, and pauses siblings so one preview plays at a time. No audio engine is added.

**Tech Stack:** PySide6 6.12, Python 3, pytest, existing theme tokens and Lucide icons.

**Spec:** `docs/superpowers/specs/2026-11-12-music-player-card-design.md`

## Global Constraints

- Theme tokens only in `ui/`; no colour literals. Lucide icons only, fetched per `AGENTS.MD`.
- Play/pause is a visual preview; no audio, no seeking, no queue.
- `MusicPlayerCard` keeps the `MediaCard` public surface: `title`, `subtitle_label`, `meta_label`, `matches(query)`, `category`.
- Do not change Video, Games, or the auth fan.
- Run tests with `.\venv\Scripts\python.exe -m pytest`.
- Commit only the files listed in each task; the working tree already contains unrelated auth changes.

## Review Focus

1. **900px minimum window:** the grid must drop to two columns and must not clip cards or create a horizontal scrollbar. Test: Task 5 geometry script.
2. **Long album/artist names:** labels must elide, not widen the card. Test: Task 2 long-title test.
3. **Missing or malformed `length`:** fall back to 3:00 and never crash. Test: Task 1 duration helper test.
4. **Filtering out a playing card:** it must pause instead of animating offscreen. Test: Task 4 filter test.
5. **Keyboard/assistive use of the play disc:** focusable, named, and toggles with the keyboard. Test: Task 2 button metadata test.

---

### Task 1: Time helpers and progress bar

**Files:**
- Create: `ui/components/music_card.py`
- Test: `tests/test_music_card.py`

**Interfaces:**
- Produces:
  - `duration_ms(text: str) -> int` — parses `"m:ss"` or `"h:mm:ss"`; returns `180_000` for empty/invalid text.
  - `format_duration(ms: int) -> str` — `"m:ss"`, clamped at zero.
  - `PlayerProgress(QWidget)` with `value() -> float` and `set_value(value: float) -> None` (clamped to 0..1), fixed 4px height.

- [ ] **Step 1: Write the failing tests**

```python
import pytest

from ui.components.music_card import (
    PlayerProgress,
    duration_ms,
    format_duration,
)


def test_duration_parses_minutes_and_hours():
    assert duration_ms("3:42") == 222_000
    assert duration_ms("1:02:03") == 3_723_000


@pytest.mark.parametrize("text", ["", "nope", "3", "3:xx"])
def test_duration_falls_back_for_bad_input(text):
    assert duration_ms(text) == 180_000


def test_format_duration_clamps_and_pads():
    assert format_duration(0) == "0:00"
    assert format_duration(111_000) == "1:51"
    assert format_duration(-500) == "0:00"


def test_progress_value_is_clamped(app):
    bar = PlayerProgress()
    bar.set_value(1.4)
    assert bar.value() == 1.0
    bar.set_value(-0.2)
    assert bar.value() == 0.0
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.\venv\Scripts\python.exe -m pytest tests/test_music_card.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'ui.components.music_card'`.

- [ ] **Step 3: Implement the helpers and progress widget**

Create `ui/components/music_card.py` with `duration_ms`, `format_duration`, and `PlayerProgress`. `PlayerProgress.paintEvent` draws a rounded track with `theme.BORDER` and a rounded fill with `theme.PRIMARY`, both via `QColor(theme...)`; use `Qt.PenStyle.NoPen` and `QPainter.RenderHint.Antialiasing`.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `.\venv\Scripts\python.exe -m pytest tests/test_music_card.py -q`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add ui/components/music_card.py tests/test_music_card.py
git commit -m "feat(music): add player time helpers and progress bar"
```

---

### Task 2: Album art and MusicPlayerCard

**Files:**
- Modify: `ui/components/music_card.py`
- Create: `assets/icons/pause.svg` (Lucide, fetched per `AGENTS.MD`)
- Test: `tests/test_music_card.py`

**Interfaces:**
- Consumes: `duration_ms`, `format_duration`, `PlayerProgress` from Task 1.
- Produces:
  - `AlbumArt(seed: str = "", parent=None)` — paints a pink sleeve with a dark vinyl disc; `disc_side() -> int` returns a deterministic `-1` or `1`.
  - `MusicPlayerCard(title, subtitle, meta="", length="", category="", parent=None)` with:
    - `play_toggled = Signal(bool)`
    - `title -> str`, `matches(query: str) -> bool`, `category: str`
    - `is_playing() -> bool`, `play() -> None`, `pause() -> None`, `toggle() -> None`, `set_playing(playing: bool) -> None`
    - `title_label`, `subtitle_label`, `meta_label` (`ElidedLabel`); `_art`, `_button`, `_progress_bar`, `_elapsed_label`, `_total_label`, `_animation`, `_progress`, `_track_ms`.

- [ ] **Step 1: Fetch the pause icon**

Verify `https://lucide.dev/icons/pause` exists, then download
`https://unpkg.com/lucide-static@latest/icons/pause.svg` to
`assets/icons/pause.svg`. Do not hand-draw it.

- [ ] **Step 2: Write the failing tests**

```python
from PySide6.QtCore import Qt

from theme import theme_manager as theme
from ui.components.music_card import AlbumArt, MusicPlayerCard


def test_album_art_side_is_deterministic(app):
    art = AlbumArt("Soft Static")
    assert art.disc_side() in (-1, 1)
    assert art.disc_side() == AlbumArt("Soft Static").disc_side()


def test_player_card_exposes_text_and_search(app):
    card = MusicPlayerCard("Soft Static", "Mira Vale", "10 tracks", "3:42")
    assert card.title == "Soft Static"
    assert card.subtitle_label.full_text() == "Mira Vale"
    assert card.meta_label.full_text() == "10 tracks"
    assert card.matches("mira")
    assert card.matches("tracks")
    assert not card.matches("zzzz")


def test_player_card_elides_long_text_without_widening(app):
    card = MusicPlayerCard("A very long album title " * 4, "An artist", "10 tracks", "3:42")
    assert card.minimumSizeHint().width() == theme.CARD_MIN_WIDTH


def test_play_toggle_switches_state_and_glyph(app):
    card = MusicPlayerCard("Soft Static", "Mira Vale", "10 tracks", "3:42")
    assert not card.is_playing()
    assert card._button.toolTip() == "Play Soft Static"

    card.toggle()
    assert card.is_playing()
    assert card._button.toolTip() == "Pause Soft Static"

    card.toggle()
    assert not card.is_playing()
    assert card._button.toolTip() == "Play Soft Static"


def test_play_disc_is_keyboard_reachable_and_named(app):
    card = MusicPlayerCard("Soft Static", "Mira Vale", "10 tracks", "3:42")
    assert card._button.focusPolicy() != Qt.FocusPolicy.NoFocus
    assert card._button.accessibleName() == "Play Soft Static"


def test_progress_updates_bar_and_elapsed(app):
    card = MusicPlayerCard("A", "B", "1 track", "3:42")
    card.play()
    card._animation.setCurrentTime(111_000)
    assert card._progress == pytest.approx(0.5, abs=0.02)
    assert card._progress_bar.value() == pytest.approx(0.5, abs=0.02)
    assert card._elapsed_label.text() == "1:51"
    card.pause()


def test_finishing_resets_to_the_start(app):
    card = MusicPlayerCard("A", "B", "1 track", "3:42")
    card.play()
    card._on_finished()
    assert not card.is_playing()
    assert card._elapsed_label.text() == "0:00"
    assert card._progress_bar.value() == 0.0


@pytest.mark.parametrize("length", ["", "nope"])
def test_missing_length_uses_three_minutes(app, length):
    card = MusicPlayerCard("A", "B", "1 track", length)
    assert card._track_ms == 180_000
    assert card._total_label.text() == "3:00"
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `.\venv\Scripts\python.exe -m pytest tests/test_music_card.py -q`
Expected: FAIL with `ImportError: cannot import name 'AlbumArt'`.

- [ ] **Step 4: Implement `AlbumArt`**

Paint with theme tokens: sleeve gradient `SECONDARY` → `ACCENT_PRESSED`; vinyl disc `TEXT_ON_ACCENT`; grooves `SECONDARY` at low alpha; label `PRIMARY`; centre hole `TEXT_ON_ACCENT`. Clip to a rounded rect (`theme.RADIUS_MD`). `disc_side()` uses a deterministic character-sum seed (`sum(ord(c) for c in seed) % 2`), never Python's salted `hash()`.

- [ ] **Step 5: Implement `MusicPlayerCard`**

Build the card with `role="mediaCard"`, `setMinimumWidth(theme.CARD_MIN_WIDTH)`, and `QSizePolicy(Preferred, Fixed)`. Set the three text labels' horizontal policy to `Ignored` so they elide. Add the art at the top with a `QGridLayout` overlay holding the 38×38 play button (`variant="playDisc"`, bottom-right, 12px inset). Add the text box (12px margins, 4px spacing) with title, artist, meta, progress bar, and a time row (`_elapsed_label` left, `_total_label` right, both `role="caption"`). In `resizeEvent`, set the art height to `max(170, min(self.contentsRect().width(), 280))`. The play button toggles a `QVariantAnimation` over `_track_ms`; `_on_progress` updates the bar and elapsed label; `_on_finished` resets to zero; `play()`/`pause()` emit `play_toggled`.

- [ ] **Step 6: Run the tests to verify they pass**

Run: `.\venv\Scripts\python.exe -m pytest tests/test_music_card.py -q`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add ui/components/music_card.py assets/icons/pause.svg tests/test_music_card.py
git commit -m "feat(music): add painted album art and player card"
```

---

### Task 3: Play disc styling and sample lengths

**Files:**
- Modify: `theme/theme_manager.py`
- Modify: `ui/pages/sample_data.py`
- Test: `tests/test_theme.py`, `tests/test_music_card.py`

**Interfaces:**
- Produces: `QPushButton[variant="playDisc"]` QSS; every `ALBUMS` entry gains `"length": "m:ss"`.

- [ ] **Step 1: Write the failing tests**

In `tests/test_theme.py`, add the selector to the existing loop:

```python
'QPushButton[variant="playDisc"]',
```

In `tests/test_music_card.py`, add:

```python
import re

from ui.pages.sample_data import ALBUMS


def test_every_album_has_a_valid_length():
    assert all(re.fullmatch(r"\d+:\d{2}", album["length"]) for album in ALBUMS)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.\venv\Scripts\python.exe -m pytest tests/test_theme.py tests/test_music_card.py -q`
Expected: FAIL on the missing selector and missing `length` key.

- [ ] **Step 3: Add the QSS role**

Add to `build_stylesheet()`:

```css
QPushButton[variant="playDisc"] {
    background-color: %(accent)s;
    border: 1px solid %(accent_pressed)s;
    border-radius: 19px;
    padding: 0px;
}
QPushButton[variant="playDisc"]:hover {
    background-color: %(accent_hover)s;
    border-color: %(accent_hover)s;
}
QPushButton[variant="playDisc"]:pressed {
    background-color: %(accent_pressed)s;
}
QPushButton[variant="playDisc"]:focus {
    border: 2px solid %(on_accent)s;
}
```

- [ ] **Step 4: Add album lengths**

Use `3:42`, `4:05`, `2:58`, `3:21`, `4:12`, `3:36` for the six albums, in order.

- [ ] **Step 5: Run the tests to verify they pass**

Run: `.\venv\Scripts\python.exe -m pytest tests/test_theme.py tests/test_music_card.py -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add theme/theme_manager.py ui/pages/sample_data.py tests/test_theme.py tests/test_music_card.py
git commit -m "feat(music): style the play disc and add album lengths"
```

---

### Task 4: Music page wiring

**Files:**
- Modify: `ui/pages/music.py`
- Test: `tests/test_music_card.py`

**Interfaces:**
- Consumes: `MusicPlayerCard` from Task 2, `ALBUMS` lengths from Task 3.
- Produces: `MusicPage` whose `grid.cards` are `MusicPlayerCard`s; `MusicPage._pause_others(active)` pauses every other playing card; `MusicPage.apply_filter()` pauses cards it hides.

- [ ] **Step 1: Write the failing tests**

```python
from ui.pages.music import MusicPage


def test_music_page_uses_player_cards(app):
    page = MusicPage()
    assert len(page.grid.cards) == len(ALBUMS)
    assert all(isinstance(card, MusicPlayerCard) for card in page.grid.cards)
    assert page.grid.cards[0].title == ALBUMS[0]["title"]


def test_starting_one_card_pauses_the_others(app):
    page = MusicPage()
    first, second = page.grid.cards[0], page.grid.cards[1]
    first.toggle()
    assert first.is_playing()

    second.toggle()
    assert second.is_playing()
    assert not first.is_playing()


def test_filtering_out_a_playing_card_pauses_it(app):
    page = MusicPage()
    page.grid.cards[0].toggle()
    page.search.setText("Pink Hours")
    assert not page.grid.cards[0].is_playing()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.\venv\Scripts\python.exe -m pytest tests/test_music_card.py -q`
Expected: FAIL because the page still builds `MediaCard`s.

- [ ] **Step 3: Implement the page wiring**

Replace the `MediaCard` construction with `MusicPlayerCard(album["title"], album["artist"], album["tracks"], album["length"], category=album["artist"])`. After `super().__init__`, connect each card's `play_toggled` to a lambda that calls `self._pause_others(card)` when `playing` is true. Add `_pause_others(active)` and override `apply_filter()` to call `super().apply_filter()` then pause any hidden playing card.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `.\venv\Scripts\python.exe -m pytest tests/test_music_card.py tests/test_pages.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add ui/pages/music.py tests/test_music_card.py
git commit -m "feat(music): use player cards on the music page"
```

---

### Task 5: Responsive verification and screenshots

**Files:**
- Generated locally: `.impeccable/review/music-900.png`, `music-1200.png`, `music-1440.png` (this folder is git-ignored; do not commit them)
- Test: full suite

**Interfaces:**
- Consumes: everything above.

- [ ] **Step 1: Write and run a geometry check**

Create a temporary script (outside the repo) that builds `MusicPage` inside `FramelessWindow`, then for each size `(900, 620)`, `(1200, 820)`, `(1440, 900)`:
- asserts the page's `QScrollArea` horizontal scrollbar is not visible;
- prints `grid._columns`, each card's width, and each `_art` height;
- asserts every art height is `max(170, min(card_width - 2, 280))`;
- asserts no visible `QLabel` is shorter than its font metrics;
- saves a screenshot to `.impeccable/review/music-<width>.png`.

Run: `.\venv\Scripts\python.exe <temp-script>.py`
Expected: 2 / 3 / 4+ columns, no horizontal scroll, no clipped labels.

- [ ] **Step 2: Fix only real geometry failures**

If the art height, column count, or clipping is wrong, adjust the art cap or card margins in `ui/components/music_card.py`; do not change the grid.

- [ ] **Step 3: Run the full suite**

Run: `.\venv\Scripts\python.exe -m pytest -q`
Expected: all tests pass (131 + new).

- [ ] **Step 4: Report the results**

State the column counts, art heights, and screenshot paths in the handoff. No commit: the screenshots are ignored runtime state and this task changes no tracked file.

---

## Self-Review

- **Spec coverage:** card anatomy (Tasks 1-2), art and play disc (Task 2), theme/sample data (Task 3), page wiring and one-at-a-time (Task 4), responsive check (Task 5). Every design goal has a task.
- **Step scan:** each step names the file, the exact interface, and the assertion; no "handle edge cases" placeholders.
- **Type consistency:** `MusicPlayerCard` is constructed with positional `(title, subtitle, meta, length, category=...)` in both the tests and `MusicPage`; `play_toggled(bool)` is used by the page lambda.
- **Review focus:** all five lines map to tests in Tasks 2, 4, and 5.
- **Proportion:** the plan is shorter than the spec plus code; bodies appear only for the painted art and the animation, where the tests do not determine the drawing.
