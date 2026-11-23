"""In-app trailer player: a YouTube embed inside Qt WebEngine.

WebEngine is imported lazily so the rest of the app never pays for it, and a
missing or broken WebEngine degrades to a message instead of a crash.
"""

from __future__ import annotations

import re

from PySide6.QtCore import QUrl
from PySide6.QtWidgets import QDialog, QLabel, QVBoxLayout, QWidget

from theme import theme_manager as theme

_KEY = re.compile(r"^[A-Za-z0-9_-]{6,20}$")

# YouTube refuses embeds that arrive without a referrer (player error 153), and
# a bare ``setHtml`` page has none. Loading the page under an https base URL and
# asking for ``strict-origin-when-cross-origin`` gives the player one.
BASE_URL = "https://entertainx.local/"


def embed_html(key: str) -> str:
    """HTML page holding the privacy-enhanced player for ``key``."""
    if not _KEY.match(key):
        raise ValueError("not a YouTube video id")
    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        "<meta name='referrer' content='strict-origin-when-cross-origin'>"
        "<style>html,body{margin:0;height:100%;background:#000;overflow:hidden}"
        "iframe{border:0;width:100%;height:100%}</style></head><body>"
        f"<iframe src='https://www.youtube-nocookie.com/embed/{key}"
        "?autoplay=1&rel=0&modestbranding=1&playsinline=1' "
        "referrerpolicy='strict-origin-when-cross-origin' "
        "allow='autoplay; encrypted-media; picture-in-picture; fullscreen' "
        "allowfullscreen></iframe></body></html>"
    )


class TrailerDialog(QDialog):
    def __init__(self, title: str, key: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"{title} \u2014 Trailer")
        self.setModal(True)
        self.resize(960, 850)
        self.view = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        try:
            from PySide6.QtWebEngineWidgets import QWebEngineView

            html = embed_html(key)
        except (ImportError, ValueError) as exc:
            note = QLabel(
                "Trailer playback needs PySide6-WebEngine."
                if isinstance(exc, ImportError)
                else "This trailer link is not valid."
            )
            note.setProperty("role", "muted")
            note.setMargin(theme.SPACE_XL)
            layout.addWidget(note)
            return

        self.status = QLabel("Loading trailer\u2026")
        self.status.setProperty("role", "muted")
        self.status.setMargin(theme.SPACE_MD)
        layout.addWidget(self.status)

        self.view = QWebEngineView()
        self.view.loadFinished.connect(self._on_loaded)
        layout.addWidget(self.view, 1)
        self.view.setHtml(html, QUrl(BASE_URL))

    def _on_loaded(self, ok: bool) -> None:
        if ok:
            self.status.hide()
        else:
            self.status.setText(
                "The trailer could not be loaded. Check your connection."
            )

    def done(self, result: int) -> None:
        """Stop playback the moment the dialog closes."""
        if self.view is not None:
            self.view.setHtml("")
        super().done(result)
