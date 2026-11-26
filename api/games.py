"""Games catalog adapter.

Fetches the Selenite game catalog (920+ titles) and resolves thumbnail
and embed URLs. Keyless, CORS-open, no auth required.
"""

from __future__ import annotations

import json
import urllib.request
from dataclasses import asdict, dataclass

CATALOG_URL = "https://selenite.cc/resources/games.json"
PRIMARY_IMAGE_BASE = "https://www.1tube.org/games/semag"
UPSTREAM_IMAGE_BASE = "https://selenite.cc/resources/semag"
EMBED_BASE = "https://selenite.cc/resources/semag"

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/134.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
}


@dataclass
class GameEntry:
    name: str
    directory: str
    image: str
    tags: list[str]
    thumbnail_url: str
    backup_thumbnail_url: str
    embed_url: str

    def to_dict(self) -> dict:
        return asdict(self)


class GamesCatalog:
    """Fetches, parses, and indexes the Selenite game catalog."""

    def __init__(self) -> None:
        self.games: list[GameEntry] = []
        self._by_directory: dict[str, GameEntry] = {}

    # -- Network ---------------------------------------------------------------

    def fetch_catalog(self, timeout: int = 15) -> list[GameEntry]:
        """Blocking fetch; call from a worker thread via run_async."""
        req = urllib.request.Request(CATALOG_URL, headers=_HEADERS)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw: list[dict] = json.loads(resp.read().decode("utf-8"))

        entries: list[GameEntry] = []
        for item in raw:
            name = item.get("name", "").strip()
            directory = item.get("directory", "").strip()
            image = item.get("image", "").strip()
            tags: list[str] = item.get("tags", [])

            if not name or not directory:
                continue

            entries.append(
                GameEntry(
                    name=name,
                    directory=directory,
                    image=image,
                    tags=tags,
                    thumbnail_url=f"{PRIMARY_IMAGE_BASE}/{directory}/{image}",
                    backup_thumbnail_url=f"{UPSTREAM_IMAGE_BASE}/{directory}/{image}",
                    embed_url=f"{EMBED_BASE}/{directory}/index.html",
                )
            )

        entries.sort(key=lambda g: g.name.lower())
        self.games = entries
        self._by_directory = {g.directory: g for g in entries}
        return self.games

    # -- Queries ---------------------------------------------------------------

    def all_tags(self) -> list[str]:
        """Sorted list of unique genre tags present in the catalog."""
        seen: set[str] = set()
        for g in self.games:
            seen.update(t.lower() for t in g.tags)
        return sorted(seen)

    def search(self, query: str = "", tag: str = "") -> list[GameEntry]:
        q = query.strip().lower()
        t = tag.strip().lower()
        results = self.games
        if t:
            results = [g for g in results if t in [x.lower() for x in g.tags]]
        if q:
            results = [g for g in results if q in g.name.lower()]
        return results

    def get_by_directory(self, directory: str) -> GameEntry | None:
        return self._by_directory.get(directory)
