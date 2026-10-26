# GOAL.md — EntertainX

> **Document status:** Revised project goal. Course requirements, owner-confirmed requirements, implementation recommendations, and pending decisions are identified separately.
> **Course:** ITL313-18 (SIA 2 LAB) — Final Term Mini Project
> **Selected category:** Media and Entertainment
> **Requested content areas:** Movies and TV Shows; Music and Audio; Video Games
> **API providers:** Not selected yet; must meet the zero-cost requirement and remain replaceable
> **Last updated:** 2026-10-25

## 1. Project Goal

Develop **EntertainX**, a Python desktop application that combines **Movies and TV Shows, Music and Audio, and Video Games in one unified GUI**. Registered users should be able to browse and search entertainment content from official external APIs, view supported details, customize the application's primary and secondary theme colors, and manage a personal favorites/library stored locally. EntertainX must also let the user **start and actually play a game inside the same application GUI through an API-based integration**. It must not merely display video-game information or replace the playable-game requirement with a quiz without the project owner's approval.

The application will demonstrate desktop GUI development, registration and local authentication, SQLite database operations, salted password hashing with Python's built-in `hashlib`, REST API integration, multi-category navigation, interactive gameplay, and persistent per-user preferences.

The application must meet the zero-cost requirement for noncommercial academic use: no API fees, payment card, billing activation, paid proxy, paid hosting, paid authentication, or expiring trial may be required for any required feature. API providers are intentionally **not fixed in this document**. The project owner may select or change suitable free providers; the implementation must keep provider-specific code modular so a provider can be replaced without rebuilding the entire application.

Implement the foundation, authentication, unified GUI, theme customization, API integrations for the three content areas, and playable in-GUI game in manageable phases. Add the favorites/personal library after the core features are working and tested.

## 2. Requirement Sources and Decision Status

This document separates the supplied assignment brief from the project owner's decisions and from implementation recommendations.

### 2.1 Requirements stated in the assignment brief

The supplied **ITL313-18 (SIA 2 LAB) Final Term Lab Activities and Mini Project — Project Overview** specifies:

- The project must use a Python GUI. The brief lists Tkinter and PyQt/PySide as GUI options.
- The project must include a login system with user authentication.
- SQLite is identified for user data storage.
- Passwords must be salted and hashed using Python's built-in `hashlib`; plain-text passwords must never be stored.
- Media and Entertainment examples listed in the brief are Movies and TV Shows, Music and Audio, and Video Games.
- The brief allows a group of one to three members.

**Assignment-scope check:** The brief uses wording about choosing only one function and then lists Movies and TV Shows, Music and Audio, and Video Games under Media and Entertainment. EntertainX's owner has requested all three content areas. Confirm with the instructor that using all three subareas under the single Media and Entertainment category is acceptable. Until confirmed, do not silently remove any of the three requested areas; document this as an approval item.

### 2.2 Owner-confirmed decisions and requirements

- **Application name:** EntertainX.
- **Application type:** Python desktop application with one unified GUI.
- **Entertainment scope:** All three areas in the same application: Movies and TV Shows, Music and Audio, and Video Games.
- **GUI preference:** PySide6 (Qt for Python). The assignment lists Tkinter and PyQt/PySide; PySide6 is the current Qt for Python binding under LGPL and directly matches the approved PyQt/PySide option.
- **Authentication fields:** Username, email, and password for registration; username and password for login unless a later requirement changes this.
- **Local storage:** SQLite for local accounts, appearance preferences, and the personal favorites/library. No hosted authentication or cloud database is required.
- **Password security:** Salted password hashing with Python's built-in `hashlib` as required by the brief.
- **API selection:** No specific API provider is mandatory. Providers may be selected, replaced, or separated by content category, provided all required functionality meets the zero-cost requirement and provider changes are approved by the project owner.
- **Playable game:** The user must be able to initiate and play an actual game inside the EntertainX GUI through an API-based integration. A static game catalog, an external browser launch, or a movie trivia quiz alone does not satisfy this requirement.
- **Custom theme colors:** Users can choose separate primary and secondary colors. Save these preferences per local account and restore them on later login.
- **Favorites/personal library:** Include after the core features are implemented and tested.
- **Zero-cost requirement:** Every required feature must work for $0 in API fees, without billing activation, a payment card, paid services, paid proxies, paid hosting, paid authentication, time-limited trials, promotional credits, or automatic paid upgrades.

### 2.3 Important distinction: game catalog vs. playable game

EntertainX has two separate game-related requirements:

1. **Video Games content area:** Browse or search video-game information from a suitable API, such as available titles, descriptions, genres, platforms, and other supported metadata.
2. **Playable game inside the GUI:** A user must be able to start and interact with a real playable game within the same EntertainX application window. The game integration must use an API call or an API-supported launch/load flow, and the actual gameplay controls must work inside EntertainX.

A video-game metadata API normally returns information about games; it may not provide a playable game. Before implementation, verify that the selected no-cost provider actually supports gameplay or returns game content that the application is legally and technically allowed to embed. A compatible embedded game view may require `QWebEngineView` or another Qt component. Do not assume PySide6 alone can display arbitrary web games.

If no provider supports an actual playable in-GUI game while meeting all zero-cost and usage requirements, stop and present feasible alternatives to the owner before implementation. Do not silently substitute a quiz, launch an external browser, use a paid service, or claim that a game is playable when only its metadata is shown.

### 2.4 Assumptions and implementation recommendations

The following are implementation recommendations rather than explicit requirements from the assignment:

- Develop and demonstrate on Windows unless the owner specifies another operating system.
- Use one application shell with shared navigation and consistent styling for Movies/TV, Music/Audio, Video Games, Play Game, Settings/Appearance, and Favorites/Library.
- Use multiple API providers if no single provider can reliably cover all content areas. The three content areas do not have to use the same provider.
- Add a provider-adapter/service layer so API URL formats, authentication methods, response fields, and attribution details do not spread throughout GUI code.
- SQLite stores account data, preferences, and saved references to external content. It should not duplicate whole provider catalogs unless caching a small amount of data is needed and allowed.
- Start with default theme colors, then let users customize the primary and secondary colors through color pickers.
- Use a modular architecture and a minimal set of dependencies. Add `QWebEngineView` only if the selected playable-game integration requires it and the instructor/owner accepts the approach.
- The application is for a noncommercial academic demonstration; it is not intended to be a streaming service or game-hosting platform.

## 3. Problem and Purpose

People often need separate services to discover films and television shows, learn about music, look up video games, and play a small game. EntertainX aims to bring these entertainment areas together in a single desktop GUI while demonstrating API integration and basic desktop application engineering.

The application should remain understandable for a student developer and demonstrable in class. Its interfaces, data handling, authentication, and game integration should be separated enough that one provider or feature can be changed without requiring a complete rewrite.

## 4. Intended Users

- **Registered user:** Registers with a username, email, and password; logs in; explores all three entertainment content areas; plays the supported in-GUI game; customizes the appearance; and manages favorites once that feature is implemented.
- **Logged-out user:** Can access registration and login. Account-specific features, personalized theme settings, saved library, and gameplay are available after successful login unless an explicitly approved requirement says otherwise.

The initial version does not require multiple permission levels, an administrator dashboard, or synchronization between devices.

## 5. Proposed Technology Stack

- **Language:** Python.
- **GUI:** PySide6 (Qt for Python, LGPL). Directly listed in the assignment brief under PyQt/PySide. No instructor approval needed.
- **Database:** SQLite through Python's built-in `sqlite3` module.
- **Password hashing:** Python's built-in `hashlib`, using `hashlib.pbkdf2_hmac` with a unique cryptographically secure random salt for each account. Store the password hash, salt, and parameters required for verification. Never store the original password or use a single unsalted fast hash for password storage.
- **HTTP requests:** `requests` or another suitable no-cost Python HTTP library.
- **Image handling:** Pillow if needed, plus Qt's built-in `QPixmap`/`QImage` for display of posters, album artwork, game cover art, or other API images.
- **Theme color selection:** `QColorDialog` or a compatible color picker from the Qt framework.
- **API providers:** To be selected after checking official documentation, zero-cost eligibility, terms, required credentials, rate limits, data availability, and compatibility with the in-GUI game requirement.
- **Playable-game display:** Decide after choosing a feasible game integration. Possible approaches include drawing gameplay with native Qt widgets from API-backed game actions, or embedding officially supported game content via `QWebEngineView`. Choose only after checking technical feasibility and terms.

Keep dependencies as small as practical. Do not add a web server, cloud database, separate account service, paid API proxy, or extra GUI framework unless a confirmed requirement and approved design justify it.

## 6. Core Features — Implement Before Favorites

### 6.1 Registration

- Provide a registration form with username, email, and password fields.
- Validate required fields and apply reasonable username, email, and password rules.
- Reject duplicate usernames and duplicate email addresses using database constraints and clear messages.
- Store the username, email, password hash, salt, and a creation timestamp as appropriate in SQLite. Never store the original password.
- Do not claim that an email address has been verified. Email verification and password-reset emails are outside the initial scope unless later required.

### 6.2 Login and Logout

- Allow a registered user to log in with username and password.
- Verify the submitted password using the same password-derivation algorithm and parameters used at registration.
- Reject invalid credentials with a useful general message that does not reveal whether a username exists.
- Provide logout that clears the active session state and returns the user to the login screen.
- Prevent access to account-specific sections, the playable game, personalized appearance settings, and the saved library while logged out.

**Authentication boundary:** Authentication is local to the computer and SQLite database where EntertainX runs. It does not provide centralized online identity, multi-device synchronization, or production-grade cloud account security. Do not describe it as such.

### 6.3 Movies and TV Shows

- Connect to a selected, approved, officially available no-cost API provider for movies and TV shows.
- Let users browse and search available films and television shows.
- Clearly distinguish movies from TV shows.
- Display details supported by the selected provider, such as title, poster, overview, release date/first-air date, genre, rating, cast, or other relevant metadata when available.
- Handle missing fields and unsupported endpoints gracefully.
- Do not stream full movies or TV episodes or download copyrighted media as part of the initial project.

### 6.4 Music and Audio

- Connect to a selected, approved, officially available no-cost API provider for music/audio data.
- Let users discover or search for supported items such as artists, tracks, albums, or genres, depending on the provider's capabilities.
- Display available metadata such as title, artist, album, artwork, release information, genre, or duration.
- If official free audio previews or playable audio are available and the provider's terms permit them, they may be added as an approved enhancement. Do not assume the API includes free full-track playback, and do not bypass subscriptions, DRM, geographic restrictions, or provider access controls.
- If audio playback is not available at $0 under acceptable terms, keep music discovery and details functional and clearly document that limitation. Do not silently depend on a paid service.

### 6.5 Video Games Catalog

- Connect to a selected, approved, officially available no-cost API provider for video-game information.
- Let users browse or search game titles and view the information the provider actually supports, such as description, genre, platform, release date, rating, publisher, or cover art.
- Clearly distinguish the Video Games catalog from the separate Play Game feature described below.
- Do not represent a game as playable simply because the API returns a title, image, metadata, or external URL.

### 6.6 Playable Game Inside EntertainX

The app must include a **Play Game** area that lets the logged-in user play an actual game within the EntertainX GUI. This is a required feature, not an optional future enhancement.

- Starting a game must initiate the approved API call or API-supported load/session flow.
- The selected solution must support real gameplay, not only game metadata or a link to a game page.
- Render gameplay in the same application window. Do not launch the operating system's default browser or a separate external game window.
- The user must be able to interact with the game through functional controls (such as keyboard or mouse actions) and see the game respond.
- Provide appropriate loading, start, active-play, completion/game-over, and retry/restart states as supported by the selected game.
- Handle unavailable service, timeouts, rejected embedding, expired game sessions, and other failures with clear messages and a safe return/retry path.
- Confirm that the provider permits the intended embedded or API-supported use, especially in a noncommercial desktop application.
- Check whether PySide6/Qt can support the chosen integration. If `QWebEngineView` or another additional component is required, document and test that dependency before adopting it.
- Do not download or execute arbitrary code returned by an API. Do not disable browser security controls or embed content in a way that bypasses the provider's restrictions.
- If the required API-driven in-GUI game cannot be achieved within the zero-cost rules, pause and present technically honest alternatives for owner approval. Do not replace it with a local quiz without approval.

### 6.7 Unified Navigation and GUI

All required content areas must exist in the **same EntertainX application and shared GUI**, not as separate unrelated applications.

- Provide shared navigation for Movies/TV Shows, Music/Audio, Video Games, Play Game, and Settings/Appearance.
- Add Favorites/Library navigation when that feature is implemented.
- Keep the same login session and theme preferences when switching sections.
- Use shared design components and consistent spacing, typography, loading states, and error messages.
- Avoid creating separate independent launchers or windows for each content area.

### 6.8 User-Selectable Primary and Secondary Theme Colors

Users must be able to customize the application's primary and secondary theme colors from a Settings or Appearance section.

- Provide separate controls for choosing the **primary color** and **secondary color**, using a color picker. Display the selected hexadecimal color values where practical.
- Preview or immediately apply changes throughout the GUI.
- Define a consistent use for each color. For example, use primary for main action buttons and active navigation, and secondary for supporting accents, tags, cards, or secondary actions.
- Keep text, focus states, selections, and feedback readable. Use suitable foreground colors or warn when a combination has poor contrast.
- Provide sensible defaults and a way to restore them.
- Save both selected colors in SQLite, associated with the currently logged-in user, and restore them at the next login/application start.
- Validate values before saving. Canceling a picker must not corrupt the current or saved theme.
- Theme changes should update the current GUI without requiring an application restart.
- The required theme customization is limited to primary and secondary colors; do not expand it into a complete editor for fonts, layout, and every widget style unless separately approved.

## 7. Favorites / Personal Library — Add After Core Features

Favorites are planned but must not delay the core requirements: authentication, the unified GUI, basic discovery/search for all three content areas, the in-GUI playable game, and theme customization.

After the core features are working and tested:

- Let a logged-in user save and remove supported content from Movies/TV Shows, Music/Audio, and Video Games, subject to what the providers return.
- Provide one personal library/favorites screen in the same GUI. Filters for content type may be used.
- Associate every saved item with the correct local user.
- Store provider identifiers and the content type rather than copying entire provider catalogs.
- Keep provider identity along with the external item ID because different APIs may use different ID spaces.
- Prevent duplicate favorites for the same user, provider, content type, and external item ID.
- Retrieve up-to-date details from the provider when practical, while handling content that has been removed or is temporarily unavailable.

If time is limited, complete and test the core application before implementing favorites. Report any incomplete features honestly.

## 8. API Provider Selection, Modifiability, and Zero-Cost Requirements

### 8.1 Provider-neutral design

No specific entertainment API provider is selected or permanently required by this goal. The project owner may identify candidate free APIs for Movies/TV Shows, Music/Audio, Video Games, and the playable-game integration. Different categories may use different providers if necessary.

Before integrating a provider:

- Review its official documentation and terms.
- Verify that its required endpoints and data actually support the planned feature.
- Verify that all required use is officially available at $0 without billing activation, a payment card, a paid subscription, paid proxy, trial, or promotional credits.
- Check authentication/key requirements, rate limits, attribution, licensing, embed policies, and any restrictions for desktop applications or academic demonstrations.
- Record the provider, relevant endpoints, conditions, and date checked in `README.md` or another project document.
- Obtain owner approval before locking in a provider or switching from one already approved.

Use a provider/service adapter for each API area. GUI components must call EntertainX service functions rather than build provider-specific URLs or parse provider-specific JSON directly. Keep API base URLs, request methods, response mapping, authentication, and provider attribution inside the relevant adapter. This allows an approved provider to be replaced without rewriting the whole GUI, database, or application navigation.

Do not force all content categories to use one provider if no single no-cost provider serves all required needs. Conversely, do not add unnecessary APIs when one provider can safely and legally cover multiple categories.

### 8.2 Zero-Cost Requirement

EntertainX is a noncommercial academic project and must operate with **$0 in API fees for every required feature**. Do not assume that a provider qualifies just because it advertises a free tier.

- Use only officially available no-cost API access for required features.
- Do not use paid subscriptions, paid API proxies, services requiring billing activation, time-limited trials, promotional credits, automatic paid upgrades, or any required feature that needs a payment card.
- Do not introduce paid hosting, cloud databases, or paid authentication services.
- Keep registration, login, authentication data, theme preferences, and the personal library/favorites in local SQLite. These functions must not require a hosted service.
- Respect API rate limits, attribution requirements, copyright, licensing, and provider terms.
- When throttled, show a useful message and wait/retry responsibly. Never automatically switch to a paid provider, plan, proxy, or endpoint.
- Do not scrape websites as a substitute for authorized API access or bypass access controls to avoid payment.
- If a provider changes its terms, removes free access, requires billing activation, or no longer supports a required feature, pause the affected integration and propose an approved no-cost replacement before changing the implementation.
- Never silently replace an API provider or switch to a paid alternative.
- The `README.md` must document every selected provider's free-use conditions, important limits, attribution requirements, and feature coverage.

#### Zero-Cost Acceptance Criteria

1. Every required API feature can be used without billing activation or entering a payment card.
2. No required feature depends on a time-limited trial, promotional credits, or automatic paid upgrade.
3. Registration, login, local theme settings, and the personal library work without hosted authentication or a cloud database.
4. `README.md` documents each API provider's free-use conditions, limits/rate limits where applicable, and attribution/licensing requirements.
5. Rate limiting produces a useful message and responsible retry/wait path; the app never silently switches to a paid service.
6. The playable game is confirmed to work within the GUI and comply with the selected provider's no-cost and embedding/API terms.
7. If a provider fails any zero-cost condition or does not support its required feature, work pauses until a suitable replacement is proposed and approved.

## 9. Local Database and Data Boundaries

SQLite stores EntertainX's local account data and preferences, not full external media catalogs or hosted-service accounts.

### 9.1 Users table — proposed fields

- `id`: local primary key.
- `username`: unique username.
- `email`: unique email address.
- `password`: cryptographically secure per-user salt derived password value.
- `created_at`: account creation timestamp, if useful.

### 9.2 User settings table — proposed fields

- `user_id`: primary key and foreign key to the local user.
- `primary_color`: validated color value, such as hexadecimal RGB.
- `secondary_color`: validated color value.
- `updated_at`: last-update timestamp, if useful.

### 9.3 Favorites table — add after core features

Suggested fields:

- `id`: local primary key, if needed.
- `user_id`: reference to the user who saved the item.
- `provider_key`: identifier for the approved provider.
- `content_type`: movie, TV show, music/artist/album/track, or video game, as appropriate.
- `external_item_id`: provider's ID for the item.
- `saved_at`: timestamp, if useful.

Use parameterized SQL queries, uniqueness constraints for usernames and email addresses, and a uniqueness rule to prevent duplicate favorites for the same user/provider/content type/external ID. Configure foreign keys appropriately. Validate any provider or game data before storing or displaying it.

## 10. GUI and Usability Goals

- Provide registration and login screens.
- After login, show one EntertainX home/dashboard with navigation to Movies/TV Shows, Music/Audio, Video Games, Play Game, and Settings/Appearance.
- Provide a single consistent browsing and details experience across categories where practical, while respecting the different fields each provider supports.
- Keep the actual playable game inside the main application window.
- Preserve the logged-in user's session and selected theme when navigating between sections.
- Include loading indicators, empty states, offline states, API-error messages, and retry actions.
- Keep the interface understandable for a beginner to explain during a class demonstration.
- Visual polish must not delay core functionality, testing, or reliability.

## 11. Security, Privacy, and Reliability

- Follow the assignment's password hashing and salting requirement with `hashlib`.
- Generate a cryptographically secure, unique salt for each account and store the parameters needed for verification.
- Validate user inputs and use parameterized SQL queries.
- Never log or display passwords, salts, password hashes, or secret API credentials.
- Keep `.env` and other secret-bearing files out of version control; use placeholder values only in `.env.example`.
- Understand that API credentials distributed with a desktop app may be extractable. Environment variables keep configuration separate from source but do not fully protect a credential shipped to users.
- Keep favorites and appearance preferences associated with the correct local account.
- Treat API responses and embedded game content as external/untrusted input; handle missing or unexpected data defensively.
- Do not download and execute arbitrary code obtained from API responses.
- Follow the game provider's embedding/security requirements. Do not disable security controls or bypass restrictions to force a game to load.
- Run network requests without freezing the GUI; use an appropriate background-task approach and safely update GUI elements on the main thread.
- Recover from API failures with useful messages instead of terminating the application.
- Do not describe local SQLite authentication as centralized online authentication or multi-device account security.

## 12. Out of Scope for the Initial Version

Unless the owner and instructor approve a change, do not implement:

- A web application or separate mobile application in addition to the desktop GUI.
- Paid subscriptions, payments, paid APIs/proxies, paid hosting, paid authentication, or a cloud database.
- Full movie/TV streaming or downloads.
- Full music streaming or music downloads unless an approved provider explicitly supports legal no-cost playback and it is separately approved.
- Downloading copyrighted games, distributing game executables, or executing arbitrary code returned by an API.
- Launching the playable game in the system's external browser or a separate unrelated application window.
- Social feeds, chat, comments, or following other users.
- Administrator panels or role-based administration.
- Cross-device account synchronization or a hosted identity system.
- Email verification, email-based password recovery, or one-time passwords.
- Complex recommendation engines, AI-generated reviews, or machine-learning features.
- An elaborate theme editor beyond primary and secondary color selection.
- Additional content categories outside Movies/TV Shows, Music/Audio, and Video Games without approval.

## 13. Acceptance Criteria

### 13.1 Setup and Authentication

1. The app starts using the documented command.
2. A user can register with username, email, and password.
3. Duplicate usernames and email addresses are rejected.
4. SQLite stores a password hash and salt, not the original password.
5. Valid login succeeds; invalid credentials are rejected.
6. Logout clears the active session and blocks access to account-only screens.

### 13.2 Unified GUI and Movies/TV Shows

7. The app provides one shared GUI with navigation to every required content area.
8. The Movies/TV Shows section retrieves information from an approved no-cost provider.
9. Users can browse/search available movies and TV shows and view supported details.
10. Results distinguish movies from TV shows, show a useful no-results state, and handle missing fields.

### 13.3 Music/Audio

11. The Music/Audio section retrieves data from an approved no-cost provider.
12. Users can browse/search the music content supported by that provider and view available details.
13. The app does not promise full audio playback unless the provider officially supports the relevant no-cost use; unavailable features are explained clearly.

### 13.4 Video Games Catalog

14. The Video Games section retrieves game information from an approved no-cost provider.
15. Users can browse/search available games and view metadata actually provided by the API.
16. The catalog does not count as satisfying the separate playable-game acceptance criteria.

### 13.5 Playable Game Inside the GUI

17. A logged-in user can start an actual playable game from the Play Game section.
18. Starting the game initiates the approved API call or API-supported game-load/session flow.
19. Gameplay is rendered and remains interactive inside the EntertainX application window; no external browser or separate game window is required.
20. At least the primary gameplay actions work, and the game responds visibly to user input.
21. Supported start, active-play, completion/game-over, and restart/retry states work.
22. API/network/embed failures show a useful message and do not crash the app.
23. The chosen provider's terms permit the use, and the integration meets the zero-cost requirements.
24. If actual in-GUI gameplay cannot be supported by an approved no-cost provider, the feature is not marked complete; the blocker and options are reported to the owner.

### 13.6 Custom Primary and Secondary Colors

25. Users can choose separate primary and secondary theme colors from the GUI.
26. Theme changes apply consistently across all sections, including the playable-game area as far as the embedding technology allows.
27. Both values are saved to the currently logged-in local user and restored after logout/login or application restart.
28. New accounts receive sensible default colors; users can restore defaults.
29. Invalid values or canceled color selection do not corrupt saved settings; text and controls remain usable with chosen colors.

### 13.7 Favorites/Personal Library — after core features pass

30. A logged-in user can save and remove supported items from all three content areas.
31. Favorites persist in SQLite across restarts.
32. Favorites are isolated by user and duplicate entries are prevented.
33. Saved references can identify which provider and content type produced each item.

### 13.8 Zero-Cost and Documentation

34. All required API features work without billing activation or a payment card.
35. No required feature depends on an expiring trial, promotional credits, or automatic paid upgrade.
36. Registration, login, saved appearance settings, and favorites use local SQLite without hosted services.
37. `README.md` documents each chosen provider's free-use conditions, relevant limits/rate limits, attribution/licensing requirements, and the features it supports.
38. Rate-limit handling shows a useful message and does not automatically switch to a paid service.
39. Provider selection and playable-game feasibility were checked against official documentation before implementation.
40. Any provider that fails the zero-cost or functional requirements is replaced only after a suitable no-cost option is presented and approved by the owner.

The project team should be able to explain the GUI framework, local authentication, SQLite design, password hashing, the API adapter pattern, each content area's provider, the playable-game integration, theme persistence, the zero-cost checks, and known limitations during the project demonstration.

## 14. Development Principles

- Read this `GOAL.md` and `AGENTS.md` before making major changes.
- Keep the code and UI in one unified application rather than creating separate applications for the categories.
- Implement in small, testable phases; do not generate the entire application in one uncontrolled change.
- Build and test registration, login/logout, and local SQLite operations before finishing all content screens.
- Evaluate API candidates against official documentation and the zero-cost checklist before depending on them.
- Keep provider-specific request/response logic inside adapters; do not bind GUI widgets directly to a specific provider's JSON schema.
- Design for provider replacement without rewriting navigation, user accounts, theme preferences, or favorites storage.
- Prove that a real game can play inside the GUI before claiming the Play Game feature is complete.
- Implement and test theme customization and persistence before favorites.
- Add favorites only after the other required core features work and have appropriate tests.
- Inspect existing files before changing them. Avoid unnecessary rewrites and dependencies.
- Run relevant tests and report actual results; never mark work complete just because code was generated.
- Update `TASKS.md` and `README.md` to match the actual implementation.
- Do not silently substitute a quiz for a playable game, drop a content area, select a paid API, or change providers without owner approval.

## 15. Pending Approval and Setup Items

1. **Scope confirmation with instructor — pending:** Confirm that implementing all three Media and Entertainment areas (Movies/TV Shows, Music/Audio, and Video Games) is acceptable under the assignment's wording about selecting only one function.
2. **GUI framework — resolved:** PySide6 (Qt for Python, LGPL) selected. Directly matches the assignment brief's PyQt/PySide option. No further instructor approval needed for the framework choice.
3. **Free API provider selection — pending:** The owner will find or approve no-cost API alternatives. Evaluate each candidate using official documentation, zero-cost conditions, rate limits, licenses, attribution, and coverage. Providers are changeable; do not hardwire a provider into the application architecture.
4. **Playable-game feasibility — pending and required:** Find an API/provider or API-supported integration that allows an actual game to be played inside the GUI at $0 and under acceptable terms. Verify whether `QWebEngineView` is necessary and compatible with PySide6. If no viable provider is available, present options and wait for owner approval rather than silently substituting another feature.
5. **Music playback scope — pending provider capability:** Music discovery and metadata are in scope. Full-track playback is not guaranteed by the project goal and must only be added if officially available at no cost and permitted by the selected provider.
6. **Operating system — assumption:** Windows is assumed for initial development and demonstration unless otherwise specified.
7. **Deadline and team size:** Not specified in this document. The assignment brief allows one to three members.

The intended direction is clear: **EntertainX is one Python desktop application for Movies/TV Shows, Music/Audio, and Video Games, with local username/email/password authentication, user-selectable primary and secondary colors, a real API-supported game playable inside the GUI, and a local favorites/library added after core features are tested. API providers are flexible and must meet the zero-cost requirement.**
