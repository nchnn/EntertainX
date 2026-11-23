# TMDB API Research Notes & Architectural Recommendations for EntertainX

Synthesis of API behavior, efficiency patterns, edge cases, and design recommendations for the EntertainX desktop client.

---

## 1. Core Architectural Discoveries

### 1.1 The Single-Roundtrip Pattern (`append_to_response`)
- **Problem:** A standard movie details screen requires primary metadata, cast/crew credits, trailers/videos, high-res backdrops, age certifications, external IDs (IMDB), and streaming providers. Querying each endpoint individually requires 7 to 8 sequential or parallel HTTP requests.
- **Solution:** TMDB supports `append_to_response`. A single request:
  `GET /movie/{id}?api_key=KEY&append_to_response=credits,videos,images,release_dates,keywords,external_ids,watch/providers`
  delivers the complete screen dataset in one compact payload.
- **Impact for EntertainX:** Reduces network latency by over 80% on page navigation and avoids Qt thread pool exhaustion.

### 1.2 TV Aggregate Credits vs Basic Credits
- **Observation:** Calling `GET /tv/{id}/credits` often only reflects the original or first season's billing order. Long-running series (e.g. *Game of Thrones*) have complex multi-year cast rotations.
- **Recommendation:** Always use `GET /tv/{id}/aggregate_credits`. This endpoint returns a `total_episode_count` for each actor and an array of `roles` capturing character title changes across seasons.

### 1.3 Image CDN Performance and Resolution Strategy
- **Trap:** Loading `original` image files into Qt `QPixmap` or QML cards causes severe UI stutter, memory leaks, and excessive bandwidth consumption.
- **Resolution Matrix for EntertainX:**
  - Card Grids (Posters): `w342` (optimal balance of sharpness on Retina/4K displays and memory footprint: ~40KB per image).
  - Hero Backdrops: `w1280` (smooth gradient blend without pixelation).
  - Cast Avatars: `w185` (circular or rounded-rect badges).
  - Transparent Studio/Network Logos: `w300` (crisp rendering on dark surfaces).

### 1.4 Rate Limiting & Concurrency
- **Status:** TMDB historically enforced a strict 40 requests per 10 seconds limit. While that hard limit was replaced with adaptive capacity-based throttling, bursts exceeding 50 concurrent calls can return `HTTP 429 Too Many Requests`.
- **Implementation Rule:** In `api/movies.py`, wrap all network requests in an exponential backoff decorator respecting the `Retry-After` header.

### 1.5 OTT Watch Providers (JustWatch Integration)
- The `/watch/providers` sub-resource provides localized streaming platforms (Netflix, HBO Max, Disney+, Apple TV).
- **Licensing Constraint:** TMDB terms require displaying the JustWatch attribution logo whenever streaming availability data is rendered.

---

## 2. API Edge Cases & Data Anomalies

1. **Nullable Fields:**
   - `budget` and `revenue` return `0` instead of `null` when financial figures are undisclosed. Code must check `> 0` before formatting currency strings.
   - `overview`, `tagline`, and `poster_path` can be `null` for newly registered indie films or foreign titles. The UI must provide consistent placeholder states.
2. **TV Season 0:**
   - Specials, bonus features, and unaired pilots are grouped into `season_number: 0`. The season selector dropdown should label Season 0 as "Specials" or sort it appropriately.
3. **Pagination Upper Limit:**
   - TMDB enforces a hard ceiling of 500 pages (`page <= 500`) on all search and discover endpoints, regardless of `total_pages` returned. Querying page 501 triggers an `HTTP 422 Unprocessable Entity`.

---

## 3. Recommended SQLite Caching Layer for EntertainX

To maintain a zero-lag desktop experience and conform to offline-first principles:

1. **Taxonomy Cache (30-day TTL):**
   - Store `/genre/movie/list`, `/genre/tv/list`, and `/configuration` in SQLite tables. These datasets change infrequently.
2. **Media Details Cache (24-hour TTL):**
   - Cache full JSON payloads from `/movie/{id}` and `/tv/{id}` keyed by media ID and language.
3. **Image Cache:**
   - Store downloaded poster and backdrop bytes in `$LOCALAPPDATA/EntertainX/cache/images/` using MD5 hash filenames. Verify file existence before issuing HTTP GET requests.

---

## 4. EntertainX UI Integration Checklist

- [ ] Implement `TMDBClient` in `api/movies.py` with `append_to_response` support.
- [ ] Implement `QThread` / `QRunnable` worker with `QThreadPool` for all API calls.
- [ ] Build reusable `MediaCard` widget utilizing `w342` posters and vote badges.
- [ ] Build `HeroBanner` component with progressive image loading (low-res placeholder to `w1280`).
- [ ] Add JustWatch attribution pill to the watch providers panel.
- [ ] Implement graceful offline fallback with cached SQLite data.
