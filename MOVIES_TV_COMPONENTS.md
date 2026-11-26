# Movies & TV Shows Component Architecture

EntertainX provides a Netflix-style browsing and discovery experience for Movies and TV Shows. Both sections are powered by a shared, modular component system backed by The Movie Database (TMDB) API v3.

This document details every component, its responsibilities, signal interfaces, visual mechanics, and data flow.

---

## 1. System Architecture & Data Flow

All network operations run off the Qt main thread to guarantee smooth 60 FPS scrolling and animations.

```
                  +-----------------------------------+
                  |        TMDB REST API (v3)         |
                  +-----------------------------------+
                                    |
                             HTTP / JSON Cache
                                    v
                  +-----------------------------------+
                  |   TmdbClient (api/movies.py)      |
                  +-----------------------------------+
                                    |
                        api.tasks.run_async()
                     (QThreadPool worker threads)
                                    |
                            QueuedConnection
                                    v
+-------------------------------------------------------------------------+
| GUI THREAD: BrowsePage (ui/pages/video_browse.py)                       |
| Base controller for MoviesPage and TVShowsPage                          |
+-------------------------------------------------------------------------+
  |
  +---> Toolbar (Search IconLineEdit, Genre QComboBox, Refresh QPushButton)
  |
  +---> Browse View (Default)
  |       |-- HeroBanner (ui/components/hero_banner.py)
  |       |-- Top10Panel (ui/components/top10_panel.py)
  |       \-- MediaRow shelves (ui/components/media_row.py) [11 total]
  |             \-- TitleTile (ui/components/title_tile.py)
  |
  +---> Results View (Search / Filter Active)
  |       \-- TileGrid (ui/components/tile_grid.py)
  |             \-- TitleTile (ui/components/title_tile.py)
  |
  +---> Overlays (Floating directly above page viewport)
  |       |-- HoverPreview (ui/components/hover_preview.py)
  |       \-- TitleDetailOverlay (ui/components/title_detail.py)
  |
  \---> Standalone Modals
          \-- TrailerDialog (ui/components/trailer_dialog.py)
```

---

## 2. Core Page Controllers

### `BrowsePage`
- **File:** `ui/pages/video_browse.py`
- **Inherits:** `PageShell` (`ui/pages/page_shell.py`)
- **Role:** Central orchestrator for the video browsing experience. Manages view switching, asynchronous task scheduling, lazy shelf loading, and floating overlay coordination.
- **Key Mechanics:**
  - **Eager vs. Lazy Shelf Loading:** On initial load, fetches only the first 3 shelves (`EAGER_ROWS = 3`). Attaches a listener to the vertical scrollbar. When a shelf comes within 360 pixels below the viewport (`LOOKAHEAD = 360`), `_request_visible_rows` triggers its background fetch.
  - **Search Debounce:** Search input is throttled by a 350ms single-shot `QTimer` (`SEARCH_DEBOUNCE_MS = 350`) to avoid flooding TMDB during typing.
  - **View Switching:** Toggles between `browse_box` (hero and horizontal shelves) and `results_box` (grid of results) depending on whether search text or genre filters are active.
  - **Shared Memory Cache:** Keeps an in-memory dictionary of loaded `MediaDetails` keyed by `(media_type, id)` so repeated hover previews and detail clicks resolve instantly.

### `MoviesPage`
- **File:** `ui/pages/video_movies.py`
- **Inherits:** `BrowsePage`
- **Role:** Subclasses `BrowsePage` configured with `media_type="movie"` and title `"Movies"`. Loads movie-specific shelf definitions (`MOVIE_ROWS`).

### `TVShowsPage`
- **File:** `ui/pages/video_tvshows.py`
- **Inherits:** `BrowsePage`
- **Role:** Subclasses `BrowsePage` configured with `media_type="tv"` and title `"TV Shows"`. Loads television-specific shelf definitions (`TV_ROWS`).

---

## 3. UI Display & Browsing Components

### `HeroBanner` & `_Dots`
- **File:** `ui/components/hero_banner.py`
- **Role:** Large featured billboard at the top of the browse feed.
- **Visual & Functional Features:**
  - Shows up to 6 trending items with high-resolution backdrop artwork (1280px).
  - Smooth cross-fade transition (`FADE_MS = 700`) using `QVariantAnimation` with cubic easing.
  - Automatic rotation every 9 seconds (`ROTATE_MS = 9000`), paused on hover or when `ENTERTAINX_REDUCE_MOTION=1`.
  - Gradient scrims: horizontal scrim darkening left-to-right for text contrast, vertical scrim fading into the page background.
  - Metadata block: Category chip ("MOVIE" / "TV SERIES"), Trending rank chip, title, star rating, release year, genre tags, and trimmed overview (up to 230 characters).
  - Action buttons: "Play Trailer" and "More Info".
  - `_Dots` sub-widget: Clickable indicator pills reflecting current slide position.
- **Signals:**
  - `play_clicked(MediaItem)`: Emitted when the play button is clicked.
  - `info_clicked(MediaItem)`: Emitted when "More Info" is clicked.

### `Top10Panel` & `Top10Tile`
- **File:** `ui/components/top10_panel.py`
- **Role:** Ranked horizontal strip displaying the top 10 trending items of the day.
- **Visual & Functional Features:**
  - `Top10Tile`: Custom-painted tile featuring a large rank numeral (1 to 10) painted directly behind the poster card.
  - **Numeral Typography:** Uses a heavy sans-serif font stack (`Impact`, `Arial Black`, `Segoe UI Black`, 220px). Painted with a dark outer glow path, chrome metallic gradient fill, and light edge stroke.
  - **Card Layer:** Foreground poster tile (210x310px) with rounded corners and a soft cast shadow falling onto the rank numeral.
  - Resolves English localized posters in the background via `provider.resolve_english_poster`.
- **Signals (`Top10Tile`):**
  - `entered(object)`: Mouse entered tile bounds.
  - `left(object)`: Mouse left tile bounds.
  - `focused(object)`: Keyboard focus gained.
  - `activated(MediaItem)`: Click or Enter/Space pressed.

### `MediaRow` & `_Viewport`
- **File:** `ui/components/media_row.py`
- **Role:** Horizontally scrolling shelf holding categorized title tiles.
- **Visual & Functional Features:**
  - `_Viewport`: Custom widget clipping the moving horizontal track and forwarding horizontal wheel / trackpad gestures.
  - Smooth page navigation via floating circular left/right arrow buttons (`scroll_page`).
  - Loading State: Shows 8 `SkeletonTile` placeholders with synchronized shimmer.
  - Error State: Shows an inline retry banner with a reload button.
  - Discards off-screen widgets cleanly to keep resource usage bounded.
- **Signals:**
  - `tile_entered(object)`: Passes hovered tile to the page hover controller.
  - `tile_left(object)`: Signals hover exit.
  - `item_activated(MediaItem)`: Triggers title detail opening.
  - `scrolled()`: Dismisses open hover previews during shelf scroll.
  - `retry_requested()`: Reloads shelf data after an error.

### `TitleTile`
- **File:** `ui/components/title_tile.py`
- **Role:** Standard landscape card (16:9 ratio, default 264x148px) used inside all `MediaRow` shelves.
- **Visual & Functional Features:**
  - Antialiased rounded corners (`RADIUS_MD`).
  - Background art rendered via `draw_cover` (CSS cover behavior with crop/scale).
  - Background English backdrop resolution via `provider.resolve_english_backdrop`.
  - Gradient scrim overlay across the bottom 55% for text readability.
  - Text metadata: Title, year, star rating, and optional badge pill ("TOP 10", "NEW").
  - Hover and keyboard focus indicator ring.
- **Signals:**
  - `entered(object)`: Emitted when pointer enters.
  - `left(object)`: Emitted when pointer leaves.
  - `focused(object)`: Emitted on focus in.
  - `activated(MediaItem)`: Emitted on click or Return/Enter/Space.

### `TileGrid`
- **File:** `ui/components/tile_grid.py`
- **Role:** Responsive grid container used for displaying search results and genre-filtered titles.
- **Visual & Functional Features:**
  - Dynamic reflow (`_reflow`): Calculates column count based on available container width (`width // (TILE_WIDTH + GAP)`).
  - Re-evaluates on window resize events to maintain uniform margins and spacing.
  - Forwards `tile_entered`, `tile_left`, and `item_activated` signals to `BrowsePage`.

---

## 4. Overlay & Interaction Components

### `HoverPreview` & `_ScaleFadeEffect`
- **File:** `ui/components/hover_preview.py`
- **Role:** Netflix-style floating card that expands out of a hovered tile after an intent delay.
- **Visual & Functional Features:**
  - **Root-level placement:** Instantiated as a direct child of `BrowsePage` so it can visually overlap neighboring shelves without clipping.
  - **Two-phase interaction timing:**
    - Phase 1 (Intent delay): Waits 350ms before opening to avoid flashing while moving across tiles.
    - Phase 2 (Autoplay countdown): Once expanded, displays a 2.5-second countdown progress bar across the bottom of the video viewport before starting the trailer.
  - **Scale & Fade Animation:** `_ScaleFadeEffect` custom `QGraphicsEffect` scales the card from 0.84 to 1.0 about the tile anchor while fading opacity from 0.0 to 1.0.
  - **Embedded Web Player:** Uses `QWebEngineView` to host an embedded YouTube iframe (`embed_hover_html`) featuring:
    - Official English title logo image overlay.
    - Audio mute/unmute floating toggle button.
    - Close button.
  - **Action Toolbar:** Includes Play button, Watchlist toggle button, and "More Info" expand button.
- **Signals:**
  - `play_requested(MediaItem)`: Triggers trailer playback.
  - `details_requested(MediaItem)`: Expands full detail overlay.
  - `details_needed(MediaItem)`: Requests background fetch of full details.
  - `wheel_passthrough(QWheelEvent)`: Forwards wheel events back to the parent scroll area so scrolling is uninterrupted.

### `TitleDetailOverlay` & `_Header`
- **File:** `ui/components/title_detail.py`
- **Role:** Full-screen modal overlay panel providing complete title metadata.
- **Visual & Functional Features:**
  - Semi-transparent backdrop scrim (`QColor(0, 0, 0, 180)`) with smooth fade animation.
  - `_Header`: Visual billboard containing backdrop artwork or embedded `QWebEngineView` trailer player with autoplay countdown.
  - Content details:
    - Title logo / text.
    - Tagline.
    - Star rating pill and MPAA/TV certification badge.
    - Release year, runtime (movies) or season/episode counts (TV).
    - Full overview narrative.
    - Genre tags.
    - Cast roster and Director / Creator credits.
  - Keyboard accessible: Esc closes the overlay.
- **Signals:**
  - `play_requested(MediaItem)`: Starts trailer playback.
  - `closed()`: Emitted when overlay finishes closing.

### `TrailerDialog`
- **File:** `ui/components/trailer_dialog.py`
- **Role:** Standalone modal dialog dedicated to full-window YouTube trailer playback.
- **Visual & Functional Features:**
  - Loads YouTube privacy-enhanced embed (`youtube-nocookie.com`).
  - Sets `strict-origin-when-cross-origin` referrer policy to avoid YouTube embed error 153.
  - Automatically terminates video audio and playback on close (`done`).
  - Graceful degradation message if `PySide6.QtWebEngineWidgets` is unavailable.

---

## 5. Supporting Primitives & Infrastructure

| Component / Utility | Location | Role in Movies & TV |
|---|---|---|
| `TmdbClient` | `api/movies.py` | Handles all TMDB API endpoints, requests, TTL file caching, and error handling. |
| `MediaItem` & `MediaDetails` | `api/movies.py` | Immutable domain data structures for titles and rich metadata. |
| `ImageStore` | `api/images.py` | Asynchronous image downloader with on-disk PNG/JPG cache and in-memory LRU cache. |
| `run_async` | `api/tasks.py` | Thread-pool dispatch ensuring no network or disk I/O ever touches the Qt GUI thread. |
| `SkeletonTile` & `pulse_clock` | `ui/components/skeleton.py` | Central sinusoidal pulse timer driving synchronized shimmer placeholders during data load. |
| `EmptyState` | `ui/components/surfaces.py` | Clean placeholder display when search returns 0 matches or TMDB API key is missing. |
| `InlineBanner` | `ui/components/surfaces.py` | Non-blocking inline banner for network failure warnings. |
| `IconLineEdit` | `ui/components/fields.py` | Styled search line edit with embedded Lucide search icon. |
| `draw_cover` | `ui/components/artwork.py` | Custom painter helper computing aspect-ratio crop rectangles for image rendering. |

---

## 6. Implementation Checklist & Status (vs. GOAL.md)

- [x] Zero-cost API integration (The Movie Database via `TmdbClient`)
- [x] 11 shelves per section (Trending, Now Playing / Airing Today, Popular, Top Rated, and Genre shelves)
- [x] Top 10 Today ranked panel with custom-painted chrome numerals
- [x] Billboard Hero Banner with smooth fade transitions and auto-rotation
- [x] Netflix-style hover preview card with scale-in animation and 2.5s trailer countdown
- [x] Full-screen Title Detail modal panel with cast, genres, credits, and logo art
- [x] Standalone full-dialog trailer player
- [x] Live search with 350ms debounce and genre category dropdown filter
- [x] Lazy shelf loading based on viewport scroll position
- [ ] Star ratings saved to SQLite database (Pending)
- [ ] Add to personal Watchlist / Favorites database tables (Pending)
