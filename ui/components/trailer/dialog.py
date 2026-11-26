"""Standalone modal dialog hosting :class:`TrailerPlayer` in simple mode."""

from __future__ import annotations

from PySide6.QtWidgets import QDialog, QLabel, QVBoxLayout, QWidget

from theme import theme_manager as theme
from ui.components.trailer.player import TrailerPlayer, TrailerSpec, ViewportFactory


class TrailerDialog(QDialog):
    def __init__(
        self,
        title: str,
        key: str,
        parent: QWidget | None = None,
        viewport_factory: ViewportFactory | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"{title} - Trailer")
        self.setModal(True)
        self.resize(960, 850)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.status = QLabel("Loading trailer\u2026")
        self.status.setProperty("role", "muted")
        self.status.setMargin(theme.SPACE_MD)
        layout.addWidget(self.status)

        self.player = TrailerPlayer(
            mode="simple",
            viewport_factory=viewport_factory,
            parent=self,
        )
        self.player.load_finished.connect(self._on_loaded)
        self.player.load_failed.connect(self._on_failed)
        layout.addWidget(self.player, 1)

        if not self.player.load(TrailerSpec(key=key, title=title)):
            self.player.hide()

    def _on_loaded(self, ok: bool) -> None:
        if ok:
            self.status.hide()
        else:
            self.status.setText(
                "The trailer could not be loaded. Check your connection."
            )
            self.status.show()

    def _on_failed(self, message: str) -> None:
        self.status.setText(message)
        self.status.show()

    def done(self, result: int) -> None:
        """Stop playback the moment the dialog closes."""
        self.player.stop()
        super().done(result)
