"""Movies and TV adapter backed by The Movie Database (TMDB).

Everything provider-specific lives here: endpoints, authentication, response
parsing, and the on-disk JSON cache. The UI only sees :class:`MediaItem` and
:class:`MediaDetails`, so TMDB can be swapped for another provider by
implementing the same interface (``available``, ``fetch_row``, ``search``,
``discover``, ``details``).

TMDB is free for non-commercial use with attribution; see README.md.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from pathlib import Path

import requests

from api.config import CACHE_DIR, get_key

API_BASE = "https://api.themoviedb.org/3"
IMAGE_BASE = "https://image.tmdb.org/t/p"

LIST_TTL = 30 * 60
SEARCH_TTL = 5 * 60
DETAIL_TTL = 6 * 60 * 60


# ── Errors ──────────────────────────────────────────────────────────────────
class ApiError(Exception):
    """Any failure talking to the provider; the message is safe to show."""


class MissingApiKey(ApiError):
    """No TMDB key is configured."""


class NetworkError(ApiError):
    """The provider could not be reached and nothing was cached."""


# ── Genres (TMDB ids are stable) ────────────────────────────────────────────
MOVIE_GENRES = {
    28: "Action", 12: "Adventure", 16: "Animation", 35: "Comedy", 80: "Crime",
    99: "Documentary", 18: "Drama", 10751: "Family", 14: "Fantasy",
    36: "History", 27: "Horror", 10402: "Music", 9648: "Mystery",
    10749: "Romance", 878: "Sci-Fi", 10770: "TV Movie", 53: "Thriller",
    10752: "War", 37: "Western",
}
TV_GENRES = {
    10759: "Action & Adventure", 16: "Animation", 35: "Comedy", 80: "Crime",
    99: "Documentary", 18: "Drama", 10751: "Family", 10762: "Kids",
    9648: "Mystery", 10763: "News", 10764: "Reality", 10765: "Sci-Fi & Fantasy",
    10766: "Soap", 10767: "Talk", 10768: "War & Politics", 37: "Western",
}
ALL_GENRES = {**MOVIE_GENRES, **TV_GENRES}

GENRE_FILTERS = {
    "movie": sorted(MOVIE_GENRES.items(), key=lambda pair: pair[1]),
    "tv": sorted(TV_GENRES.items(), key=lambda pair: pair[1]),
}


# ── Models ──────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class MediaItem:
    id: int
    media_type: str  # "movie" | "tv"
    title: str
    overview: str = ""
    poster_path: str = ""
    backdrop_path: str = ""
    release_date: str = ""
    rating: float = 0.0
    votes: int = 0
    genre_ids: tuple[int, ...] = ()

    @property
    def year(self) -> str:
        return self.release_date[:4]

    @property
    def kind_label(self) -> str:
        return "Movie" if self.media_type == "movie" else "TV Series"

    @property
    def genre_names(self) -> list[str]:
        return [ALL_GENRES[g] for g in self.genre_ids if g in ALL_GENRES]

    @property
    def key(self) -> tuple[str, int]:
        return (self.media_type, self.id)

    def backdrop_url(self, size: str = "w780") -> str:
        return f"{IMAGE_BASE}/{size}{self.backdrop_path}" if self.backdrop_path else ""

    def poster_url(self, size: str = "w500") -> str:
        return f"{IMAGE_BASE}/{size}{self.poster_path}" if self.poster_path else ""

    def art_url(self, size: str = "w780") -> str:
        """Landscape art when TMDB has it, otherwise the poster."""
        return self.backdrop_url(size) or self.poster_url("w500")


@dataclass(frozen=True)
class MediaDetails:
    item: MediaItem
    tagline: str = ""
    runtime_text: str = ""
    certification: str = ""
    genres: tuple[str, ...] = ()
    cast: tuple[str, ...] = ()
    credit_label: str = ""
    credits: tuple[str, ...] = ()
    trailer_key: str = ""
    status: str = ""
    logo_path: str = ""
    english_backdrop_path: str = ""
    textless_backdrop_path: str = ""
    english_poster_path: str = ""

    def logo_url(self, size: str = "w500") -> str:
        return f"{IMAGE_BASE}/{size}{self.logo_path}" if self.logo_path else ""

    def backdrop_url(self, size: str = "w780") -> str:
        path = self.english_backdrop_path or self.item.backdrop_path
        return f"{IMAGE_BASE}/{size}{path}" if path else ""

    def textless_backdrop_url(self, size: str = "w780") -> str:
        path = self.textless_backdrop_path or self.item.backdrop_path
        return f"{IMAGE_BASE}/{size}{path}" if path else ""

    def poster_url(self, size: str = "w500") -> str:
        path = self.english_poster_path or self.item.poster_path
        return f"{IMAGE_BASE}/{size}{path}" if path else ""


@dataclass(frozen=True)
class RowSpec:
    """One shelf on the browse page; ``badge`` is "top10", "new" or ""."""

    key: str
    title: str
    source: str  # "trending" | "category" | "genre"
    arg: str = ""
    badge: str = ""


MOVIE_ROWS = [
    RowSpec("trending", "Trending This Week", "trending", badge="top10"),
    RowSpec("now_playing", "New in Theaters", "category", "now_playing", "new"),
    RowSpec("upcoming", "Coming Soon", "category", "upcoming"),
    RowSpec("popular", "Popular Right Now", "category", "popular"),
    RowSpec("top_rated", "Critically Acclaimed", "category", "top_rated"),
    RowSpec("g28", "Action", "genre", "28"),
    RowSpec("g878", "Sci-Fi", "genre", "878"),
    RowSpec("g35", "Comedy", "genre", "35"),
    RowSpec("g16", "Animation", "genre", "16"),
    RowSpec("g27", "Horror", "genre", "27"),
    RowSpec("g18", "Drama", "genre", "18"),
]
TV_ROWS = [
    RowSpec("trending", "Trending This Week", "trending", badge="top10"),
    RowSpec("airing_today", "Airing Today", "category", "airing_today", "new"),
    RowSpec("on_the_air", "On the Air", "category", "on_the_air"),
    RowSpec("popular", "Popular Right Now", "category", "popular"),
    RowSpec("top_rated", "Critically Acclaimed", "category", "top_rated"),
    RowSpec("g18", "Drama", "genre", "18"),
    RowSpec("g35", "Comedy", "genre", "35"),
    RowSpec("g10765", "Sci-Fi & Fantasy", "genre", "10765"),
    RowSpec("g80", "Crime", "genre", "80"),
    RowSpec("g16", "Animation", "genre", "16"),
    RowSpec("g99", "Documentary", "genre", "99"),
]
ROWS = {"movie": MOVIE_ROWS, "tv": TV_ROWS}

_CATEGORIES = {
    "movie": {"now_playing", "upcoming", "popular", "top_rated"},
    "tv": {"airing_today", "on_the_air", "popular", "top_rated"},
}


# ── Parsing ─────────────────────────────────────────────────────────────────
def parse_item(raw: dict, media_type: str) -> MediaItem | None:
    """Build a :class:`MediaItem`, or ``None`` for people and malformed rows."""
    kind = raw.get("media_type", media_type)
    if kind not in ("movie", "tv"):
        return None
    title = raw.get("title") or raw.get("name") or ""
    ident = raw.get("id")
    if not title or not isinstance(ident, int):
        return None
    return MediaItem(
        id=ident,
        media_type=kind,
        title=str(title),
        overview=str(raw.get("overview") or ""),
        poster_path=str(raw.get("poster_path") or ""),
        backdrop_path=str(raw.get("backdrop_path") or ""),
        release_date=str(raw.get("release_date") or raw.get("first_air_date") or ""),
        rating=float(raw.get("vote_average") or 0.0),
        votes=int(raw.get("vote_count") or 0),
        genre_ids=tuple(g for g in raw.get("genre_ids", []) if isinstance(g, int)),
    )


def parse_items(payload: dict, media_type: str) -> list[MediaItem]:
    items = (parse_item(row, media_type) for row in payload.get("results", []))
    return [item for item in items if item is not None]


def format_runtime(minutes: int) -> str:
    if minutes <= 0:
        return ""
    hours, rest = divmod(minutes, 60)
    if hours and rest:
        return f"{hours}h {rest}m"
    return f"{hours}h" if hours else f"{rest}m"


def pick_trailer(videos: dict) -> str:
    """YouTube key of the best trailer: official trailers, then any, then teasers/clips."""
    clips = [
        clip
        for clip in videos.get("results", [])
        if clip.get("site") == "YouTube" and clip.get("key")
    ]
    ranking = (
        lambda clip: clip.get("type") == "Trailer" and clip.get("official") and int(clip.get("size") or 0) >= 1080,
        lambda clip: clip.get("type") == "Trailer" and clip.get("official"),
        lambda clip: clip.get("type") == "Trailer",
        lambda clip: clip.get("type") in ("Teaser", "Clip"),
    )
    for wanted in ranking:
        for clip in clips:
            if wanted(clip):
                return str(clip["key"])
    return ""


def pick_logo(images: dict) -> str:
    """Choose the best transparent official logo file_path from TMDB images."""
    logos = [
        logo for logo in images.get("logos", [])
        if logo.get("file_path")
    ]
    if not logos:
        return ""

    def logo_priority(logo: dict) -> tuple[int, float, int]:
        lang = logo.get("iso_639_1")
        is_en = 2 if lang == "en" else (1 if not lang else 0)
        votes = float(logo.get("vote_average") or 0.0)
        count = int(logo.get("vote_count") or 0)
        return (is_en, votes, count)

    logos.sort(key=logo_priority, reverse=True)
    return str(logos[0]["file_path"])


def pick_english_image(images: list[dict], fallback: str) -> str:
    """Choose the best artwork with language EN (English), avoiding textless artwork."""
    en_candidates = [
        img for img in images
        if img.get("iso_639_1") == "en" and img.get("file_path")
    ]
    if en_candidates:
        en_candidates.sort(
            key=lambda img: (
                int(img.get("vote_count") or 0),
                float(img.get("vote_average") or 0.0),
            ),
            reverse=True,
        )
        return str(en_candidates[0]["file_path"])
    return fallback


def pick_textless_image(images: list[dict], fallback: str) -> str:
    """Choose the best textless backdrop (iso_639_1 is None), suitable for overlaying UI."""
    textless_candidates = [
        img for img in images
        if img.get("iso_639_1") is None and img.get("file_path")
    ]
    if textless_candidates:
        textless_candidates.sort(
            key=lambda img: (
                int(img.get("vote_count") or 0),
                float(img.get("vote_average") or 0.0),
            ),
            reverse=True,
        )
        return str(textless_candidates[0]["file_path"])
    return fallback


def _certification(raw: dict, media_type: str, region: str) -> str:
    countries = [region, "US"] if region != "US" else ["US"]
    if media_type == "movie":
        entries = raw.get("release_dates", {}).get("results", [])
        for country in countries:
            for entry in entries:
                if entry.get("iso_3166_1") == country:
                    for release in entry.get("release_dates", []):
                        if release.get("certification"):
                            return str(release["certification"])
        return ""
    entries = raw.get("content_ratings", {}).get("results", [])
    for country in countries:
        for entry in entries:
            if entry.get("iso_3166_1") == country and entry.get("rating"):
                return str(entry["rating"])
    return ""


def parse_details(raw: dict, media_type: str, region: str = "US") -> MediaDetails:
    base = {**raw, "media_type": media_type}
    item = parse_item(
        {**base, "genre_ids": [g.get("id") for g in raw.get("genres", [])]},
        media_type,
    )
    if item is None:
        raise ApiError("TMDB returned an unreadable title.")

    cast = tuple(
        person["name"]
        for person in raw.get("credits", {}).get("cast", [])[:8]
        if person.get("name")
    )
    if media_type == "movie":
        credit_label = "Director"
        credits = tuple(
            person["name"]
            for person in raw.get("credits", {}).get("crew", [])
            if person.get("job") == "Director" and person.get("name")
        )[:2]
        runtime = format_runtime(int(raw.get("runtime") or 0))
    else:
        credit_label = "Creator"
        credits = tuple(p["name"] for p in raw.get("created_by", []) if p.get("name"))[:2]
        seasons = int(raw.get("number_of_seasons") or 0)
        runtime = f"{seasons} Season{'s' if seasons != 1 else ''}" if seasons else ""

    imgs = raw.get("images", {})
    en_backdrop = pick_english_image(imgs.get("backdrops", []), item.backdrop_path)
    textless_backdrop = pick_textless_image(imgs.get("backdrops", []), item.backdrop_path)
    en_poster = pick_english_image(imgs.get("posters", []), item.poster_path)

    from dataclasses import replace
    updated_item = replace(item, backdrop_path=en_backdrop, poster_path=en_poster)

    return MediaDetails(
        item=updated_item,
        tagline=str(raw.get("tagline") or ""),
        runtime_text=runtime,
        certification=_certification(raw, media_type, region),
        genres=tuple(g["name"] for g in raw.get("genres", []) if g.get("name")),
        cast=cast,
        credit_label=credit_label,
        credits=credits,
        trailer_key=pick_trailer(raw.get("videos", {})),
        status=str(raw.get("status") or ""),
        logo_path=pick_logo(imgs),
        english_backdrop_path=en_backdrop,
        textless_backdrop_path=textless_backdrop,
        english_poster_path=en_poster,
    )


# ── Client ──────────────────────────────────────────────────────────────────
class TmdbClient:
    """Thin, thread-safe TMDB client with a small on-disk response cache.

    A fresh cache entry avoids the request entirely; a stale one is served when
    the network is down, which is the app's offline mode.
    """

    def __init__(
        self,
        api_key: str | None = None,
        session: requests.Session | None = None,
        cache_dir: Path | None = None,
        language: str = "en-US",
        region: str | None = None,
    ) -> None:
        self._key = api_key if api_key is not None else get_key("TMDB_API_KEY")
        self._session = session or requests.Session()
        self._cache_dir = (cache_dir or CACHE_DIR) / "tmdb"
        self._language = language
        self._region = (region if region is not None else get_key("TMDB_REGION")).upper()

    # ── Provider interface ──────────────────────────────────────────────────
    @property
    def available(self) -> bool:
        return bool(self._key)

    def fetch_row(self, spec: RowSpec, media_type: str) -> list[MediaItem]:
        if spec.source == "trending":
            return self.trending(media_type)
        if spec.source == "genre":
            return self.discover(media_type, int(spec.arg))
        return self.category(media_type, spec.arg)

    def trending(self, media_type: str, window: str = "week") -> list[MediaItem]:
        payload = self._get(f"/trending/{media_type}/{window}")
        return parse_items(payload, media_type)

    def trending_today(self, media_type: str) -> list[MediaItem]:
        """Daily trending -- used for the Top 10 Today panel."""
        payload = self._get(f"/trending/{media_type}/day", ttl=LIST_TTL)
        return parse_items(payload, media_type)[:10]

    def category(self, media_type: str, name: str) -> list[MediaItem]:
        if name not in _CATEGORIES.get(media_type, ()):
            raise ValueError(f"Unknown {media_type} category: {name}")
        params = {"region": self._region} if self._region and media_type == "movie" else {}
        return parse_items(self._get(f"/{media_type}/{name}", **params), media_type)

    def discover(self, media_type: str, genre_id: int) -> list[MediaItem]:
        payload = self._get(
            f"/discover/{media_type}",
            with_genres=genre_id,
            sort_by="popularity.desc",
            **{"vote_count.gte": 100, "include_adult": "false"},
        )
        return parse_items(payload, media_type)

    def search(self, media_type: str, query: str) -> list[MediaItem]:
        query = query.strip()
        if not query:
            return []
        payload = self._get(
            f"/search/{media_type}", query=query, include_adult="false", ttl=SEARCH_TTL
        )
        return parse_items(payload, media_type)

    def details(self, media_type: str, ident: int) -> MediaDetails:
        extra = "release_dates" if media_type == "movie" else "content_ratings"
        raw = self._get(
            f"/{media_type}/{ident}",
            ttl=DETAIL_TTL,
            append_to_response=f"videos,credits,images,{extra}",
            include_image_language="en,null",
        )
        return parse_details(raw, media_type, self._region or "US")

    # ── HTTP + cache ────────────────────────────────────────────────────────
    def _get(self, path: str, ttl: int = LIST_TTL, **params) -> dict:  # type: ignore[misc]
        if not self._key:
            raise MissingApiKey("No TMDB API key is configured.")

        params = {"language": self._language, **params}
        cache_file = self._cache_path(path, params)
        cached = self._read_cache(cache_file)
        if cached is not None and time.time() - cached[0] < ttl:
            return cached[1]

        headers = {"Accept": "application/json"}
        # TMDB issues both a short v3 key and a long v4 read-access token.
        if len(self._key) > 40:
            headers["Authorization"] = f"Bearer {self._key}"
        else:
            params["api_key"] = self._key

        try:
            response = self._session.get(
                API_BASE + path, params=params, headers=headers, timeout=(5, 12)
            )
        except requests.RequestException as exc:
            if cached is not None:
                return cached[1]
            raise NetworkError(
                "Can't reach TMDB. Check your connection and try again."
            ) from exc

        if response.status_code == 401:
            raise ApiError("TMDB rejected the API key. Check TMDB_API_KEY in .env.")
        if response.status_code == 429:
            if cached is not None:
                return cached[1]
            raise ApiError("TMDB is rate limiting requests. Try again in a moment.")
        if not response.ok:
            if cached is not None:
                return cached[1]
            raise ApiError(f"TMDB returned an error (HTTP {response.status_code}).")

        try:
            data = response.json()
        except ValueError as exc:
            raise ApiError("TMDB sent an unreadable response.") from exc
        self._write_cache(cache_file, data)
        return data

    def _cache_path(self, path: str, params: dict) -> Path:
        # The key is never part of the cache identity or the file contents.
        safe = {k: v for k, v in params.items() if k not in ("api_key",)}
        ident = path + json.dumps(safe, sort_keys=True, default=str)
        return self._cache_dir / (hashlib.sha1(ident.encode()).hexdigest() + ".json")

    @staticmethod
    def _read_cache(path: Path) -> tuple[float, dict] | None:
        try:
            blob = json.loads(path.read_text(encoding="utf-8"))
            return float(blob["t"]), blob["data"]
        except (OSError, ValueError, KeyError, TypeError):
            return None

    @staticmethod
    def _write_cache(path: Path, data: dict) -> None:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps({"t": time.time(), "data": data}), encoding="utf-8")
        except OSError:
            pass  # caching is best-effort
