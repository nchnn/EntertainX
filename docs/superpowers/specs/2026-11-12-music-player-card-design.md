# EntertainX — Music Player Card (Design)

Date: 2026-11-12
Status: awaiting owner approval.

## Intent

The Music page currently shows the same generic `MediaCard` as Movies, TV, and
Games: a 150px icon tile, title, artist, and track count. The owner wants the
music cards to read as **Music Player cards** — album objects with player
chrome — so the Music section looks like a music app rather than a reskinned
catalogue.

## Goals

1. Replace the Music page's generic cards with a dedicated player card:
   painted album sleeve + vinyl, an always-visible play disc, title, artist,
   track count, a thin progress bar, and elapsed/total time.
2. Keep the existing Music page structure, search, preview badge, empty state,
   and responsive grid. Only the card changes.
3. Play/pause is a **visual preview**: the disc toggles glyph, the progress bar
   and elapsed time animate, and starting one card pauses the others. No audio,
   no seeking — `QMediaPlayer` is a later phase.
4. Theme tokens only; no colour literals in `ui/`. Lucide icons only.
5. Keep the card's public contract (`title`, `subtitle_label`, `meta_label`,
   `matches`, `category`) so `GridPage`/`CardGrid` need no changes.

## Non-goals

- No real audio playback, track lists, queue, volume, or seek interaction.
- No changes to the Video or Games cards.
- No changes to the auth fan's music cover.
- No new raster assets or third-party dependencies.

## Anti-goals

- Six fake players showing an arbitrary mid-track position at rest.
- A play button that does nothing, or a progress bar that lies about playback.
- Cards that clip at the 900px minimum window or break the grid reflow.
- A card that loses search matching or the preview badge.

## Constraints

- PySide6 6.12, Windows, Python 3.
- `CardGrid` sizes cards from their size hint and reflows on width; cards are
  `Preferred`/`Fixed` vertically today.
- `theme.CARD_MIN_WIDTH = 210`; a square cover makes the card taller than the
  current 150px thumb, so the grid must be checked at 900px, 1200px, 1440px.
- No audio engine exists; the page already carries a "Preview" badge and static
  sample data.

## Approaches considered

1. **Mini-player card at rest (chosen).** Square painted sleeve + vinyl, play
   disc over the art, title/artist/tracks, progress and time below. Every card
   reads as a player; the play control drives a visual preview.
2. **Player chrome on hover.** Calmer grid, but the player only appears on
   interaction and does not satisfy "looks like a Music Player card" at rest.
3. **Featured now-playing hero + unchanged grid.** Best for a real player, but
   changes the page structure and leaves the cards generic.

## What the owner decided

- Direction A: mini-player card at rest, play disc always visible.
- The Music page's album cards, not the auth fan cover.

## Decisions made by the builder

- **New component, not a `MediaCard` fork of the page.** `ui/components/music_card.py`
  holds `AlbumArt` (painted sleeve/vinyl) and `MusicPlayerCard`. It mirrors the
  `MediaCard` public surface so `GridPage` and `CardGrid` stay unchanged.
- **Artwork.** A pink sleeve gradient (`SECONDARY` → `ACCENT_PRESSED`) with a
  dark vinyl disc peeking from one side, concentric grooves, a pink label, and
  a centre hole. Disc side/angle varies deterministically per album title, so
  the grid has rhythm without introducing new colours.
- **Square cover.** The art height follows the card width on resize (card height
  grows); the grid reflows, and the art is capped so very wide cards do not
  become billboards.
- **Player row.** A 3px progress track with an accent fill, `0:00` elapsed on
  the left and the album's lead-track length on the right. The progress is
  decorative until audio exists; it never seeks.
- **Play control.** A real `QPushButton` with a Lucide `play`/`pause` icon,
  tooltip, accessible name, and focus ring. It toggles a `QVariantAnimation`
  (0→1 over the track length) that updates the bar and elapsed label. Pausing
  keeps the position; finishing resets to the start.
- **One preview at a time.** `MusicPage` connects each card's `play_toggled` and
  pauses the other cards, matching a single-player model.
- **Sample data.** `ALBUMS` gains a `length` (e.g. `"3:42"`) for the time row;
  `tracks` remains the meta line and search text.
- **Theme.** A QSS role for the play disc; the progress bar is painted from the
  existing `BORDER`/`PRIMARY` tokens, and the disc label/hole reuse the accent
  and on-accent values. No colour literals.

## Parts

- `ui/components/music_card.py` — `AlbumArt`, `PlayerProgress`, `MusicPlayerCard`.
- `ui/pages/music.py` — build `MusicPlayerCard`s; pause siblings on play.
- `ui/pages/sample_data.py` — add album `length`.
- `theme/theme_manager.py` — player QSS roles/tokens.
- `tests/test_music_card.py` — anatomy, filter contract, play toggle, one-at-a-
  time coordination, theme roles.

## Left to the builder

Exact art geometry, groove density, disc offset range, spacing, and copy
beyond the sample lengths.
