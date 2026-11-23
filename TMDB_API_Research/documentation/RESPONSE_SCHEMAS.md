# TMDB API Verified Response Schemas

Field-by-field structural specifications, typing rules, and nullability flags extracted and verified against live TMDB API responses.

---

## 1. Movie Details Schema (`GET /movie/{id}`)

| Field Name | Type | Nullable | Description / Sub-structure |
| :--- | :--- | :--- | :--- |
| `adult` | `boolean` | No | Indicates adult content classification |
| `backdrop_path` | `string` | Yes | Relative image path on CDN (e.g. `/rr7E0NoGKxvbSu2ecNdR9NiKuM4.jpg`) |
| `belongs_to_collection` | `object` | Yes | `{ id: int, name: string, poster_path: string?, backdrop_path: string? }` |
| `budget` | `integer` | No | Production budget in USD (0 indicates unrecorded) |
| `genres` | `Array<object>`| No | `[ { id: int, name: string } ]` |
| `homepage` | `string` | Yes | Official promotional website URL |
| `id` | `integer` | No | Unique TMDB primary key |
| `imdb_id` | `string` | Yes | External IMDB identifier (e.g. `tt0137523`) |
| `origin_country` | `Array<string>`| No | ISO 3166-1 alpha-2 country codes |
| `original_language` | `string` | No | ISO 639-1 code (e.g. `en`) |
| `original_title` | `string` | No | Untranslated title in native language |
| `overview` | `string` | Yes | Synopsis narrative |
| `popularity` | `number` | No | Algorithmic popularity metric |
| `poster_path` | `string` | Yes | Relative poster image path |
| `production_companies` | `Array<object>`| No | `[ { id: int, logo_path: string?, name: string, origin_country: string } ]` |
| `production_countries` | `Array<object>`| No | `[ { iso_3166_1: string, name: string } ]` |
| `release_date` | `string` | No | Format: `YYYY-MM-DD` |
| `revenue` | `integer` | No | Worldwide box office revenue in USD |
| `runtime` | `integer` | Yes | Length of feature in minutes |
| `spoken_languages` | `Array<object>`| No | `[ { english_name: string, iso_639_1: string, name: string } ]` |
| `status` | `string` | No | `Rumored`, `Planned`, `In Production`, `Post Production`, `Released`, `Canceled` |
| `tagline` | `string` | Yes | Promotional marketing tagline |
| `title` | `string` | No | Localized release title |
| `video` | `boolean` | No | Indicates existence of uploaded digital master video |
| `vote_average` | `number` | No | Mean user rating (0.0 to 10.0) |
| `vote_count` | `integer` | No | Total count of validated user ratings |

### Appended Sub-Resources (via `append_to_response`)
- **`credits`:**
  - `cast`: `Array<{ adult: bool, gender: int, id: int, known_for_department: str, name: str, original_name: str, popularity: num, profile_path: str?, cast_id: int, character: str, credit_id: str, order: int }>`
  - `crew`: `Array<{ adult: bool, gender: int, id: int, known_for_department: str, name: str, original_name: str, popularity: num, profile_path: str?, credit_id: str, department: str, job: str }>`
- **`videos`:**
  - `results`: `Array<{ iso_639_1: str, iso_3166_1: str, name: str, key: str, site: str ("YouTube"), size: int, type: str ("Trailer"|"Teaser"|"Featurette"), official: bool, published_at: str, id: str }>`
- **`images`:**
  - `backdrops`: `Array<{ aspect_ratio: num, height: int, iso_639_1: str?, file_path: str, vote_average: num, vote_count: int, width: int }>`
  - `posters`: `Array<{ aspect_ratio: num, height: int, iso_639_1: str?, file_path: str, vote_average: num, vote_count: int, width: int }>`
  - `logos`: `Array<{ aspect_ratio: num, height: int, iso_639_1: str?, file_path: str, vote_average: num, vote_count: int, width: int }>`
- **`release_dates`:**
  - `results`: `Array<{ iso_3166_1: str, release_dates: Array<{ certification: str, descriptors: Array<str>, iso_639_1: str?, note: str, release_date: str, type: int }> }>`
- **`external_ids`:**
  - `{ imdb_id: str?, wikidata_id: str?, facebook_id: str?, instagram_id: str?, twitter_id: str? }`

---

## 2. TV Show Details Schema (`GET /tv/{id}`)

| Field Name | Type | Nullable | Description / Sub-structure |
| :--- | :--- | :--- | :--- |
| `adult` | `boolean` | No | Explicit classification flag |
| `backdrop_path` | `string` | Yes | Series landscape backdrop |
| `created_by` | `Array<object>`| No | `[ { id: int, credit_id: str, name: str, gender: int, profile_path: str? } ]` |
| `episode_run_time` | `Array<int>` | No | Typical durations in minutes (often empty in modern responses) |
| `first_air_date` | `string` | Yes | Series premiere date (`YYYY-MM-DD`) |
| `genres` | `Array<object>`| No | `[ { id: int, name: string } ]` |
| `homepage` | `string` | Yes | Network series portal |
| `id` | `integer` | No | Series primary key |
| `in_production` | `boolean` | No | Active production state |
| `languages` | `Array<string>`| No | Spoken audio languages |
| `last_air_date` | `string` | Yes | Date of most recent broadcast |
| `last_episode_to_air` | `object` | Yes | Full episode summary object |
| `name` | `string` | No | Series title |
| `next_episode_to_air` | `object` | Yes | Upcoming scheduled broadcast summary |
| `networks` | `Array<object>`| No | `[ { id: int, logo_path: str?, name: str, origin_country: str } ]` |
| `number_of_episodes`| `integer` | No | Total cumulative broadcast episodes |
| `number_of_seasons` | `integer` | No | Total formal broadcast seasons |
| `origin_country` | `Array<string>`| No | Producing nation codes |
| `original_language` | `string` | No | Original audio language code |
| `original_name` | `string` | No | Untranslated series title |
| `overview` | `string` | Yes | Series logline / description |
| `popularity` | `number` | No | TMDB internal engagement score |
| `poster_path` | `string` | Yes | Main portrait poster path |
| `seasons` | `Array<object>`| No | `[ { air_date: str?, episode_count: int, id: int, name: str, overview: str, poster_path: str?, season_number: int, vote_average: num } ]` |
| `status` | `string` | No | `Returning Series`, `Ended`, `Canceled`, `In Production` |
| `tagline` | `string` | Yes | Series slogan |
| `type` | `string` | No | `Scripted`, `Documentary`, `Miniseries`, `Reality` |
| `vote_average` | `number` | No | Rating average (0 to 10) |
| `vote_count` | `integer` | No | Rating sample size |

### Specialized TV Sub-Resources
- **`aggregate_credits`:**
  - `cast`: `Array<{ id: int, name: str, roles: Array<{ credit_id: str, character: str, episode_count: int }>, total_episode_count: int, order: int }>`
- **`content_ratings`:**
  - `results`: `Array<{ descriptors: Array<str>, iso_3166_1: str, rating: str }>`

---

## 3. Person Details Schema (`GET /person/{id}`)

| Field Name | Type | Nullable | Description |
| :--- | :--- | :--- | :--- |
| `adult` | `boolean` | No | Adult performer flag |
| `also_known_as` | `Array<string>`| No | Alternate screen names and localized spellings |
| `biography` | `string` | Yes | Markdown-formatted or plain text life history |
| `birthday` | `string` | Yes | Date of birth (`YYYY-MM-DD`) |
| `deathday` | `string` | Yes | Date of passing (`YYYY-MM-DD`), null if living |
| `gender` | `integer` | No | 0: Unspecified, 1: Female, 2: Male, 3: Non-binary |
| `homepage` | `string` | Yes | Personal website URL |
| `id` | `integer` | No | Person identifier |
| `imdb_id` | `string` | Yes | IMDB name identifier (e.g. `nm0000093`) |
| `known_for_department`| `string` | No | Primary vocation (`Acting`, `Directing`, `Writing`, etc.) |
| `name` | `string` | No | Primary billing name |
| `place_of_birth` | `string` | Yes | City, State/Province, Country string |
| `popularity` | `number` | No | Trend metric |
| `profile_path` | `string` | Yes | Portrait image path |

---

## 4. Paginated List Envelope (`Curated`, `Search`, `Discover`, `Trending`)

Every collection endpoint returns a standardized outer envelope:

```json
{
  "page": 1,
  "results": [ ... ],
  "total_pages": 42,
  "total_results": 834
}
```

- `page` (`integer`): Current result window index.
- `results` (`Array<object>`): Collection of items.
- `total_pages` (`integer`): Hard capped by TMDB at 500 pages for search/discover endpoints.
- `total_results` (`integer`): Absolute matching count in catalogue.
