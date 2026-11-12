# GOAL.md — EntertainX: Comprehensive Unified Entertainment Desktop Application Specification

> **Document Status:** Authoritative Single Source of Truth for EntertainX Architecture, Requirements, and Implementation.
> **Course:** ITL313-18 (Systems Integration and Architecture 2 Laboratory / SIA 2 LAB) — Final Term Mini Project
> **Academic Term:** Academic Year 2026–2027
> **Selected Category:** Media and Entertainment
> **Core Content Domains:** Movies and TV Shows; Music and Audio; Video Games
> **Interactive Gameplay Integration:** Playable In-GUI Game Engine via Zero-Cost API Integration
> **External API Operational Policy:** Strict Zero-Cost ($0) Requirement across all functional modules (no credit card requirements, no paid cloud proxies, no time-limited trials, no promotional balance dependencies)
> **Target Evaluation Fitness Score:** ≥ 92 / 100 Points (Mandatory Definition of Done Threshold)
> **Reference Document:** `EntertainX_GOAL.md` (Base Requirements Specification)
> **Last Revision Date:** November 2026

---

## 1. Document Overview and Administrative Metadata

This document, `GOAL.md`, serves as the comprehensive, technically binding, and authoritative architectural specification for **EntertainX**. Developed as the final term capstone laboratory project for ITL313-18 (Systems Integration and Architecture 2 Laboratory), EntertainX synthesizes modern desktop GUI design, secure local SQLite persistence, cryptographically salted authentication, asynchronous networking, defensive REST API integration, dynamic QSS theming, and embedded real-time interactive game execution.

### 1.1 Academic Purpose and Learning Objectives
The instructional intent within ITL313-18 is guiding student engineers from isolated CLI scripts to architecting cohesive, multi-tiered desktop systems, confronting the engineering challenges of:
1. **Asynchronous Desktop GUI Engineering:** Managing Qt (PySide6) single-threaded event loop constraints by deploying background worker threads (`QThread`, `QThreadPool`, `QRunnable`) to prevent network blocking and ensure a responsive 60 FPS GUI.
2. **Defensive Systems Integration:** Interfacing with diverse third-party REST services under unpredictable latency, rate limits, and zero-cost constraints, using modular API adapters to isolate schema volatility from UI layers.
3. **Cryptographic Data Protection:** Implementing credential salting and iterative key derivation (`PBKDF2-HMAC-SHA256`) via Python `hashlib` to ensure credentials are never stored in plain text or unsalted hashes.
4. **Relational Data Modeling and Transactional Integrity:** Designing normalized SQLite schemas enforcing referential integrity (`PRAGMA foreign_keys = ON`), constraints, indexes, and parameterized queries to eliminate SQL injection vulnerabilities.
5. **Interactive Media Embedding:** Integrating interactive gameplay inside the desktop window via `QWebEngineView` or native Qt canvas rendering without external browser popups while maintaining zero financial cost.
6. **Stateful Dynamic Styling Architecture:** Creating a tokenized Qt Style Sheet (QSS) system enabling users to customize primary/secondary theme colors via native color dialogs, persisting settings across user sessions.

### 1.2 Document Authority and Hierarchy
Within the EntertainX software repository, this document represents the single source of truth (`SSOT`). All planning documents, including implementation checklists, task tracking trackers (`TASKS.md`), developer guidelines (`AGENTS.md`), and automated integration test suites, derive their acceptance criteria and verification metrics directly from the statements, schemas, tables, and constraints detailed herein. 

Where discrepancies arise, this document prevails. Modifications require formal architectural review and owner sign-off. Developers and agents must not unilaterally dilute, bypass, or delete core requirements, such as in-GUI gameplay or the zero-cost mandate.

---

## 2. Executive Summary, Problem Statement, and Core Objectives

### 2.1 Project Vision
EntertainX is a unified desktop hub harmonizing three entertainment sectors—cinematic media (Movies & TV Shows), auditory media (Music & Audio), and interactive digital entertainment (Video Games & Playable Games)—into a single PySide6 GUI. Consolidating search, discovery, metadata inspection, personal library curation, star ratings, and embedded real-time gameplay into a native desktop shell, EntertainX provides an integrated media experience.

### 2.2 The Problem of Entertainment Fragmentation
Contemporary digital entertainment is plagued by fragmentation. Users juggle separate browser tabs, streaming portals, web databases, and game launchers to track releases, listen to previews, read summaries, or play quick games. This creates:
- **Resource Overhead:** Heavyweight, JavaScript-saturated browser tabs consume gigabytes of RAM and processor cycles.
- **Interface Inconsistency:** Distinct UI paradigms, typography, and color schemes cause friction when switching between services.
- **Advertising Clutter:** Intrusive third-party ads, tracking beacons, video commercials, and cookie prompts slow down discovery.
- **Siloed Libraries:** Users cannot maintain a single cross-media queue; watchlists, playlists, and game wishlists remain separated across distinct accounts.

EntertainX solves these pain points by providing a centralized, local-first desktop application engineered with clean Qt widgets, local SQLite storage, zero tracking, and a unified personal library spanning all supported entertainment categories.

### 2.3 Core Project Objectives
To satisfy the requirements of ITL313-18 and the vision established by the project owner, EntertainX is structured around seven foundational engineering goals:
1. **Unified Application Experience:** Presenting a single, cohesive desktop window featuring an intuitive persistent navigation sidebar, dynamic header breadcrumbs, and silky category page transitions.
2. **Multi-Domain Information Retrieval:** Integrating reliable, zero-cost external REST APIs to provide real-time search, discovery, trending feeds, and rich metadata visualization for Movies, TV Shows, Music, and Video Games.
3. **Embedded Interactive In-GUI Gameplay:** Providing a fully interactive, playable game directly inside the EntertainX application window via an API-driven session flow, explicitly rejecting external browser redirects or separate unmanaged application windows.
4. **Zero-Cost Sustainable Architecture:** Guaranteeing that the application operates perpetually at zero commercial cost ($0.00), utilizing only free-tier APIs that require no billing activation, payment cards, or expiring promotional subscriptions.
5. **Robust Local Security and Authentication:** Implementing a secure local SQLite authentication subsystem that enforces strong password hashing with random per-user salts, protecting user credentials against dictionary, rainbow table, and offline brute-force attacks.
6. **Cross-Category Personal Library and Ratings:** Empowering registered users to curate unified personal collections (Favorites, Watchlist / Playlist / Want-to-Play, and Completed / Watched / Played) and assign granular 1-to-5 star ratings across all media domains.
7. **Dynamic Theme Customization:** Enabling users to personalize their visual environment by selecting custom Primary and Secondary accent colors and toggling between Dark and Light modes, persisting these preferences across sessions in SQLite and applying them immediately through runtime QSS styling.

---

## 3. Requirement Sources, Scope Boundaries, and Decision Status

EntertainX clearly demarcates between course assignment requirements, confirmed owner decisions, and implementation recommendations.

### 3.1 Course Specification (ITL313-18 SIA 2 LAB)
The official course laboratory guidelines establish the foundational academic baseline:
- **Technology Platform:** The application must be implemented in Python using a recognized desktop graphical user interface framework. PySide / PyQt and Tkinter are approved GUI options. PySide6 is selected as the optimal Qt binding.
- **User Authentication:** The application must incorporate a functional registration and login subsystem capable of authenticating users before granting access to personalized application state.
- **Database Engine:** SQLite is mandated for all local data persistence, including user credentials, configuration profiles, and application records.
- **Cryptographic Requirements:** Password storage must strictly employ salting and hashing utilizing Python's built-in `hashlib` library. Storing plain-text passwords or using unsalted hashes is strictly prohibited and constitutes an automatic failure condition.
- **Selected Project Domain:** The project must select an approved industry category. EntertainX operates under the **Media and Entertainment** category.
- **Content Scope Analysis:** The course brief illustrates Media and Entertainment with examples: "Movies and TV Shows", "Music and Audio", and "Video Games", accompanied by phrasing suggesting the selection of a single functional area. However, the EntertainX project owner has explicitly chosen to implement **all three content areas** in a single unified architecture, demonstrating advanced integration capability. This comprehensive scope has been formally documented for instructor approval.

### 3.2 Owner-Confirmed Architectural Decisions
The EntertainX project owner has finalized several critical architectural directives that govern development:
- **Application Identity:** Official software name is **EntertainX**.
- **Desktop Paradigm:** Single-window desktop application with a shared navigation sidebar and unified central content viewport. Standalone launcher scripts or fragmented popup windows are disallowed.
- **GUI Toolkit:** **PySide6** (Qt 6 for Python) under the LGPL license, leveraging modern Qt widgets, layouts, signals/slots, and Qt Quick / WebEngine capabilities where appropriate.
- **Authentication Credentials:** User registration requires a valid username, email address, and password. Login requires username and password verification against local SQLite records.
- **Local Data Sovereignty:** All user accounts, appearance settings, ratings, and library collections are stored exclusively within a local SQLite database (`entertainx.db`). No cloud databases, remote user directories, or third-party identity providers (e.g., Firebase, Auth0, Supabase) are permitted or required.
- **API Provider Strategy:** Providers are decoupled via adapter interfaces. While specific APIs are selected for initial development (such as TMDB or TVMaze for video, iTunes/Last.fm for music, and FreeToGame / RAWG for games), the core system must allow effortless swapping of API providers without requiring modifications to the GUI or database layers.
- **Playable Game In-GUI Requirement:** An actual, interactive game must be playable inside the EntertainX interface. This feature is a core requirement, not a stretch goal or optional bonus.
- **Theme Personalization:** Users must be able to choose custom Primary and Secondary accent colors via native color pickers (`QColorDialog`) and switch between Dark Mode and Light Mode, with settings saved in SQLite per user profile.

### 3.3 Critical Architectural Distinction: Game Catalog vs. Playable Game In-GUI
EntertainX strictly separates video game browsing from interactive gameplay into dedicated application views:
1. **Video Games Catalog View:** A discovery and metadata inspection module where users browse, search, and filter video game titles across PC and console platforms, viewing release dates, publisher details, ESRB/PEGI ratings, system requirements, descriptions, and high-resolution screenshots retrieved from external video game APIs.
2. **Playable In-GUI Game View:** A dedicated, fully interactive gaming environment embedded directly inside the EntertainX window. Users can initiate an API-driven game session, interact with game elements via keyboard and mouse controls, experience real-time graphical feedback, pause/resume gameplay, view game-over screens, and restart matches without ever leaving the desktop application window.

External browser redirection (e.g., launching Chrome or Edge via `webbrowser.open()`) or spawning detached external OS processes is strictly forbidden and fails the Playable Game acceptance criteria.

### 3.4 Zero-Cost Academic Mandate
EntertainX operates under a strict **Zero-Cost ($0.00) Mandate**. To ensure reproducibility by evaluators and students, every feature must function without financial cost:
- **No Credit Card Required:** No chosen API or library may require billing activation, credit card registration, or payment verification to obtain an active API key or access tier.
- **No Expiring Trials:** The software must not rely on 14-day or 30-day commercial trial tiers that render the application inoperable after the evaluation window closes.
- **No Paid Proxies or Paid Cloud Hosting:** The system must connect directly from the client machine to official, public, zero-cost API endpoints.
- **Respectful Rate Limiting:** All API adapters must implement polite request throttling, exponential backoff, and local caching to operate comfortably within public free-tier rate limits.
- **Documentation Transparency:** Every external data source must have its zero-cost terms, rate limits, and attribution requirements fully documented in `README.md`.

### 3.5 Out-of-Scope System Boundaries (Anti-Goals)
To prevent scope creep and ensure timely delivery, the following features are explicitly out of scope:
- **Full Movie or TV Episode Video Streaming:** EntertainX does not host, pirate, or stream copyrighted full-length movies or television episodes. Video integration is strictly limited to metadata, official movie trailers, and promotional video clips.
- **Full-Length Music Streaming and MP3 Downloading:** The application does not provide unauthorized full-track music downloads or pirated audio streaming. Audio features are restricted to official 30-second legal preview clips provided by authorized APIs (e.g., Deezer or iTunes).
- **Distributing Copyrighted Binary Game Executables:** EntertainX does not distribute, crack, or install pirated commercial desktop video games. In-GUI gameplay relies on legal, open-access web-engine HTML5/Canvas games or native Qt game logic backed by API session initialization.
- **Cloud Account Synchronization and Web Hosting:** EntertainX does not feature cloud-based multi-device synchronization, user profile sharing, or a web-based companion interface.
- **Social Networking and Multi-User Chat:** Features such as user friends lists, live chat messaging, public comment forums, or social media activity feeds are explicitly excluded.
- **Overcomplicated Theme Scripting:** The theming engine focuses strictly on primary/secondary color customization and dark/light modes. Arbitrary custom CSS editors, font loaders, or widget layout drag-and-drop editors are out of scope.

---

## 4. Technical Stack and Architectural Specifications

EntertainX leverages a curated, modern, and robust technology stack designed to balance performance, developer ergonomics, security, and zero financial cost.

### 4.1 Programming Language and Runtime Environment
- **Language:** **Python 3.12+**
- **Runtime Virtualization:** Standard Python Virtual Environment (`venv`). The entire application, including all dependencies and test harnesses, is contained within an isolated virtual environment (`C:\Users\chris\OneDrive\Desktop\EntertainX\venv`). This guarantees absolute portability across Windows 11 machines without contaminating global interpreter packages.
- **Standard Library Utilization:** Maximum reliance on Python standard library modules (`sqlite3`, `hashlib`, `os`, `sys`, `json`, `time`, `datetime`, `re`, `threading`, `urllib.parse`) to minimize dependency bloat and vulnerability exposure.

### 4.2 Desktop GUI Framework
- **Framework:** **PySide6 (Qt for Python 6.12+)**
- **Licensing Compliance:** GNU Lesser General Public License (LGPLv3), ensuring full legal compliance for open academic and non-commercial desktop development.
- **Core Qt Modules:**
  - `PySide6.QtCore`: Core non-GUI classes (`Qt`, `QThread`, `QThreadPool`, `QRunnable`, `QTimer`, `QUrl`, `Signal`, `Slot`).
  - `PySide6.QtGui`: Graphical primitives (`QColor`, `QPixmap`, `QImage`, `QIcon`, `QFont`, `QPainter`).
  - `PySide6.QtWidgets`: Desktop widgets (`QApplication`, `QMainWindow`, `QWidget`, `QStackedWidget`, layouts, buttons, dialogs).
  - `PySide6.QtWebEngineWidgets`: `QWebEngineView`, providing an embedded Chromium-based browser runtime to execute interactive HTML5/Canvas games directly within the Qt widget tree.

### 4.3 Database and Persistence Architecture
- **Engine:** **SQLite 3**
- **Interface:** Built-in Python `sqlite3` module.
- **Configuration:** Initialized with `PRAGMA foreign_keys = ON;` on every database connection to guarantee strict relational referential integrity.
- **Access Pattern:** Data Access Object (DAO) and Repository patterns with context-managed database connections, explicit commit boundaries, and strict parameterized query binding (`?` placeholders) to make SQL injection physically impossible.

### 4.4 Cryptographic and Security Infrastructure
- **Hashing Algorithm:** Password-Based Key Derivation Function 2 with HMAC-SHA256 (`hashlib.pbkdf2_hmac`).
- **Iteration Count:** 600,000 iterations, following OWASP 2024 recommendations for high-security password storage.
- **Salt Generation:** 32 bytes (256 bits) of cryptographically secure pseudo-random entropy generated via `os.urandom(32)` per individual user account.
- **Comparison Logic:** Constant-time verification via `hmac.compare_digest` to provide complete immunity against side-channel timing analysis attacks.

### 4.5 Networking, Threading, and HTTP Clients
- **HTTP Client:** `requests` library for synchronous, reliable HTTP communication with REST APIs.
- **Concurrency Model:** Multi-threaded asynchronous execution utilizing `QThreadPool` and lightweight `QRunnable` worker objects, or dedicated `QThread` sub-classes for long-running network transfers.
- **Thread Communication:** Worker threads communicate with the PySide6 main GUI thread exclusively through Qt Signals and Slots, guaranteeing that UI widgets are never mutated from secondary threads (which would trigger fatal Qt memory segmentation faults).
- **Network Resilience:** Standard HTTP timeouts (5.0s connect, 10.0s read), automated exponential backoff on HTTP 429 (Too Many Requests), and comprehensive exception trapping for `requests.exceptions.RequestException`.

### 4.6 Media Processing and Image Caching
- **Image Manipulation:** `Pillow` (PIL fork) for image format conversion, aspect-ratio-preserving resizing, and dynamic thumbnail generation.
- **Pixmap Rendering:** `QPixmap.loadFromData()` for instant rasterization of network-downloaded image byte streams.
- **Two-Tier Image Cache:** 
  - Tier 1: In-memory `LRUCache` dictionary holding up to 100 recent `QPixmap` instances for zero-latency card scrolling.
  - Tier 2: Persistent local disk cache (`assets/cache/`) storing raw JPEG/PNG image files hashed by their remote URL (`hashlib.sha256(url.encode()).hexdigest()`), dramatically reducing redundant network requests and conserving API bandwidth.

### 4.7 Styling and Dynamic Design System
- **Styling Engine:** Qt Style Sheets (QSS), an established CSS2-like declarative language tailored for native Qt widgets.
- **Dynamic Compilation:** Centralized `ThemeManager` class that maintains tokenized color variables (`PRIMARY`, `SECONDARY`, `BG_DARK`, `BG_SIDEBAR`, `BG_CARD`, `TEXT_PRIMARY`, `TEXT_SECONDARY`, `BORDER_COLOR`).
- **Runtime Hot-Swapping:** Recompiles the global application QSS string and injects it into `QApplication.instance().setStyleSheet()` whenever a user modifies theme colors or toggles dark/light mode, updating every open widget instantaneously without requiring an application restart.

## 5. Comprehensive Relational Database Architecture

EntertainX uses an embedded SQLite database engine for zero-configuration, ACID-compliant persistence, operating locally without network latency or cloud dependencies to meet zero-cost requirements.

### 5.1 Design Principles and Relational Integrity
The database architecture adheres to strict relational database design principles:
- **Foreign Key Enforcement:** Foreign key constraints are disabled by default in SQLite. EntertainX explicitly enforces referential integrity on every active connection by executing `PRAGMA foreign_keys = ON;` immediately upon opening the database handle.
- **Normalization:** The schema is normalized to Third Normal Form (3NF) to eliminate data redundancy, prevent update anomalies, and maintain clear entity separation between identity credentials, appearance preferences, curated library items, and user ratings.
- **Collation and Uniqueness:** To ensure case-insensitive identity protection, email addresses utilize the `COLLATE NOCASE` attribute. Unique constraints on usernames and emails prevent duplicate accounts at the storage engine level.
- **Transactional Atomicity:** Multi-statement mutations (such as user account deletion with cascading child records or batch library updates) are wrapped in atomic transactions (`BEGIN TRANSACTION ... COMMIT;`) to prevent partial database corruption in the event of an abrupt application crash or system power outage.

### 5.2 Schema Definition and Complete DDL
The EntertainX database schema comprises five core tables: `users`, `user_settings`, `library_items`, `user_ratings`, and `game_sessions`. Below is the complete Data Definition Language (DDL) executed during database initialization:

```sql
-- Enable foreign key constraint checking
PRAGMA foreign_keys = ON;

-- Table 1: User Identity and Cryptographic Credentials
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT    UNIQUE NOT NULL COLLATE NOCASE,
    email         TEXT    UNIQUE NOT NULL COLLATE NOCASE,
    password_hash BLOB    NOT NULL,
    salt          BLOB    NOT NULL,
    created_at    TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- Table 2: User Appearance and Theme Personalization Settings
CREATE TABLE IF NOT EXISTS user_settings (
    user_id         INTEGER PRIMARY KEY,
    primary_color   TEXT    NOT NULL DEFAULT '#6C63FF',
    secondary_color TEXT    NOT NULL DEFAULT '#FF6584',
    theme_mode      TEXT    NOT NULL DEFAULT 'dark' CHECK (theme_mode IN ('dark', 'light')),
    updated_at      TEXT    NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Table 3: Unified Personal Library and Collections (Cross-Category)
CREATE TABLE IF NOT EXISTS library_items (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id          INTEGER NOT NULL,
    provider_key     TEXT    NOT NULL,
    content_type     TEXT    NOT NULL CHECK (content_type IN ('movie', 'tv', 'music', 'game')),
    external_item_id TEXT    NOT NULL,
    title            TEXT    NOT NULL,
    subtitle         TEXT,
    image_url        TEXT,
    list_type        TEXT    NOT NULL DEFAULT 'favorites' CHECK (list_type IN ('favorites', 'watchlist', 'completed')),
    added_at         TEXT    NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE (user_id, provider_key, content_type, external_item_id, list_type)
);

-- Table 4: User Content Ratings and Personal Reviews
CREATE TABLE IF NOT EXISTS user_ratings (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id          INTEGER NOT NULL,
    provider_key     TEXT    NOT NULL,
    content_type     TEXT    NOT NULL CHECK (content_type IN ('movie', 'tv', 'music', 'game')),
    external_item_id TEXT    NOT NULL,
    rating_score     INTEGER NOT NULL CHECK (rating_score BETWEEN 1 AND 5),
    review_notes     TEXT,
    updated_at       TEXT    NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE (user_id, provider_key, content_type, external_item_id)
);

-- Table 5: Playable Game Activity and Session Telemetry
CREATE TABLE IF NOT EXISTS game_sessions (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id          INTEGER NOT NULL,
    game_identifier  TEXT    NOT NULL,
    game_title       TEXT    NOT NULL,
    duration_seconds INTEGER NOT NULL DEFAULT 0,
    session_outcome  TEXT    CHECK (session_outcome IN ('completed', 'forfeit', 'abandoned', 'victory', 'defeat')),
    played_at        TEXT    NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Performance Optimization Indexes
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_library_user_list ON library_items(user_id, list_type);
CREATE INDEX IF NOT EXISTS idx_library_lookup ON library_items(user_id, provider_key, content_type, external_item_id);
CREATE INDEX IF NOT EXISTS idx_ratings_lookup ON user_ratings(user_id, provider_key, content_type, external_item_id);
CREATE INDEX IF NOT EXISTS idx_game_sessions_user ON game_sessions(user_id, played_at);
```

### 5.3 Data Access Object (DAO) Pattern and Thread Safety
Because SQLite connections cannot safely be shared across threads in PySide6, EntertainX implements a thread-local connection factory:
- `database/db.py` exposes `get_connection(db_path: str = "entertainx.db") -> sqlite3.Connection`. Every thread that performs database I/O obtains its own dedicated connection instance and closes it upon task completion using Python's context manager (`with get_connection() as conn:`).
- `init_db(conn: sqlite3.Connection) -> None` idempotently executes the DDL script shown above, creating all missing tables, triggers, and indexes upon the initial launch of the application.
- All query arguments are strictly supplied via parameter tuples (`cursor.execute("SELECT ... WHERE username = ?", (username,))`). String interpolation or formatted f-strings are strictly banned from SQL statements.

---

## 6. Security, Cryptography, and Zero-Cost Compliance Specifications

Security in EntertainX is designed defensively, recognizing that desktop database files and application bytecodes reside in local user environments.

### 6.1 Cryptographic Credential Protection Architecture
User password security follows the course mandate and modern cryptographic standards:
1. **Iterative Key Derivation (PBKDF2):** Unsalted or fast hashes (MD5, SHA-1, single-round SHA-256) are vulnerable to dictionary and GPU brute-force attacks. EntertainX enforces **PBKDF2-HMAC-SHA256** with **600,000 iterations**, creating a robust barrier against offline attacks while executing in ~80 milliseconds during login.
2. **Cryptographic Salting:** Registration generates a unique 32-byte salt using `os.urandom(32)`, stored in `users.salt` alongside the derived key in `users.password_hash`, ensuring identical passwords yield distinct stored hashes.
3. **Constant-Time Verification:** During login, candidate passwords are processed via `hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), stored_salt, 600000, dklen=32)` and verified using `hmac.compare_digest` to prevent timing attacks.

### 6.2 Defensive Network Security and Untrusted Data Handling
External API interactions require defensive safeguards:
- **Untrusted Input Sanitization:** All JSON payloads and image URLs from external APIs are treated as untrusted input. Text in Qt labels is sanitized using `Qt.PlainText` or tag escaping, preventing XSS vulnerabilities.
- **Network Timeouts and Circuit Breaking:** Outgoing HTTP calls enforce explicit timeouts (5.0s connect, 10.0s read), failing gracefully with fallback data rather than crashing the Qt main thread.
- **Rate-Limit Backoff:** When an external API responds with HTTP status 429 (Too Many Requests), the API adapter captures the `Retry-After` header (or applies an exponential backoff formula: $T = 2^{	ext{attempt}}$ seconds) and surfaces a courteous, informative notification to the user without spamming the remote server.

### 6.3 Secure Secret Management
- **Environment Variable Isolation:** API keys and environment configurations are loaded via `python-dotenv` from a local `.env` file.
- **Repository Cleanliness:** The `.env` file is explicitly ignored in `.gitignore`. A sanitized template file, `.env.example`, is committed to the repository, containing dummy placeholder keys and explicit signup instructions for zero-cost API registration.
- **Client-Side Security Posture:** Environment variables provide configuration separation rather than absolute reverse-engineering immunity; therefore, no privileged master keys are distributed with EntertainX.

### 6.4 Zero-Cost Verification Protocol
Every prospective API candidate must pass this four-step verification protocol:
1. **Financial Barrier Check:** Does the provider mandate a credit card, PayPal account, or billing profile during registration? If **YES**, the provider is immediately disqualified.
2. **Subscription Duration Check:** Does the free tier expire after 7, 14, or 30 days? If **YES**, the provider is immediately disqualified.
3. **Usage Quota Feasibility:** Does the free tier provide sufficient daily request allowances (e.g., at least 500 requests per day) to support interactive student demonstrations and evaluation testing? If **NO**, an alternative provider or local mock adapter must be prepared.
4. **Desktop Redistribution Terms:** Do the provider's Terms of Service permit non-commercial academic desktop client usage? If **YES**, the provider is approved and documented in `README.md`.

---

## 7. Detailed Functional Specifications and Module Requirements

EntertainX is organized into eight interconnected, cohesive functional subsystems. Each module is specified below with detailed interface contracts, behavioral expectations, and visual requirements.

### 7.1 Authentication and Session Management System
The authentication subsystem regulates access, ensuring only authenticated users access personalized features, themes, lists, and gameplay.

#### Registration Flow (`ui/login_window.py` & `auth/auth_manager.py`)
- **Input Fields:** Username (alphanumeric, 3–20 characters), Email (standard RFC 5322 format), Password (minimum 6 characters), and Password Confirmation.
- **Validation Rules:**
  - Username: Cannot be blank; must not contain spaces; must be unique in SQLite `users`.
  - Email: Must contain `@` and valid domain dots; must be unique in SQLite `users` (case-insensitive).
  - Password: Minimum length 6 characters; must match confirmation field exactly.
- **Database Insertion:** Generates a 32-byte salt; derives a 32-byte PBKDF2-HMAC-SHA256 hash; writes to `users` and initializes default records in `user_settings` with `#6C63FF` (Primary) and `#FF6584` (Secondary).
- **Feedback:** On success, displays a green success banner and switches to the Login tab. On validation or constraint failure, highlights offending fields and displays specific, non-leaking error messages (e.g., "Username or email is already registered").

#### Login Flow
- **Input Fields:** Username and Password.
- **Verification:** Queries `users` for the matching username (case-insensitive). If found, computes candidate hash against stored salt and verifies via `hmac.compare_digest`.
- **Security Messaging:** If the user does not exist or the password does not match, displays an identical generic error: "Invalid username or password". This prevents user enumeration vulnerabilities.
- **Session State:** Upon successful authentication, constructs an active session payload:
  ```python
  session_user = {
      "id": user_row[0],
      "username": user_row[1],
      "email": user_row[2]
  }
  ```
  Transitions from `LoginWindow` to `MainWindow`, passing session data and the `AuthManager` instance.

#### Logout Flow
- Accessible from sidebar and Settings. Calling `auth_manager.logout()` clears session state, destroys `MainWindow`, and re-opens `LoginWindow`, flushing cached memory.

### 7.2 Main Window Shell, Sidebar Navigation, and Layout Hierarchy
The presentation layer is governed by `QMainWindow` (`ui/main_window.py`) enforcing a split-view layout:
- **Left Sidebar Navigation (`ui/sidebar.py`):**
  - Fixed width of 220 pixels with background `#16213e`.
  - Top: Application branding header featuring the EntertainX logo and stylized title.
  - Middle: Vertical navigation buttons with custom icons:
    1. **Video** (Movies & TV Shows)
    2. **Music** (Artists, Albums & Tracks)
    3. **Games** (Catalog & Playable In-GUI Games)
    4. **My Lists** (Personal Library & Watchlists)
    5. **Settings** (Theme Customization & Profile)
  - Bottom: Authenticated user badge displaying the active username, an avatar glyph, and an immediate Logout button.
  - State Management: Emits `category_changed(str)` signal when a category is clicked. The active category is highlighted with a primary-colored vertical indicator strip and distinct button background.
- **Central Content Area (`ui/content_area.py`):**
  - Dynamic Sub-Tab Bar: Displayed across the top of the content area for categories containing multiple views:
    * **Video Sub-Tabs:** `YouTube` | `Movies` | `TV Shows`
    * **Music Sub-Tabs:** `Music Discovery` (single tab or artist/album views)
    * **Games Sub-Tabs:** `Chess (Playable)` | `Fireboy & Watergirl (Playable)` | `Browse Games (Catalog)`
    * **My Lists Sub-Tabs:** `All Items` | `Movies & TV` | `Music` | `Games`
    * **Settings Sub-Tabs:** `Appearance & Themes` | `Account Settings`
  - Stacked Viewport (`QStackedWidget`): Houses all instantiated content page widgets. Switching categories or sub-tabs instantly transitions the stacked widget index without page re-creation overhead.
  - State Memory: `ContentArea` maintains a `_last_tab` mapping so navigating away from a category (e.g., from Video -> Music -> Video) immediately restores the user's previously active sub-tab.

### 7.3 Movies and TV Shows Discovery Module (`ui/pages/video_movies.py` & `ui/pages/video_tvshows.py`)
- **External API Adapter:** Interfaced via `api/movies.py` connecting to zero-cost providers such as The Movie Database (TMDB) API or TVMaze API.
- **Functional Capabilities:**
  - **Trending / Popular Feeds:** Automatically populates the landing grid with current trending films and television broadcasts upon page load.
  - **Live Search & Filter:** Responsive search bar with debounced input (300ms delay) allowing users to query titles by keyword, release year, or genre.
  - **Entity Differentiation:** Strictly distinguishes movies from television series, rendering release years for movies and season/episode counts with air dates for TV shows.
  - **Rich Detail Modal / View:** Clicking any title card opens an overlay modal displaying:
    * High-resolution poster and backdrop artwork.
    * Synopsis / plot overview.
    * Genre tags, runtime, content advisory ratings, and release dates.
    * Primary cast and crew credits.
    * Official YouTube trailer playback or link integration where supported.
    * Interactive Star Rating widget (1 to 5 stars).
    * "Add to My Lists" dropdown menu (Favorites, Watchlist, Watched).

### 7.4 Music and Audio Exploration Module (`ui/pages/music.py`)
- **External API Adapter:** Interfaced via `api/music.py` connecting to verified zero-cost providers such as the iTunes Search API, Deezer Free API, or Last.fm Audio API.
- **Functional Capabilities:**
  - **Search by Entity:** Search by artist name, track title, or album release.
  - **Metadata Presentation:** High-resolution album cover art, artist name, track title, album name, release year, and duration (formatted as `MM:SS`).
  - **Legal 30-Second Audio Previews:** Where supported by the free API (e.g., iTunes / Deezer 30-second preview streams), integrates Qt's `QMediaPlayer` or native audio playback component to allow users to listen to audio clips directly within the EntertainX GUI.
  - **Playback Safety:** Full-length songs requiring paid streaming subscriptions (e.g., Spotify Premium or Apple Music paid tiers) are never promised. The interface clearly labels audio clips as "30-Second Official Preview".
  - **Personal Curation:** Star rating and one-click addition of tracks or albums to personal playlists and favorites in SQLite.

### 7.5 Video Games Catalog Module (`ui/pages/games_browse.py`)
- **External API Adapter:** Interfaced via `api/games.py` connecting to zero-cost gaming databases such as FreeToGame API, GamerPower API, or RAWG Video Games Database free tier.
- **Functional Capabilities:**
  - **Catalog Discovery:** Browse hundreds of popular PC and browser-based video games categorized by genre (MMORPG, Shooter, Strategy, MOBA, Indie) and platform (PC Windows, Web Browser).
  - **Rich Metadata Inspection:** Displays high-resolution cover artwork, title, short description, publisher, developer, release date, and official genre classifications.
  - **Minimum System Requirements:** Where provided by the API, displays system hardware requirements (OS, Processor, Memory, Graphics, Storage).
  - **Screenshot Carousel:** Displays promotional in-game screenshots with thumbnail navigation.
  - **Ratings and Want-to-Play Lists:** Integrated rating system and one-click addition to the user's "Want to Play" or "Played" lists.

### 7.6 Playable In-GUI Game Module (`ui/pages/games_chess.py` & `ui/pages/games_fireboy.py`)
The Playable In-GUI Game module fulfills the academic requirement allowing users to play an actual game inside the desktop window, not merely browse catalog metadata.

#### Technical Architecture and Implementation Options
1. **Embedded Web Engine Gameplay (`QWebEngineView`):**
   - Integrates PySide6's Chromium-based `QWebEngineView` widget directly inside `games_chess.py` and `games_fireboy.py`.
   - Loads legal, zero-cost, open-access HTML5/Canvas game engines (such as open-source JavaScript Chess or embedded Flash-emulated web classics via Ruffle/HTML5).
   - In-GUI Containment: The game canvas is strictly rendered within the Qt layout hierarchy. All keyboard and mouse input events are routed directly to the embedded view.
   - External browser spawning (via `webbrowser.open()`) is strictly prohibited.
2. **Native Qt Interactive Game Canvas (Fallback Option):**
   - Alternatively, for lightweight deployment on systems without WebEngine dependencies, incorporates a fully functional native Qt Chess or Arcade game implemented using `QGraphicsScene`, `QGraphicsView`, and custom `QGraphicsItem` subclasses.
   - The game communicates with external APIs (e.g., Stockfish chess engine API or chess puzzle APIs) to initialize boards, validate legal moves, and retrieve computational AI responses.
3. **Session Lifecycle and Telemetry:**
   - **Start Game:** Initiates game assets, begins session timer, and creates an entry in `game_sessions`.
   - **Active Gameplay:** Smooth 60 FPS rendering, responsive controls, visual move highlights, and audio sound effects.
   - **Pause / Restart:** Controls to restart match, reset board, or pause game loop.
   - **Game Over / Outcome:** Displays victory/defeat dialog, calculates match duration, and updates `game_sessions.duration_seconds` and `game_sessions.session_outcome`.

### 7.7 Shared Personal Lists and Star Ratings System (`ui/pages/my_lists.py` & `ui/components/star_rating.py`)
- **Shared Data Model:** Connects directly to `library_items` and `user_ratings` tables in SQLite, binding all media categories into a single unified personal library interface.
- **List Categories:**
  - **Favorites:** Top-rated, beloved items across all three categories.
  - **Watchlist / Playlist / Want-to-Play:** Pending media queue for future viewing, listening, or playing.
  - **Completed / Watched / Played:** Archive of consumed media.
- **Cross-Category Filtering:** Sub-tabs allow users to view "All Items", "Movies & TV", "Music", or "Games", with visual category badges on each card.
- **Granular 1–5 Star Rating:** Reusable Qt component (`StarRatingWidget`) displaying interactive golden stars. Users can click any star to record or update their rating, which immediately updates SQLite and refreshes aggregate ratings across cards.
- **Removal and Status Toggle:** Users can change list assignment or remove items with a single click, triggering smooth list re-renders.

### 7.8 Dynamic Custom Theming Engine (`theme/theme_manager.py` & `ui/pages/settings.py`)
- **Tokenized Color Architecture:**
  - `PRIMARY`: Default `#6C63FF` (vibrant purple). Used for call-to-action buttons, active navigation indicators, slider thumbs, and star highlights.
  - `SECONDARY`: Default `#FF6584` (coral pink). Used for secondary badges, tags, subtle hover accents, and alerts.
  - `BG_DARK`: `#1a1a2e` (deep navy/slate). Main window background.
  - `BG_SIDEBAR`: `#16213e` (darker blue). Sidebar background.
  - `BG_CARD`: `#1f1b2e` (elevated surface). Content card containers.
  - `TEXT_PRIMARY`: `#ffffff` (crisp white).
  - `TEXT_SECONDARY`: `#a0a0b0` (muted gray).
  - `BORDER_COLOR`: `#2a2a4a` (subtle divider borders).
- **Interactive Customization:**
  - Settings page provides interactive color swatches for Primary and Secondary colors.
  - Clicking a swatch invokes Qt's native `QColorDialog`, allowing the user to pick any RGB hex color.
  - Contrast Ratio Guard: Validates that selected colors maintain at least a 3:1 contrast ratio against the background, ensuring visual legibility.
- **Dark / Light Mode Toggle:**
  - Inverts background and text tokens (e.g., Light mode: `BG_DARK = #f5f6fa`, `BG_CARD = #ffffff`, `TEXT_PRIMARY = #2f3640`, `TEXT_SECONDARY = #718093`).
- **Persistence and Instant Compilation:**
  - Saves hex values and theme mode to SQLite `user_settings`.
  - Re-injects the compiled QSS into `QApplication.instance().setStyleSheet()` in real time. The entire UI updates instantly without requiring an application restart.

## 8. User Experience, UI Components, and QSS Styling System

EntertainX provides a cohesive desktop experience following modern Human Interface Guidelines, sharing a unified visual language across all sections.

### 8.1 Visual Hierarchy and Layout Guidelines
- **Consistent Grid Systems:** Content items in Movies, TV Shows, Music, and Games are presented in responsive grid layouts within `QScrollArea` containers. Grid columns dynamically adjust based on window width (e.g., 3 columns at 1024x768, 5 columns at 1920x1080).
- **Typography Standards:** Typography utilizes standard system fonts (`Segoe UI` on Windows). Headers use bold weights (20–24px), section titles use semibold weights (15–17px), and body metadata uses regular weights (12–13px).
- **Spacing:** Standardized 8-pixel grid spacing units (8px, 16px, 24px, 32px) maintain clean layout rhythm.

### 8.2 Reusable UI Component Library (`ui/components/`)
To maximize code reuse and eliminate duplicated GUI logic, EntertainX establishes a reusable component suite:
1. `ContentCard`: A versatile card container widget displaying thumbnail artwork, title label, subtitle/year, rating badge, and interactive hover states. Used uniformly across Movies, TV Shows, Music, and Video Games.
2. `StarRatingWidget`: An interactive 5-star rating control supporting click selection and fractional display, emitting a `rating_changed(int)` signal.
3. `SearchBar`: A styled search input box with embedded magnifying glass icon, clear button, and built-in keystroke debouncing.
4. `LoadingSpinner`: A smooth graphical loading indicator displayed during asynchronous API network requests.
5. `EmptyStateWidget`: A friendly visual placeholder displayed when search queries return zero results or when a personal list is empty, offering helpful guidance.

### 8.3 State Management and Thread-Safe UI Updates
To guarantee a responsive user interface that never blocks:
- All external HTTP calls are dispatched to background threads via `QThreadPool` using custom `Worker(QRunnable)` classes.
- Worker threads emit signals (`signals.result`, `signals.error`, `signals.finished`) upon task completion.
- The main GUI thread connects to these signals to update widgets, populate cards, and hide loading spinners safely.

---

## 9. Implementation Roadmap and Development Phases

Development proceeds systematically through eight distinct phases:

### Phase 1: Environment Setup, Database Architecture, and Salted Authentication (Complete)
- Configured Python 3.12 virtual environment (`venv`) with PySide6 and testing dependencies.
- Implemented `database/db.py` with foreign key enforcement and automatic schema creation.
- Built `auth/auth_manager.py` implementing PBKDF2-HMAC-SHA256 password hashing with 32-byte salts and constant-time verification.
- Developed `ui/login_window.py` featuring tabbed registration and login forms with full input validation.
- Validated with unit tests in `tests/test_db.py` and `tests/test_auth.py`.

### Phase 2: Unified Main Navigation Shell, Sidebar, and Sub-Tab Stacks (Complete)
- Implemented `ui/main_window.py` providing the master application shell.
- Built `ui/sidebar.py` with category buttons (Video, Music, Games, My Lists, Settings) and active category state tracking.
- Developed `ui/content_area.py` featuring a dynamic sub-tab navigation bar and `QStackedWidget` viewport.
- Created styled placeholder pages for all future functional modules.
- Created initial `theme/theme_manager.py` with base tokenized dark QSS.
- Validated navigation transitions with automated tests in `tests/test_navigation.py`.

### Phase 3: Movies and TV Shows API Adapter and Browsing UI
- Implement `api/movies.py` connecting to TMDB or TVMaze API with polite rate-limiting.
- Build grid-based discovery and live search views in `ui/pages/video_movies.py` and `ui/pages/video_tvshows.py`.
- Implement asynchronous image loading and two-tier caching for movie posters.
- Develop rich media detail modal with synopsis, cast credits, and trailers.

### Phase 4: Music and Audio Discovery Module and Audio Playback Integration
- Implement `api/music.py` connecting to iTunes Search API or Deezer Free API.
- Build search and discovery interface in `ui/pages/music.py` for artists, albums, and songs.
- Implement 30-second legal audio preview streaming using Qt's `QMediaPlayer`.
- Integrate star rating and playlist addition controls.

### Phase 5: Video Games Catalog Integration and Metadata Browser
- Implement `api/games.py` connecting to FreeToGame API or RAWG free tier.
- Build game discovery and filtering UI in `ui/pages/games_browse.py`.
- Render system requirements, screenshots carousel, and platform indicators.

### Phase 6: Playable In-GUI Game Integration
- Integrate embedded HTML5/Canvas interactive gameplay via `QWebEngineView` in `ui/pages/games_chess.py` and `ui/pages/games_fireboy.py`.
- Implement alternative native Qt interactive game engine as an accessible fallback.
- Integrate game session tracking with `game_sessions` table in SQLite.
- Verify zero-cost compliance and strictly prevent external browser popups.

### Phase 7: Shared Personal Lists, Custom Star Ratings, and Local Library Management
- Implement `ui/pages/my_lists.py` connecting to `library_items` and `user_ratings` tables.
- Build cross-category filtering for Favorites, Watchlist, and Completed items.
- Implement reusable `StarRatingWidget` and real-time rating updates.

### Phase 8: Dynamic Color Theming, Dark/Light Mode Engine, and Comprehensive Polish
- Implement full `QColorDialog` interactive color pickers in `ui/pages/settings.py`.
- Build dynamic QSS compilation engine supporting custom Primary and Secondary colors.
- Add Dark Mode and Light Mode switching with contrast ratio validation.
- Conduct complete integration testing, security scanning, and documentation finalization.

---

## 10. Comprehensive Acceptance Criteria (Granular 40-Point Matrix)

To establish clear, objective verification gates, EntertainX defines 40 granular acceptance criteria derived directly from `EntertainX_GOAL.md`:

### 10.1 Setup and Authentication (Criteria 1–6)
1. **Startup:** The application launches cleanly from a virtual environment without errors using `python main.py`.
2. **Registration:** A new user can successfully register with username, email, and password.
3. **Duplicate Prevention:** Registration rejects duplicate usernames and email addresses with clear feedback.
4. **Credential Hashing:** Passwords are saved only as PBKDF2-HMAC-SHA256 hashes with unique 32-byte salts; plain-text passwords never enter SQLite.
5. **Login Validation:** Valid credentials log the user in; invalid credentials display generic non-leaking error messages.
6. **Session Isolation:** Logout clears all session memory and blocks access to account-protected views.

### 10.2 Unified GUI and Movies/TV Shows (Criteria 7–10)
7. **Single Window:** All views exist in one unified GUI window sharing a persistent navigation sidebar.
8. **Movie/TV Retrieval:** The Movies & TV section retrieves content from an approved zero-cost API.
9. **Search & Browse:** Users can browse popular titles, execute keyword searches, and view rich details.
10. **Entity Distinction:** Movies and TV shows are visually distinguished with accurate type-specific metadata.

### 10.3 Music and Audio (Criteria 11–13)
11. **Music Retrieval:** The Music section retrieves artist, album, and track data from an approved zero-cost API.
12. **Metadata Presentation:** Cover artwork, artist names, album titles, and track lengths render accurately.
13. **Audio Previews:** Legal 30-second previews play smoothly within the GUI; full-song paid streaming is not promised.

### 10.4 Video Games Catalog (Criteria 14–16)
14. **Game Information:** The Video Games catalog retrieves titles, genres, and metadata from an approved free API.
15. **Detail Inspection:** Game descriptions, screenshots, and system requirements display correctly.
16. **Feature Separation:** The catalog is clearly separated from the interactive playable game feature.

### 10.5 Playable Game Inside the GUI (Criteria 17–24)
17. **Playable Execution:** A logged-in user can start and play a real game inside the EntertainX GUI.
18. **API-Supported Session:** Starting the game initiates an API-backed session or asset retrieval flow.
19. **In-GUI Containment:** Gameplay renders strictly inside the application window; no external browser is opened.
20. **Functional Controls:** Keyboard and mouse controls respond immediately during active gameplay.
21. **Lifecycle States:** Start, active play, pause, game-over, and restart states operate smoothly.
22. **Fault Resilience:** Network drops or loading errors show clear recovery options without crashing the app.
23. **Zero-Cost Terms:** The embedded game integration strictly complies with zero-cost and licensing terms.
24. **No Substitution:** The playable game cannot be replaced with a static trivia quiz without explicit approval.

### 10.6 Custom Primary and Secondary Theming (Criteria 25–29)
25. **Color Pickers:** Users can choose custom Primary and Secondary colors using native color dialogs.
26. **Global Application:** Theme adjustments apply uniformly across all tabs, buttons, cards, and dialogs.
27. **Persistence:** Theme colors persist per user account in SQLite and reload automatically on login.
28. **Sensible Defaults:** Sensible default colors (`#6C63FF` and `#FF6584`) are provided with a Reset button.
29. **Non-Corrupting:** Canceling color pickers does not corrupt active or saved themes.

### 10.7 Personal Library and Shared Lists (Criteria 30–33)
30. **Universal Saving:** Users can save/remove items from Movies, TV, Music, and Games into personal lists.
31. **Local Persistence:** All personal list selections persist in SQLite across application restarts.
32. **User Isolation:** Personal collections are strictly partitioned by user account.
33. **Metadata Mapping:** Saved entries store external provider IDs, avoiding entire catalog duplication.

### 10.8 Zero-Cost Architecture and Compliance (Criteria 34–40)
34. **No Billing:** Every required feature operates with $0 in API fees without payment card verification.
35. **No Expiring Trials:** No functionality depends on time-limited commercial trial accounts.
36. **Local Independence:** Authentication, theming, and lists operate without requiring cloud backends.
37. **Documentation:** `README.md` documents every provider's zero-cost terms, rate limits, and attribution.
38. **Polite Throttling:** Rate-limiting handles HTTP 429 politely without switching to paid endpoints.
39. **Documented Checks:** All API candidate selections are pre-verified against official documentation.
40. **Transparent Replacement:** Unviable API providers are replaced only after formal approval.

---

## 11. Definition of Done Checklist (10 Strict Categories)

Before EntertainX can be certified as complete, every item in this 10-category checklist must be verified and true:

### 1. Authentication System (Mandatory)
- [x] User Registration with username, email, and password validation.
- [x] User Login with secure credential verification.
- [x] Generic, non-leaking error messages for invalid credentials.
- [x] Passwords properly salted with 32-byte salts and hashed using PBKDF2-HMAC-SHA256.
- [x] Functional Logout clearing session memory and redirecting to login.
- [x] Session state maintained across all views until explicit logout.

### 2. Application Structure and Navigation
- [x] Single unified application shell with persistent left sidebar navigation.
- [x] Clear category separation: Video (Movies & TV), Music, Games, My Lists, Settings.
- [x] Dynamic sub-tab navigation bar with active category memory.
- [x] Smooth transitions between pages without visual flicker or layout deformation.

### 3. Movies and TV Shows Section
- [ ] Real-time search and discovery powered by an approved zero-cost API.
- [ ] Popular and trending content grids populated automatically on load.
- [ ] Rich detail view displaying poster, plot overview, genres, cast, and release info.
- [ ] Visual distinction between films and television series.
- [ ] User star rating (1–5 stars) saved to local SQLite.
- [ ] One-click addition to personal lists (Favorites, Watchlist, Watched).

### 4. Music Section
- [ ] Search functionality for artists, albums, and individual song tracks.
- [ ] High-resolution album artwork, artist names, release dates, and track durations.
- [ ] Legal 30-second audio preview playback within the GUI.
- [ ] User star rating (1–5 stars) saved to local SQLite.
- [ ] One-click addition to personal playlists and favorites.

### 5. Games Section (Catalog)
- [ ] Search and discovery of video game titles across genres and platforms.
- [ ] Rich metadata display including cover art, publisher, genre, and system requirements.
- [ ] User star rating (1–5 stars) and addition to Want-to-Play lists.
- [ ] In-game screenshots carousel.

### 6. Playable Game In-GUI System
- [ ] In-GUI interactive playable game execution (via `QWebEngineView` or native Qt engine).
- [ ] Game session initiated via API-supported flow.
- [ ] Gameplay contained strictly within the desktop window; no external browser popups.
- [ ] Full keyboard and mouse interactive controls with real-time graphical feedback.
- [ ] Start, active play, pause, game-over, and restart states fully operational.

### 7. Personal Lists System (Shared Cross-Category)
- [ ] Three standardized list categories: Favorites, Watchlist/Want-to-Play, and Completed/Played.
- [ ] Unified interface allowing browsing of all saved items or filtering by media category.
- [ ] Persistent storage in SQLite partitioned by user account.
- [ ] Instant item removal and list status toggling.

### 8. Dynamic Theming System
- [ ] User-selectable Primary and Secondary colors via native `QColorDialog`.
- [ ] Dark Mode and Light Mode toggle options.
- [ ] Theme preferences saved per user in SQLite and restored on login.
- [ ] Instant runtime QSS compilation updating all widgets without restarting.

### 9. User Experience and Polish
- [ ] Asynchronous background loading preventing GUI freezes.
- [ ] Visual loading spinners and debounced search inputs.
- [ ] Comprehensive error handling for network dropouts, rate limits, and empty states.
- [ ] High-contrast, visually cohesive Qt styling matching modern desktop aesthetics.

### 10. Code Quality and Security
- [ ] Clean modular architecture separating UI, API adapters, database, and auth.
- [ ] Reusable UI components (`ContentCard`, `StarRatingWidget`, etc.).
- [ ] No hardcoded secrets or plain-text passwords; sanitized `.env.example`.
- [ ] Comprehensive automated test suites with high code coverage.

---

## 12. Fitness Function and 100-Point Evaluation Rubric

As mandated by `AGENTS.md`, EntertainX must achieve an evaluation score of **≥ 92 out of 100 points** to satisfy the project Definition of Done. The scoring model is weighted across nine comprehensive categories:

| Evaluation Category | Maximum Points | Target Minimum | Key Assessment Criteria |
| :--- | :---: | :---: | :--- |
| **1. Authentication & Security** | 15 | 15 | PBKDF2-HMAC-SHA256, 32-byte salt, timing-attack protection, foreign keys, input validation. |
| **2. App Structure & Navigation** | 12 | 12 | Unified PySide6 window, sidebar navigation, sub-tabs, stacked widget, session preservation. |
| **3. Movies & TV Shows Section** | 15 | 14 | Zero-cost API integration, trending feeds, live search, rich details, movie/TV distinction. |
| **4. Music & Audio Section** | 13 | 12 | Track/artist search, metadata display, 30s audio previews, zero-cost compliance. |
| **5. Games Section (Catalog & Playable)** | 13 | 12 | Metadata catalog plus fully interactive playable game inside the GUI window. |
| **6. Shared Personal Lists System** | 8 | 8 | Cross-category unified library, Favorites, Watchlist, Completed, SQLite persistence. |
| **7. Dynamic Custom Theming** | 10 | 10 | Primary/Secondary color selection, QColorDialog, Dark/Light modes, runtime QSS recompile. |
| **8. UI/UX Polish & Consistency** | 8 | 7 | Asynchronous worker threads, loading states, empty states, error handling, modern typography. |
| **9. Code Quality & Architecture** | 6 | 6 | Clean directory structure, adapter pattern, reusable widgets, tests passing, `.env.example`. |
| **Total Evaluation Score** | **100** | **≥ 92** | **Project Certification Threshold: ≥ 92 Points** |

---

## 13. Quality Assurance, Automated Testing, and Verification Plan

EntertainX maintains a quality assurance regimen combining automated unit tests, headless GUI verification, and acceptance checks.

### 13.1 Automated Test Suites (`tests/`)
1. `tests/test_db.py`: Validates SQLite database initialization, table creation, foreign key enforcement, unique constraints, and schema idempotency.
2. `tests/test_auth.py`: Tests password hashing, salt uniqueness, successful registration, duplicate rejection, valid login, invalid login rejection, and session state persistence.
3. `tests/test_navigation.py`: Uses `pytest-qt` to verify headless sidebar clicks, category switching, sub-tab transitions, category history memory, and logout signal dispatching.
4. `tests/test_api_adapters.py`: Tests API adapter response mapping, HTTP timeout handling, and fallback behavior using mocked network payloads.
5. `tests/test_theming.py`: Verifies QSS template compilation, token substitution, color validation, and database setting restoration.
6. `tests/test_lists.py`: Validates cross-category library insertions, duplicate prevention, and deletion cascades.

### 13.2 Execution Command
Execute tests via pytest runner:
```bash
pytest -v --tb=short tests/
```

---

## 14. Risk Assessment, Contingency Management, and Project Approval

### 14.1 Technical Risk Matrix
- **Risk 1: External API Deprecation or Outage:** A selected free API provider abruptly modifies its endpoint schema or experiences server downtime.
  * *Mitigation:* API adapters encapsulate all provider-specific parsing. If an API becomes permanently unavailable, a replacement zero-cost adapter can be plugged in without altering GUI or database code.
- **Risk 2: Rate Limit Exhaustion During Evaluation:** Multiple rapid test runs exceed public API hourly request quotas.
  * *Mitigation:* The two-tier local cache (memory + disk) intercepts repeated queries, serving cached responses immediately.
- **Risk 3: WebEngine Dependency Overhead:** Some Windows environments may lack Chromium runtime dependencies required by `QWebEngineView`.
  * *Mitigation:* The playable game architecture supports both embedded WebEngine games and pure native Qt interactive canvas implementations.

### 14.2 Final Sign-Off and Commitment
EntertainX represents software engineering excellence, user privacy, and academic rigor, delivering a cohesive multi-media desktop application that fulfills all capstone requirements for ITL313-18.