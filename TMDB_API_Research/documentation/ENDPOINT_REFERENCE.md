# TMDB API Endpoint Reference Specification

Technical specifications for TMDB REST API v3 endpoints, parameter types, validation constraints, and querying rules.

---

## 1. Authentication & Base Protocols

- **Base URL:** `https://api.themoviedb.org/3`
- **Protocol:** HTTPS (TLS 1.2+ mandatory)
- **Supported Methods:** `GET`, `POST`, `DELETE` (Research suite focuses on read operations via `GET`)
- **Authentication Parameters:**
  - Query parameter: `?api_key=YOUR_KEY`
  - HTTP Header: `Authorization: Bearer <API_READ_ACCESS_TOKEN>` (v4 auth token)
- **Content Type:** `application/json;charset=utf-8`

---

## 2. Movies Domain

### 2.1 Movie Details
- **Endpoint:** `GET /movie/{movie_id}`
- **Path Parameters:**
  - `movie_id` (integer, required): TMDB movie identifier.
- **Query Parameters:**
  - `language` (string, optional, default: `en-US`): ISO 639-1 language code.
  - `append_to_response` (string, optional): Comma-separated list of sub-resources to bundle into a single response.
    - Supported values: `credits`, `videos`, `images`, `release_dates`, `keywords`, `external_ids`, `recommendations`, `similar`, `reviews`, `watch/providers`, `lists`, `translations`.

### 2.2 Movie Credits
- **Endpoint:** `GET /movie/{movie_id}/credits`
- **Path Parameters:**
  - `movie_id` (integer, required)
- **Query Parameters:**
  - `language` (string, optional, default: `en-US`)

### 2.3 Curated Movie Lists
- **Endpoints:**
  - `GET /movie/popular`
  - `GET /movie/now_playing`
  - `GET /movie/top_rated`
  - `GET /movie/upcoming`
- **Query Parameters:**
  - `page` (integer, optional, default: `1`, min: `1`, max: `500`): Pagination index.
  - `language` (string, optional, default: `en-US`)
  - `region` (string, optional): ISO 3166-1 alpha-2 code to filter theatrical release windows.

### 2.4 Media (Images & Videos)
- **Endpoints:**
  - `GET /movie/{movie_id}/images`
  - `GET /movie/{movie_id}/videos`
- **Query Parameters for Images:**
  - `include_image_language` (string, optional): Comma-separated ISO 639-1 codes (e.g. `en,null` to include textless artwork).
- **Query Parameters for Videos:**
  - `include_video_language` (string, optional)

---

## 3. TV Shows Domain

### 3.1 TV Series Details
- **Endpoint:** `GET /tv/{series_id}`
- **Path Parameters:**
  - `series_id` (integer, required): TMDB series identifier.
- **Query Parameters:**
  - `language` (string, optional, default: `en-US`)
  - `append_to_response` (string, optional): `credits`, `aggregate_credits`, `videos`, `images`, `content_ratings`, `keywords`, `external_ids`, `recommendations`, `similar`, `reviews`, `watch/providers`, `season/{season_number}`.

### 3.2 TV Seasons & Episodes
- **Endpoints:**
  - `GET /tv/{series_id}/season/{season_number}`
  - `GET /tv/{series_id}/season/{season_number}/episode/{episode_number}`
- **Path Parameters:**
  - `series_id` (integer, required)
  - `season_number` (integer, required): 0 indicates specials; 1+ indicates formal seasons.
  - `episode_number` (integer, required): 1-indexed sequential episode number.

### 3.3 TV Aggregate Credits
- **Endpoint:** `GET /tv/{series_id}/aggregate_credits`
- **Description:** Aggregates all actor and crew contributions across the entire broadcast run, computing total episode counts and character iterations. Superior to `/credits` for series overview pages.

---

## 4. People Domain

### 4.1 Person Details
- **Endpoint:** `GET /person/{person_id}`
- **Path Parameters:**
  - `person_id` (integer, required)
- **Query Parameters:**
  - `append_to_response` (string, optional): `movie_credits`, `tv_credits`, `combined_credits`, `images`, `external_ids`, `tagged_images`.

### 4.2 Combined Credits
- **Endpoint:** `GET /person/{person_id}/combined_credits`
- **Description:** Returns both cinematic and television roles in two unified arrays (`cast` and `crew`) with distinct `media_type` tags.

---

## 5. Search & Discovery Engines

### 5.1 Multi Search
- **Endpoint:** `GET /search/multi`
- **Query Parameters:**
  - `query` (string, required): URI-encoded search phrase.
  - `page` (integer, optional, default: 1, max: 500)
  - `include_adult` (boolean, optional, default: false)
  - `language` (string, optional, default: `en-US`)
- **Behavior:** Returns polymorphic objects in `results` differentiated by `media_type: "movie" | "tv" | "person"`.

### 5.2 Faceted Movie Discovery
- **Endpoint:** `GET /discover/movie`
- **Key Parameters:**
  - `sort_by` (string, default: `popularity.desc`): Supported values include `popularity.asc`, `popularity.desc`, `revenue.desc`, `primary_release_date.desc`, `vote_average.desc`, `vote_count.desc`.
  - `with_genres` (string, optional): Comma-separated (AND) or pipe-separated (OR) genre IDs.
  - `vote_count.gte` (integer, optional): Eliminates unvetted niche titles with artificially high ratings.
  - `vote_average.gte` (number, optional, range: 0.0 to 10.0)
  - `primary_release_year` (integer, optional)
  - `with_watch_providers` (string, optional): Filter by streaming service ID.
  - `watch_region` (string, optional): Mandatory when filtering by watch providers.

---

## 6. System Configuration & Image Construction

TMDB does not serve full CDN image URLs in resource payloads. It supplies relative paths (e.g. `/path.jpg`).

### Image URL Assembly Rule
`URL = {images.secure_base_url} + {size_tier} + {file_path}`

### Official Dimension Tiers:
- **Posters:** `w92`, `w154`, `w185`, `w342`, `w500`, `w780`, `original`
- **Backdrops:** `w300`, `w780`, `w1280`, `original`
- **Profiles:** `w45`, `w185`, `h632`, `original`
- **Logos:** `w45`, `w92`, `w154`, `w185`, `w300`, `w500`, `original`
- **Episode Stills:** `w92`, `w185`, `w300`, `original`
