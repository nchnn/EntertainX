# GOAL.md — EntertainX

> **Role:** Compact working summary — the daily driver for all development decisions.
> **Full Specification:** See [`GOAL_SPEC.md`](file:///c:/Users/chris/OneDrive/Desktop/EntertainX/GOAL_SPEC.md) for detailed architecture, schemas, security specs, and module contracts.
> **Course:** ITL313-18 — SIA 2 LAB Final Term Mini Project (AY 2026–2027)
> **Target Score:** ≥ 92 / 100

---

## Project Identity

**EntertainX** — A unified multi-category entertainment desktop app combining Movies & TV Shows, Music, and Video Games (including playable in-GUI games) into a single PySide6 window.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.12+ |
| GUI | PySide6 (Qt 6) |
| Database | SQLite 3 (`sqlite3` module) |
| Auth | PBKDF2-HMAC-SHA256, 32-byte salt, `hmac.compare_digest` |
| HTTP | `requests` + `QThreadPool` workers |
| Styling | Tokenized QSS with runtime hot-swap |
| Env | `python-dotenv` (`.env` ignored, `.env.example` committed) |

---

## Core Requirements (Non-Negotiable)

1. **Single unified window** — sidebar nav + stacked content viewport
2. **Secure auth** — registration, login, logout; PBKDF2 hashing; no plain-text passwords
3. **Movies & TV** — zero-cost API, search, trending, detail view, star ratings, list actions
4. **Music** — zero-cost API, search, metadata, audio previews, ratings, playlists
5. **Games Catalog** — zero-cost API, browse, metadata, screenshots, ratings
6. **Playable In-GUI Game** — interactive game inside the app window (QWebEngineView or native Qt); no external browser; session tracking in `game_sessions` table
7. **Personal Lists** — Favorites / Watchlist / Completed across all categories; SQLite-backed
8. **Dynamic Theming** — custom Primary & Secondary colors via QColorDialog; Dark/Light mode toggle; persisted per-user in SQLite; instant QSS recompile
9. **Zero-Cost Mandate** — no credit cards, no expiring trials, no paid proxies

---

## Key Constraints

- **No** `webbrowser.open()` or external process spawning for games
- All API calls on background threads; never block the Qt main thread
- Parameterized SQL queries only (`?` placeholders); no f-string SQL

---

## Architecture Quick Reference

| Directory | Purpose |
|---|---|
| `api/` | One adapter per domain (movies, music, games) |
| `auth/` | AuthManager, password hashing, session |
| `database/` | SQLite init, DAO, migrations |
| `theme/` | ThemeManager, QSS tokens |
| `ui/` | Main window, sidebar, content area |
| `ui/pages/` | Feature pages (video, music, games, lists, settings) |
| `ui/components/` | Reusable widgets (ContentCard, StarRating, SearchBar, etc.) |

**Database tables:** `users`, `user_settings`, `library_items`, `user_ratings`, `game_sessions`

> For full DDL, security specs, module contracts, and UI component details → [`GOAL_SPEC.md`](file:///c:/Users/chris/OneDrive/Desktop/EntertainX/GOAL_SPEC.md)

---

## Current Progress

> **Estimated Score:** ~55 / 100 (Phases 1–3 complete)

### Definition of Done Checklist

#### ✅ 1. Authentication System
- [x] Registration with username, email, password validation
- [x] Login with secure credential verification
- [x] Generic error messages (no user enumeration)
- [x] PBKDF2-HMAC-SHA256 with 32-byte salts
- [x] Logout clears session, redirects to login
- [x] Session maintained across views

#### ✅ 2. App Structure & Navigation
- [x] Unified shell with persistent sidebar
- [x] Category separation: Video, Music, Games, My Lists, Settings
- [x] Dynamic sub-tab bar with category memory
- [x] Smooth page transitions

#### ✅ 3. Movies & TV Shows
- [x] Zero-cost API search and discovery (TMDB)
- [x] Trending/popular grids on load (11 shelves: trending, categories, genres)
- [x] Rich detail view (poster, plot, genres, cast, director, runtime, certification)
- [x] Movie vs. TV visual distinction (kind chip, season count vs runtime)
- [ ] Star ratings saved to SQLite
- [ ] Add to personal lists

#### ⏳ 4. Music
- [x] Artist/album/track search
- [x] Album art, metadata, durations
- [x] High-bitrate audio streaming playback (320kbps & previews)
- [ ] Star ratings saved to SQLite
- [ ] Add to playlists/favorites

#### 🟡 5. Games Catalog
- [x] Genre/platform search and discovery
- [ ] Cover art, publisher, system requirements
- [ ] Star ratings and Want-to-Play lists
- [ ] Screenshot carousel

#### 🟡 6. Playable In-GUI Game
- [x] Interactive game inside the app window
- [ ] API-supported session flow
- [x] No external browser — contained in Qt
- [ ] Keyboard/mouse controls, real-time feedback
- [ ] Start, play, pause, game-over, restart

#### ⬜ 7. Personal Lists
- [ ] Favorites / Watchlist / Completed across all categories
- [ ] Cross-category filtering
- [ ] SQLite persistence per user
- [ ] Remove and toggle list status

#### ⬜ 8. Dynamic Theming
- [ ] Custom Primary & Secondary colors (QColorDialog)
- [ ] Dark / Light mode toggle
- [ ] Persisted per user in SQLite
- [ ] Instant QSS recompile without restart

#### ⬜ 9. UX Polish
- [ ] Async background loading (no freezes)
- [ ] Loading spinners and debounced search
- [ ] Error handling for network issues and empty states
- [ ] Visually cohesive modern styling

#### ⬜ 10. Code Quality
- [ ] Clean modular architecture
- [ ] Reusable UI components
- [ ] No hardcoded secrets; `.env.example` present

---

## Scoring Rubric (Summary)

| Category | Max | Target |
|---|:---:|:---:|
| Authentication & Security | 15 | 15 |
| App Structure & Navigation | 12 | 12 |
| Movies & TV Shows | 15 | 14 |
| Music & Audio | 13 | 12 |
| Games (Catalog + Playable) | 13 | 12 |
| Personal Lists | 8 | 8 |
| Dynamic Theming | 10 | 10 |
| UI/UX Polish | 8 | 7 |
| Code Quality & Architecture | 6 | 6 |
| **Total** | **100** | **≥ 92** |

> For the full 40-point acceptance criteria matrix → [`GOAL_SPEC.md` §10](file:///c:/Users/chris/OneDrive/Desktop/EntertainX/GOAL_SPEC.md)
