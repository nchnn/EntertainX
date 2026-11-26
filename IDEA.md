# ENTERTAINX — PROJECT INSTRUCTIONS

## 1. PROJECT OVERVIEW

EntertainX is a Python desktop application that combines three entertainment categories into one unified GUI:

1. Movies and TV Shows
2. Music and Audio
3. Video Games

The application aims to provide entertainment discovery, local user authentication, customizable appearance, personal favorites, and an actual playable game inside the application.

It is a noncommercial academic project. Prioritize functionality, usability, security, maintainability, and zero-cost operation.

## 2. PROJECT OWNER AUTHORITY — HIGHEST PRIORITY

The project owner has FINAL AUTHORITY over every aspect of EntertainX development.

The owner can:
- Add, modify, improve, or remove features.
- Change requirements and development priorities.
- Replace APIs, libraries, frameworks, and technologies.
- Redesign the GUI and application architecture.
- Approve or reject recommendations.
- Expand or reduce the project's scope.
- Change previously approved decisions.

The assistant acts as a development partner, technical adviser, and programmer.

IMPORTANT RULES:
- Always follow the owner's latest instructions.
- Never impose recommendations as mandatory requirements.
- Never silently remove, replace, or modify approved features.
- Explain technical limitations and propose alternatives.
- Ask for approval before significant changes to requirements, architecture, or project direction.
- Do not assume that an earlier decision cannot be changed.

Keep the application modular and flexible to support future modifications.

## 3. ACADEMIC REQUIREMENTS

The assignment specifies:
- Python GUI development using PyQt/PySide.
- User authentication/login.
- SQLite for user data storage.
- Salted password hashing using Python's built-in hashlib.
- Media and Entertainment as the selected project category.

The assignment lists Movies and TV Shows, Music and Audio, and Video Games under Media and Entertainment.

IMPORTANT: The assignment mentions choosing only one function. Confirm with the instructor whether implementing all three entertainment subcategories is acceptable. Do not remove any requested category without the owner's approval.

## 4. TECHNOLOGY STACK

Current preferred technologies:

- Programming language: Python
- GUI: PySide6 (Qt for Python)
- Database: SQLite (sqlite3)
- Password security: hashlib
- API requests: requests
- Image processing: Pillow when needed
- Color selection: Qt QColorDialog

These are the current project choices, but the owner may approve alternatives whenever necessary.

Keep dependencies minimal. Avoid unnecessary frameworks, libraries, and services.

## 5. CORE FEATURES

### A. Registration and Authentication

Registration fields:
- Username
- Email
- Password

Requirements:
- Validate registration inputs.
- Prevent duplicate usernames and emails.
- Store account information in SQLite.
- Allow users to log in using username and password.
- Support secure logout and session handling.
- Restrict account-specific features to logged-in users.

Security:
- Use hashlib.pbkdf2_hmac or an approved secure password-hashing approach.
- Generate a unique cryptographically secure salt per account.
- Never store plain-text passwords.
- Use parameterized SQL queries.

Authentication is local through SQLite. Cloud authentication is not required.

### B. Movies and TV Shows

Users must be able to:
- Play Movie or TV Shows
- Browse and search movies and TV shows.
- View titles and descriptions.
- Display posters and artwork.
- View release dates, genres, ratings, cast, and other available information.

Full movie and TV streaming are not required.

### C. Music and Audio

Users must be able to:
- Play music
- Discover and search artists.
- Search songs and albums.
- Browse music information.
- Display album artwork.
- View available track, artist, genre, and release information.

Audio previews or playback may be added if officially supported at no cost. Full-track streaming is not mandatory.

### D. Video Games Catalog

Users must be able to:
- Play inside GUI
- Browse and search video games.
- View descriptions and game information.
- Display game artwork.
- View available genres, platforms, release dates, and ratings.

The game catalog is separate from the playable-game feature.

### E. Playable Game Inside EntertainX

EntertainX MUST include a separate Play Game section.

Requirements:
- Users can start an actual playable game.
- Gameplay appears inside the EntertainX application window.
- Support real keyboard or mouse interaction.
- Gameplay responds to user input.
- Provide appropriate loading, start, completion/game-over, and restart states.
- Use an approved API or officially supported API-based game integration.

A game catalog, external browser link, or trivia quiz does NOT satisfy this requirement.

Investigate whether PySide6 QWebEngineView or another compatible component is necessary.

If no suitable zero-cost integration exists, explain the limitation and present alternatives. Wait for the owner's approval before changing this requirement.

### F. Customizable Theme

Users must be able to customize:

1. Primary Color
2. Secondary Color

Requirements:
- Separate color-selection controls.
- Color picker interface.
- Apply changes throughout the GUI.
- Maintain readable text and sufficient contrast.
- Provide default colors and a reset option.
- Save preferences in SQLite.
- Associate preferences with individual accounts.
- Restore preferences after login.
- Apply changes without restarting the application.

### G. Favorites / Personal Library

Implement this after the core features are working and tested.

Users should be able to:
- Save favorite movies and TV shows.
- Save favorite artists, albums, and tracks.
- Save favorite video games.
- View saved content in one personal library.
- Remove favorites.
- Filter saved content by category.

Store external provider IDs and associate saved items with the correct local account. Prevent duplicate entries.

## 6. API INTEGRATION AND PROVIDER FLEXIBILITY

No specific API provider is permanently required.

Different providers may be used for Movies/TV Shows, Music/Audio, Video Games, and Playable Game integration.

Before selecting a provider, verify:
- Official documentation and available endpoints.
- Actual feature compatibility.
- Free-access conditions.
- Rate limits and authentication requirements.
- Licensing, attribution, and usage restrictions.
- Game embedding permissions when applicable.

Use modular API adapters/services. Keep provider-specific requests and response processing separate from GUI components.

This allows approved providers to be replaced without rewriting the entire application.

The owner must approve significant provider selections and replacements.

## 7. ZERO-COST REQUIREMENT

Every required feature must operate at $0 in API fees.

Do not require:
- Paid API subscriptions.
- Payment cards or billing activation.
- Paid proxies or hosting.
- Paid authentication.
- Expiring trials or promotional credits.
- Automatic paid upgrades.

Use local SQLite for accounts, preferences, and favorites.

Respect API rate limits, licensing, and provider terms.

Never silently switch to paid services.

Document selected providers, free-access conditions, limitations, and attribution requirements in README.md.

## 8. GUI AND APPLICATION STRUCTURE

Use one unified application with shared navigation.

Main sections:
1. Home / Dashboard
2. Movies and TV Shows
3. Music and Audio
4. Video Games
5. Play Game
6. Settings / Appearance
7. Favorites / Personal Library

Include appropriate loading indicators, search results, empty states, error messages, offline handling, and retry functionality.

Maintain a consistent interface and preserve the user's session when navigating between sections.

Do not create separate independent applications for each category.

## 9. SECURITY AND RELIABILITY

- Validate user inputs.
- Use parameterized SQLite queries.
- Protect API credentials.
- Never expose passwords or password hashes.
- Handle missing or unexpected API responses.
- Prevent network requests from freezing the GUI.
- Handle connection failures gracefully.
- Keep account-specific information isolated.
- Never execute arbitrary code returned by APIs.
- Follow external game providers' security and embedding requirements.

## 10. DEVELOPMENT PRIORITIES

Recommended implementation sequence:

1. Project setup, architecture, and SQLite.
2. Registration, login, logout, and password security.
3. Unified GUI, dashboard, and navigation.
4. Movies/TV, Music/Audio, and Video Games API integrations.
5. Actual playable game inside the GUI.
6. Primary and secondary theme customization.
7. Favorites and personal library.
8. Testing, debugging, documentation, and final demonstration.

The owner may change this sequence at any time.

Do not consider a feature complete until it has been implemented and tested.

## 11. INITIAL OUT-OF-SCOPE FEATURES

Unless approved by the owner, the initial version does not require:
- Separate web or mobile applications.
- Full movie or TV streaming.
- Full music streaming or downloads.
- Paid subscriptions.
- Cloud authentication or synchronization.
- Social networking features.
- Administrator dashboards.
- Complex AI recommendation systems.
- Email verification or password recovery.

These limitations are not permanent. The owner may approve them in the future.

## 12. DEVELOPMENT WORKING RULES

When working on EntertainX:

1. Read AGENTS.md, and relevant documentation before major changes.
2. Inspect existing files before editing.
3. Preserve existing working features.
4. Follow the latest owner-approved requirements.
5. Work in manageable, testable steps.
6. Avoid unnecessary rewrites and dependencies.
7. Explain technical decisions and limitations.
8. Test implemented functionality.
9. Never claim untested features are working.
10. Update README.md and TASKS.md when appropriate.
11. Never silently substitute a quiz for the playable game, drop a content category, or select a paid API.
12. Ask for approval before significant project changes.

## 13. FINAL DEVELOPMENT PRINCIPLE

EntertainX is the project owner's creation.

The assistant must help implement the owner's vision, provide technical guidance, identify problems, suggest improvements, and explain possible solutions.

However, recommendations are not decisions.

The owner has the FINAL SAY over all features, technologies, APIs, designs, priorities, modifications, and project direction.

**ALWAYS PRIORITIZE THE OWNER'S LATEST APPROVED INSTRUCTIONS.**
