# EntertainX — Grey/Pink Redesign and Frameless Shell (Design)

Date: 2026-11-12
Status: approved in conversation (project owner), implemented in the same session.

## Intent

Phase 2 of EntertainX ships a working navigation shell whose look is navy/purple,
whose chrome is a stock Windows title bar, and whose auth screens are unstyled
stacked inputs. The owner wants the application to read as a modern, minimal,
grey-dominant desktop entertainment app with light-pink accents, and asked for
real content shells in every section so the polish is visible end to end.

## Goals

1. One frameless window (custom title bar) for both auth and main views, with
   minimize / maximize-restore / close, drag, and edge resize on Windows.
2. Grey palette (`#242326` base, `#303034` sidebar, `#3B393F` card,
   `#454249` elevated, `#504C53` border) with `#E8AAB9` accent.
3. Redesigned login and registration cards: icons in fields, show/hide
   password, Remember Me (username only), field-level validation feedback,
   non-clearing success banner, double-submit guard.
4. `theme/theme_manager.py` becomes the single source of truth: tokens,
   typography, radii, spacing, and QSS for every component variant. No colour
   literals in UI modules.
5. Every section gets a real content shell (header, search, card grid, empty
   state) using static sample data until Phases 3-7 wire the APIs.
6. Existing auth/DB/logout/navigation behaviour and all 18 tests keep passing.

## Non-goals

- No live APIs, playback, game engines, or list persistence (Phases 3-7).
- No settings UI for accent colours or light mode (Phase 8). The theme module is
  built to support it, but the Settings page only previews the palette.
- No changes to the SQLite schema.
- No new third-party dependencies, no binary assets.

## Anti-goals

- Auth screens that look good but lose Remember Me, success feedback, or field
  error highlighting.
- A frameless window that cannot be moved, resized, maximized, or closed
  normally, or that breaks logout/login swapping.
- Colour literals leaking back into `ui/`.

## Constraints

- PySide6 6.12, Python 3, Windows desktop.
- `users` / `user_settings` schema unchanged. `auth_manager.AuthManager`
  public API (`register`, `login`, `logout`, `is_logged_in`, `current_user`)
  unchanged.
- UI icons are Lucide SVGs stored in `assets/icons/` (per `AGENTS.MD`) and
  tinted at render time by `ui/components/icons.py`; no colour is baked into
  an asset. The EntertainX mark itself is painted in code.
- `GOAL.md` validation rules apply: username 3-20 alphanumeric, email with `@`
  and a dot in the domain, password min 6, generic login failure message.

## Approaches considered

1. **Keep the stock frame, restyle inside.** Cheapest, but fails the explicit
   borderless requirement.
2. **Frameless via manual hit-testing + `startSystemResize`.** Portable, but
   misses Windows aero snap and can fight child widgets for edge events.
3. **Frameless with `WM_NCHITTEST` handled in `nativeEvent` (chosen).** Native
   resize cursors, corners, and snap keep working; title bar drag uses
   `startSystemMove`, which is smooth and snap-aware. Falls back to
   `startSystemResize` hit-testing on non-Windows.

Theme approach: module-level tokens plus `build_stylesheet()` generator and
semantic widget variants (`primary`, `ghost`, `nav`, `tab`, `window`) applied
through Qt dynamic properties, so the whole UI restyles from one call and
Phase 8 can regenerate QSS with per-user accents.

Page approach: shared components (`PageHeader`, `CardGrid`, `MediaCard`,
`EmptyState`) over `ui/pages/sample_data.py`, so wiring an API later replaces
data, not layout.

## What the owner decided

- Grey + light pink identity, palette as listed above.
- Real page content, not restyled "Coming soon" placeholders.
- Redesign and edit `theme/theme_manager.py` as the central theme.
- Auth window and main window share the borderless treatment.

## Decisions made by the builder

- One OS window; `main.py` swaps the content below the shared title bar.
  Login and main views therefore cannot drift apart.
- `MainWindow` becomes a plain `QWidget` so it can sit inside the frameless
  window without nesting `QMainWindow`s.
- Remember Me stores only the username in `QSettings("EntertainX", "EntertainX")`.
  Passwords are never stored; no auto-login.
- Registration success switches to Login and leaves a green banner above the
  form; it also prefills the username.
- Registration writes default `user_settings` colours (via the theme tokens) so
  Phase 8 finds a row per user. Schema untouched.
- Sample content is labelled in code as static, and game pages that need real
  engines use designed "in development" panels with disabled actions rather
  than dead buttons.
- Window minimum size 900x620 so the register card never becomes unusable.

## Parts

- `theme/theme_manager.py` — tokens, `build_stylesheet()`, `apply_theme()`,
  `restyle()`.
- `ui/frameless.py` — `TitleBar`, `FramelessWindow`, `BrandMark`.
- `ui/components/` - Lucide-backed icons, field widgets (`IconLineEdit`,
  `PasswordLineEdit`, `FormField`), surfaces (`Card`, `PageHeader`,
  `EmptyState`, `Badge`, `InlineBanner`), `MediaCard`/`CardGrid`.
- `ui/login_window.py` — auth cards + Remember Me + validation UX.
- `ui/sidebar.py`, `ui/content_area.py`, `ui/main_window.py` — restyle and
  rewire.
- `ui/pages/*` — real shells for YouTube, Movies, TV Shows, Music, Chess,
  Fireboy & Watergirl, Browse Games, My Lists, Settings.
- `auth/auth_manager.py` — validation, generic login error, settings row.
- `auth/preferences.py` — `LoginPreferences` over `QSettings`.
- `tests/` — theme, preferences, validation, and widget smoke tests.

## Left to the builder

Exact spacing, icon geometry, sample content, and copy beyond the strings the
owner specified.

## Follow-up: layout and consistency pass

Date: 2026-11-12. Scope: fix duplication, alignment, spacing, and resize
behaviour without changing the palette, the shell, the database, or the auth
logic.

- **Branding.** The EntertainX mark and name appear only in the custom title
  bar. The sidebar has no logo or project name; it opens directly with
  navigation, so the rail reads as pure navigation.
- **One logout action.** The sidebar footer owns logout: profile avatar,
  username, "Signed in", and a 36x36 icon button (pink `logout` glyph, subtle
  elevated background, hover/pressed states, "Log out" tooltip and accessible
  name). `MainWindow` wires it to the existing auth logout; `MainApp` returns
  to the login view. `ContentArea` and `SettingsPage` no longer accept a
  logout callback. Settings keeps a Session card that points to the sidebar.
- **Sidebar structure.** Header -> nav (Video, Music, Games, My Lists,
  Settings) -> stretch -> divider -> profile/logout footer. The stretch keeps
  the footer at the bottom at every window height; the username is an
  `ElidedLabel` with an `Ignored` horizontal policy so long names truncate
  instead of displacing the logout button.
- **Stable content axis.** The sub-tab strip is always present, including
  single-tab categories. The first tab label shares the 32px page-title axis
  (14px bar margin + 18px tab padding), so page headers no longer jump by the
  strip height when switching categories.
- **Shared metrics.** `CONTROL_HEIGHT = 44` for search fields and toolbars,
  `CARD_THUMB_HEIGHT = 150` for every media card, and `SPACE_XS` for card text
  spacing. Pages no longer override card thumb heights, so cards are the same
  height across Video, Music, and Games.
- **Responsive grid.** `CardGrid.minimumSizeHint()` reports one card width
  instead of the live layout minimum. Without it, the grid locked wider than
  the viewport after a resize and clipped the last column; it now drops to 2
  columns at 900px and returns to 4 when widened.
- **Wrapping detail copy.** The game detail description wraps instead of
  relying on a single-line elided label, removing the horizontal scrollbar on
  the Chess/Fireboy pages at the minimum window size.
