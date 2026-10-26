# AGENTS.md — EntertainX

## Project Overview
EntertainX is a multi-category entertainment desktop app built with PySide6 (Qt for Python).  
It includes three main sections (Movies & TV Shows, Music, and Games) under a single unified interface, with user authentication, ratings, personal lists, and full custom theming.

## Core Principles
- Follow `GOAL.md` as the single source of truth
- Keep the three sections feeling like one cohesive application
- Prefer clean, readable, and maintainable code
- APIs are flexible — choose reliable free options
- Never hardcode secrets or store plain-text passwords

## Development Guidelines
- Separate UI, API logic, database, and theme management
- Create reusable components (especially content cards and star rating)
- Handle API failures and loading states gracefully
- Maintain visual consistency across Movies, Music, and Games sections
- Save user preferences (theme colors + mode) in the database

## Key Directories
- `api/` → One file per domain (movies.py, music.py, games.py)
- `ui/` → Organized by section + shared components
- `theme/` → All theming logic
- `database/` → All SQLite operations
- `auth/` → Login, register, password hashing

## When Implementing Features
1. Check the relevant section in GOAL.md
2. Implement cleanly
3. Test the feature
4. Ensure it matches the overall design language
5. Move to the next feature

## Definition of Done
Do not mark the project as complete until the score in GOAL.md reaches ≥ 92 and all checklist items are satisfied.