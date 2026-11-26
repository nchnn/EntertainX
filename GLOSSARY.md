# EntertainX

EntertainX is a unified multi-category entertainment desktop workspace for discovering Movies & TV Shows, Music, and Video Games with personal lists and customizable themes.

## Language

**Title**:
A Movie or TV Show entry presented across shelves, search results, **Hover Previews**, and **Title Details**.
_Avoid_: item, record, entry

**Hover Preview**:
A floating miniature card raised over a browsed **Title** after hover intent, showing backdrop art, metadata, quick actions, and auto-playing its **Trailer**.
_Avoid_: tooltip card, popup preview

**Title Detail**:
The modal view presenting full metadata for a **Title**, including synopsis, cast, certification, runtime, logo art, and **Trailer** playback.
_Avoid_: info modal, details popup

**Trailer**:
A promotional YouTube video linked to a **Title**, played either inline inside a **Hover Preview** or **Title Detail** header or full-window inside a dialog.
_Avoid_: preview clip, video embed

**Trailer Player**:
The unified playback surface that validates, renders, mutes, and tears down a **Trailer** across inline and standalone modes.
_Avoid_: web view, video frame, embed wrapper

**Watchlist**:
A user's personal collection of saved **Titles** toggled across **Hover Previews**, **Title Details**, and personal lists.
_Avoid_: favorites, queue
