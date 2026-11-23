"""Poster and backdrop loading with an on-disk and an in-memory cache.

Downloading and decoding happen on worker threads (``QImage`` is thread-safe,
``QPixmap`` is not); the pixmap is created on the GUI thread when the result
arrives. Requests for the same picture are merged, and each picture is scaled
once to the width the caller will actually paint.
"""

from __future__ import annotations

import hashlib
from collections import OrderedDict
from collections.abc import Callable
from pathlib import Path

import requests
from PySide6.QtCore import QObject, Qt
from PySide6.QtGui import QImage, QPixmap
from shiboken6 import isValid

from api.config import CACHE_DIR
from api.tasks import run_async

Callback = Callable[[QPixmap | None], None]
Fetcher = Callable[[str], bytes]


def _http_fetch(url: str) -> bytes:
    response = requests.get(url, timeout=(5, 15))
    response.raise_for_status()
    return response.content


class ImageStore(QObject):
    def __init__(
        self,
        cache_dir: Path | None = None,
        fetch: Fetcher | None = None,
        memory_items: int = 120,
    ) -> None:
        super().__init__()
        self._dir = (cache_dir or CACHE_DIR) / "images"
        self._fetch = fetch or _http_fetch
        self._limit = memory_items
        self._memory: OrderedDict[tuple[str, int], QPixmap] = OrderedDict()
        self._pending: dict[tuple[str, int], list[tuple[Callback, QObject | None]]] = {}

    def cached(self, url: str, width: int) -> QPixmap | None:
        pixmap = self._memory.get((url, width))
        if pixmap is not None:
            self._memory.move_to_end((url, width))
        return pixmap

    def request(
        self,
        url: str,
        width: int,
        callback: Callback,
        owner: QObject | None = None,
    ) -> None:
        """Deliver the picture at ``url`` (scaled to ``width`` px) to ``callback``.

        ``callback`` gets ``None`` when the picture cannot be loaded. It runs on
        the GUI thread, and is skipped if ``owner`` was deleted in the meantime.
        """
        if not url:
            callback(None)
            return
        key = (url, width)
        hit = self.cached(url, width)
        if hit is not None:
            callback(hit)
            return
        waiting = self._pending.get(key)
        if waiting is not None:
            waiting.append((callback, owner))
            return
        self._pending[key] = [(callback, owner)]
        run_async(
            self._load,
            url,
            width,
            on_done=lambda image: self._finish(key, image),
            on_error=lambda _error: self._finish(key, None),
        )

    # ── Worker side ─────────────────────────────────────────────────────────
    def _load(self, url: str, width: int) -> QImage:
        path = self._dir / (hashlib.sha1(url.encode()).hexdigest() + ".img")
        data: bytes | None = None
        try:
            data = path.read_bytes()
        except OSError:
            pass
        if data is None:
            data = self._fetch(url)
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
            except OSError:
                pass
        image = QImage.fromData(data)
        if image.isNull():
            raise ValueError("undecodable image")
        if width and image.width() > width:
            image = image.scaledToWidth(width, Qt.TransformationMode.SmoothTransformation)
        return image

    # ── GUI side ────────────────────────────────────────────────────────────
    def _finish(self, key: tuple[str, int], image: QImage | None) -> None:
        pixmap = QPixmap.fromImage(image) if image is not None else None
        if pixmap is not None:
            self._memory[key] = pixmap
            while len(self._memory) > self._limit:
                self._memory.popitem(last=False)
        for callback, owner in self._pending.pop(key, []):
            if owner is None or isValid(owner):
                callback(pixmap)


_store: ImageStore | None = None


def get_store() -> ImageStore:
    """The shared store used by every page."""
    global _store
    if _store is None:
        _store = ImageStore()
    return _store
