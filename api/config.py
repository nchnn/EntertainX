"""Environment and cache locations shared by every API adapter.

Secrets live in a git-ignored ``.env`` file (see ``.env.example``); nothing in
the source tree carries a key.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CACHE_DIR = ROOT / ".cache"


@lru_cache(maxsize=1)
def _load_env() -> None:
    try:
        from dotenv import load_dotenv
        load_dotenv(ROOT / ".env", override=False)
    except ImportError:
        pass


def get_key(name: str) -> str:
    """Return the value of ``name`` from the environment or ``.env``, else ``""``."""
    _load_env()
    return os.environ.get(name, "").strip().strip("\"'")
