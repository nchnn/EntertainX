"""GamePlayerWidget: embedded Chromium view for Selenite HTML5 games.

Lives inside a QStackedWidget; never spawns an external browser.
Subclasses QWebEnginePage to block popup windows at the engine layer.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtWebEngineCore import (
    QWebEnginePage,
    QWebEngineProfile,
    QWebEngineSettings,
)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from theme import theme_manager as theme
from ui.components.icons import make_icon


class _NoPopupPage(QWebEnginePage):
    """Block every window.open() call; free game sites use it for ads."""

    def createWindow(self, _type) -> None:  # type: ignore[override]
        return None


class GamePlayerWidget(QWidget):
    """Self-contained in-app game player using QWebEngineView."""

    close_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("GamePlayerWidget")
        self._is_fullscreen = False
        self._setup_ui()

    # -- Build -----------------------------------------------------------------

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header bar
        self._header = QWidget()
        self._header.setFixedHeight(48)
        self._header.setStyleSheet(
            f"background-color: {theme.BG_ELEVATED}; "
            f"border-bottom: 1px solid {theme.BORDER};"
        )
        hdr_layout = QHBoxLayout(self._header)
        hdr_layout.setContentsMargins(theme.SPACE_LG, 0, theme.SPACE_MD, 0)
        hdr_layout.setSpacing(theme.SPACE_MD)

        # Back button
        self._btn_back = QPushButton()
        self._btn_back.setIcon(make_icon("chevron", theme.TEXT_SECONDARY, 16, rotate=180))
        self._btn_back.setFixedSize(32, 32)
        self._btn_back.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_back.setToolTip("Back to games")
        self._btn_back.setStyleSheet(
            f"""
            QPushButton {{
                background-color: rgba(255,255,255,0.08);
                border: 1px solid {theme.BORDER};
                border-radius: 16px;
            }}
            QPushButton:hover {{
                background-color: rgba(255,255,255,0.14);
            }}
            """
        )
        self._btn_back.clicked.connect(self._on_back)
        hdr_layout.addWidget(self._btn_back)

        self._title_label = QLabel("Playing")
        self._title_label.setStyleSheet(
            f"color: {theme.TEXT_PRIMARY}; font-weight: 600; font-size: 14px;"
        )
        hdr_layout.addWidget(self._title_label, 1)

        # Mute button
        self._muted = False
        self._btn_mute = QPushButton()
        self._btn_mute.setIcon(make_icon("volume-2", theme.TEXT_SECONDARY, 16))
        self._btn_mute.setFixedSize(32, 32)
        self._btn_mute.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_mute.setToolTip("Mute / Unmute")
        self._btn_mute.setStyleSheet(self._btn_back.styleSheet())
        self._btn_mute.clicked.connect(self._toggle_mute)
        hdr_layout.addWidget(self._btn_mute)

        # Fullscreen button
        self._btn_fs = QPushButton()
        self._btn_fs.setIcon(make_icon("maximize", theme.TEXT_SECONDARY, 16))
        self._btn_fs.setFixedSize(32, 32)
        self._btn_fs.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_fs.setToolTip("Fullscreen")
        self._btn_fs.setStyleSheet(self._btn_back.styleSheet())
        self._btn_fs.clicked.connect(self._toggle_fullscreen)
        hdr_layout.addWidget(self._btn_fs)

        layout.addWidget(self._header)

        # Chromium embed
        profile = QWebEngineProfile("entertainx_games", self)
        self._page = _NoPopupPage(profile, self)
        self._configure_settings(self._page.settings())
        self._page.fullScreenRequested.connect(self._handle_fs_request)

        self._web_view = QWebEngineView(self)
        self._web_view.setPage(self._page)
        layout.addWidget(self._web_view, 1)

    @staticmethod
    def _configure_settings(s: QWebEngineSettings) -> None:
        on = QWebEngineSettings.WebAttribute
        s.setAttribute(on.JavascriptEnabled, True)
        s.setAttribute(on.LocalStorageEnabled, True)
        s.setAttribute(on.WebGLEnabled, True)
        s.setAttribute(on.Accelerated2dCanvasEnabled, True)
        s.setAttribute(on.FullScreenSupportEnabled, True)
        s.setAttribute(on.PlaybackRequiresUserGesture, False)
        s.setAttribute(on.JavascriptCanOpenWindows, False)

    # -- Public API ------------------------------------------------------------

    def load_game(self, name: str, embed_url: str) -> None:
        self._title_label.setText(name)
        self._muted = False
        self._page.setAudioMuted(False)
        self._btn_mute.setIcon(make_icon("volume-2", theme.TEXT_SECONDARY, 16))
        self._web_view.setUrl(QUrl(embed_url))

    def stop_game(self) -> None:
        """Unload the page so WebGL/WASM heaps are freed."""
        self._web_view.setUrl(QUrl("about:blank"))

    # -- Controls --------------------------------------------------------------

    def _on_back(self) -> None:
        self.stop_game()
        self.close_requested.emit()

    def _toggle_mute(self) -> None:
        self._muted = not self._muted
        self._page.setAudioMuted(self._muted)
        icon_name = "volume-x" if self._muted else "volume-2"
        color = theme.WARNING if self._muted else theme.TEXT_SECONDARY
        self._btn_mute.setIcon(make_icon(icon_name, color, 16))

    def _toggle_fullscreen(self) -> None:
        win = self.window()
        if self._is_fullscreen:
            win.showNormal()
            self._header.show()
            self._is_fullscreen = False
            self._btn_fs.setIcon(make_icon("maximize", theme.TEXT_SECONDARY, 16))
        else:
            win.showFullScreen()
            self._header.hide()
            self._is_fullscreen = True
            self._btn_fs.setIcon(make_icon("minimize", theme.PRIMARY, 16))

    def _handle_fs_request(self, request) -> None:
        request.accept()
        if request.toggleOn():
            self.window().showFullScreen()
            self._header.hide()
            self._is_fullscreen = True
        else:
            self.window().showNormal()
            self._header.show()
            self._is_fullscreen = False
