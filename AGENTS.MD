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

## Icons
- Source of truth: <https://lucide.dev/icons/> (Lucide). Never invent an icon name or recall one from memory.
- Verify each name by fetching `https://lucide.dev/icons/<name>` before using it.
- Fetch SVG source from `https://unpkg.com/lucide-static@latest/icons/<name>.svg` (kebab-case, 24×24 grid, `currentColor` stroke, stroke-width 2).
- Save as `assets/icons/<name>.svg`, keeping the exact Lucide name.
- Render through `ui/components/icons.py::make_icon(name, color, px)` so theme tinting stays in one place — do not tint SVGs at download time.
- Lucide is the only **UI** icon set: no mixed sources and no emoji substitutes for controls. Third-party brand marks follow the Brand logos section below.

## Brand Logos
- Source of truth: <https://thesvg.org/> (theSVG). Use it for third-party brand marks (Netflix, Spotify, Steam, …) — never hand-draw or guess a logo.
- Find the slug from the icon page `https://thesvg.org/icon/<slug>` and read that page's `variants` list first; not every brand ships every variant.
- Download from `https://thesvg.org/icons/<slug>/<variant>.svg`:
  - `default` → full-colour mark (gradients/hex fills, arbitrary viewBox)
  - `mono` → single path, 24×24, usually **no `fill`** → renders black; set an explicit `fill` when it sits on a dark surface
  - `wordmark` → brand name lockup in brand colour
- Store as `assets/brands/<slug>/<variant>.svg`. Keep this separate from `assets/icons/`, which is Lucide only.
- Never tint `default` or `wordmark` — the brand colour is part of the mark. Only `mono` may be recoloured for contrast.
- Brand marks are trademarks: use them to refer to that brand (provider pills, catalogue badges), never as UI controls. Check the page's `license` field — many are `CC0-1.0` but some are `Fair use`, and the `guidelines` URL links the owner's asset rules.

## Key Directories
- `api/` → One file per domain (movies.py, music.py, games.py)
- `assets/icons/` → Lucide SVG icons (see Icons)
- `assets/brands/` → Third-party brand logos by slug (see Brand Logos)
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