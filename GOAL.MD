# GOAL.md — EntertainX

## Goal
Build a complete, polished multi-category entertainment desktop application called **EntertainX** from scratch.

Develop EntertainX, a Python desktop application that combines Movies and TV Shows, Music and Audio, and Video Games in one unified GUI. Registered users should be able to browse and search entertainment content from official external APIs, view supported details, customize the application's primary and secondary theme colors, and manage a personal favorites/library stored locally. EntertainX must also let the user start and actually play a game inside the same application GUI through an API-based integration.

The app must combine three main sections in a single modern GUI:
- Movies & TV Shows
- Music
- Games

Users can explore content, view details, rate items, and manage personal lists — all inside one cohesive application.

---

## Tech Stack (Locked)
- GUI Framework: **PySide6** (Qt for Python — LGPL, assignment-approved PyQt/PySide option)
- Database: **SQLite** (`sqlite3`)
- Password Security: `hashlib` + salt (never store plain-text passwords)
- HTTP Requests: `requests`
- Image Handling: `Pillow` + Qt's built-in `QPixmap`/`QImage`
- Environment Variables: `python-dotenv` (for any API keys)
- Theming: **QSS** (Qt Style Sheets) — User-selectable Primary + Secondary colors + Dark/Light mode
- Embedded Web View: `QWebEngineView` (for playable in-GUI game integration)

**APIs are flexible** — Use any reliable free APIs that provide good data for Movies/TV, Music, and Games. Prefer APIs that are stable and easy to use.

---

## Definition of Done (Must All Be True)

### 1. Authentication System (Mandatory)
- [ ] User Registration (username + password)
- [ ] User Login
- [ ] Clear error messages for wrong credentials
- [ ] Passwords are properly salted and hashed
- [ ] Logout functionality
- [ ] Session is maintained until logout

### 2. Application Structure
- [ ] Single unified application with clear navigation between:
  - Movies & TV Shows
  - Music
  - Games
- [ ] Consistent design language across all three sections
- [ ] Smooth page transitions

### 3. Movies & TV Shows Section
- [ ] Search functionality
- [ ] Trending / Popular content
- [ ] Detailed view (poster, overview, rating, genres, cast, release info)
- [ ] Trailer support (if available from the chosen API)
- [ ] Recommendations (if supported by API)
- [ ] User can rate (1–5 stars)
- [ ] Add to personal lists

### 4. Music Section
- [ ] Search for artists, songs, or albums
- [ ] Display relevant information (cover art, artist, album, duration, etc.)
- [ ] Ability to view details
- [ ] User can rate tracks/albums (1–5 stars)
- [ ] Add to personal lists
- [ ] Optional: Preview / external link if the free API supports it

### 5. Games Section
- [ ] Search for games
- [ ] Display game details (cover, rating, genres, platforms, release date, description)
- [ ] User can rate games (1–5 stars)
- [ ] Add to personal lists
- [ ] Show screenshots or additional media if available from the API

### 6. Personal Lists System (Shared across all categories)
- [ ] At least three list types:
  - Favorites
  - Watchlist / Playlist / Want to Play
  - Completed / Watched / Played
- [ ] Users can add and remove items from any category into these lists
- [ ] Dedicated page to view all items in each list (with category indicators)

### 7. Theming System
- [ ] Dark Mode and Light Mode
- [ ] User can choose **Primary** and **Secondary** theme colors
- [ ] Theme preference is saved per user and restored on login
- [ ] Theme applies consistently across the entire application

### 8. User Experience & Polish
- [ ] Modern and clean PySide6/Qt interface
- [ ] Loading indicators when fetching data
- [ ] Proper error handling (network issues, API failures, empty results)
- [ ] Consistent spacing, typography, and visual hierarchy
- [ ] App feels cohesive (not like three separate apps forced together)

### 9. Code Quality
- [ ] Clean project structure with separation of concerns
- [ ] Reusable components (cards, rating widget, etc.)
- [ ] No giant single-file codebase
- [ ] Meaningful naming
- [ ] `.env.example`, `requirements.txt`, and `README.md` included
- [ ] API keys never hardcoded

### 10. Security & Stability
- [ ] No plain-text passwords
- [ ] App does not crash on common errors
- [ ] Database tables created automatically on first run

---

## Recommended Project Structure
entertainx/
├── main.py
├── .env
├── .env.example
├── requirements.txt
├── README.md
├── database/
│   └── db.py
├── auth/
│   └── auth_manager.py
├── api/
│   ├── movies.py
│   ├── music.py
│   └── games.py
├── theme/
│   └── theme_manager.py
├── ui/
│   ├── login_window.py
│   ├── main_window.py
│   ├── movies/
│   ├── music/
│   ├── games/
│   ├── lists_window.py
│   ├── settings_window.py
│   └── components/
│       ├── content_card.py
│       └── star_rating.py
└── assets/



---

## Fitness Function (Score out of 100)

| Category                        | Points | Description |
|--------------------------------|--------|-----------|
| Authentication & Security      | 15     | Fully working + secure |
| Overall App Structure & Navigation | 12  | Unified feel across 3 sections |
| Movies & TV Shows Section      | 15     | Search, details, rating, lists |
| Music Section                  | 13     | Search, details, rating, lists |
| Games Section                  | 13     | Search, details, rating, lists |
| Shared Lists System            | 8      | Works across all categories |
| Custom Theming                 | 10     | Primary + Secondary + Dark/Light |
| UI/UX Polish & Consistency     | 8      | Modern, clean, cohesive |
| Code Quality & Structure       | 6      | Clean, maintainable, well organized |

**Target Score: ≥ 90**

---

## Constraints (Hard Rules)
1. Must use **PySide6** (Qt for Python) only
2. Must support **Movies/TV + Music + Games** in one application
3. APIs must be free (or free-tier) — agent may choose the best available free options
4. Must use SQLite for all user data
5. Never store plain-text passwords
6. Never hardcode API keys
7. Theme system must be fully functional and persistent
8. Prioritize reliability, clean code, and good UI over adding too many extra features

---

## Operating Mode
**Converge**

Suggested build order:
1. Project setup + Database + Authentication
2. Main navigation structure (Movies / Music / Games)
3. Movies & TV Shows section
4. Music section
5. Games section
6. Shared Lists + Ratings system
7. Theme system (colors + dark/light)
8. Final polish, error handling, and consistency pass

---

## Success Criteria Summary
EntertainX is complete when a user can:
- Securely register and log in
- Browse and search Movies/TV, Music, and Games in one app
- View rich details for each type of content
- Rate items and manage personal lists across all categories
- Fully customize the app’s colors and theme mode
- Enjoy a modern, stable, and cohesive experience

---