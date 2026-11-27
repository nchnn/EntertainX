"""Modal detail panel for one title, laid over the page like Netflix's."""

from __future__ import annotations

from PySide6.QtCore import (
    QEasingCurve,
    QEvent,
    QRectF,
    QSize,
    Qt,
    QVariantAnimation,
    Signal,
)
from PySide6.QtGui import QColor, QKeyEvent, QPainter, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from api.images import ImageStore, get_store
from api.movies import MediaDetails, MediaItem
from theme import theme_manager as theme
from ui.components import motion
from ui.components.artwork import draw_cover, fill_vertical_scrim, rounded_path
from ui.components.icons import make_icon
from ui.components.trailer.player import (
    CountdownController,
    TrailerPlayer,
    TrailerSpec,
    render_trailer_html,
)

HEADER_H = 510
PANEL_MAX_W = 1140


def embed_modal_html(
    key: str,
    logo_url: str = "",
    title: str = "",
    muted: bool = False,
    in_watchlist: bool = False,
) -> str:
    """Delegate to :func:`render_trailer_html` with mode ``modal``."""
    return render_trailer_html(
        "modal",
        TrailerSpec(
            key=key,
            title=title,
            logo_url=logo_url,
            muted=muted,
            in_watchlist=in_watchlist,
        ),
    )


class _Header(QWidget):
    """Artwork banner; the title and buttons are children painted on top."""

    close_requested = Signal()
    play_requested = Signal()
    watchlist_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.pixmap: QPixmap | None = None
        self.details: MediaDetails | None = None
        self.setFixedHeight(HEADER_H)
        self.setMouseTracking(True)

        self._countdown = CountdownController(parent=self)
        self._countdown.progressed.connect(self._on_countdown_progress)
        self._countdown.completed.connect(self._on_countdown_complete)
        self._countdown_progress = 0.0

        self._player = TrailerPlayer(mode="modal", parent=self)
        self._player.action_triggered.connect(self._on_action)
        self._player.playback_stopped.connect(self._on_playback_stopped)
        self._player.hide()

    @property
    def _countdown_active(self) -> bool:
        return self._countdown.is_active

    @property
    def _is_playing(self) -> bool:
        return self._player.is_playing

    @property
    def web_view(self):
        """Backward-compatible accessor for tests that inspect the web view."""
        vp = self._player.viewport
        return vp.widget() if vp is not None else None

    def _on_action(self, action: str) -> None:
        if action == "close":
            self.close_requested.emit()
        elif action == "play":
            self.play_requested.emit()
        elif action == "watchlist":
            self.watchlist_requested.emit()

    def _on_playback_stopped(self) -> None:
        self.update()

    def _on_countdown_progress(self, progress: float) -> None:
        self._countdown_progress = progress
        self.update()

    def _on_countdown_complete(self) -> None:
        self._countdown_progress = 1.0
        self.start_trailer()

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        w, h = event.size().width(), HEADER_H
        self._player.setGeometry(0, 0, w, h)

    def enterEvent(self, event) -> None:  # noqa: N802
        super().enterEvent(event)
        if self.details and self.details.trailer_key and not self._is_playing:
            self.start_countdown()

    def leaveEvent(self, event) -> None:  # noqa: N802
        super().leaveEvent(event)
        self.stop_countdown()

    def start_countdown(self) -> None:
        self._countdown.start()

    def stop_countdown(self) -> None:
        self._countdown.stop()
        self._countdown_progress = 0.0
        self.update()

    def _on_countdown_tick(self) -> None:
        """Kept for backward compatibility with tests that call this directly."""
        self._countdown.tick()

    def start_trailer(self, details: MediaDetails | None = None) -> None:
        d = details or self.details
        if d is None or not d.trailer_key:
            return
        if not self._player.available:
            return
        self.stop_countdown()
        logo_url = d.logo_url("w500") if d.logo_path else ""
        backdrop_url = (
            d.backdrop_url("w1280")
            or (d.item.backdrop_url("w1280") if d.item else "")
        )
        title = d.item.title if d.item else ""
        spec = TrailerSpec(
            key=d.trailer_key,
            title=title,
            logo_url=logo_url,
            backdrop_url=backdrop_url,
            muted=False,
        )
        self._player.setGeometry(0, 0, self.width(), HEADER_H)
        self._player.load(spec)
        self.update()

    def stop_trailer(self) -> None:
        self.stop_countdown()
        self._player.stop()
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        bounds = QRectF(self.rect())
        radius = float(theme.RADIUS_XL)
        # Round only the top corners: clip a taller rounded rect.
        painter.setClipPath(rounded_path(bounds.adjusted(0, 0, 0, radius * 2), radius))
        painter.fillRect(bounds, QColor("#18181b"))
        if not self._is_playing:
            if self.pixmap is not None and not self.pixmap.isNull():
                draw_cover(painter, bounds, self.pixmap, 0.5, 0.25)
            fill_vertical_scrim(painter, bounds, 0.30, 1.0, "#18181b")

            if self._countdown_active and self._countdown_progress > 0:
                prog_w = bounds.width() * min(1.0, max(0.0, self._countdown_progress))
                if prog_w > 0:
                    painter.setPen(Qt.PenStyle.NoPen)
                    painter.fillRect(
                        QRectF(bounds.left(), bounds.bottom() - 4, bounds.width(), 4),
                        QColor(255, 255, 255, 45),
                    )
                    painter.fillRect(
                        QRectF(bounds.left(), bounds.bottom() - 4, prog_w, 4),
                        QColor(theme.PRIMARY),
                    )
        painter.end()


class TitleDetailOverlay(QWidget):
    play_requested = Signal(object)  # MediaItem
    closed = Signal()

    def __init__(
        self,
        host: QWidget,
        store: ImageStore | None = None,
    ) -> None:
        super().__init__(host)
        self._host = host
        self._store = store
        self.item: MediaItem | None = None
        self.details: MediaDetails | None = None
        self._scrim = 0.0
        self._fade: QVariantAnimation | None = None
        self._in_watchlist = False
        self._auto_play = False

        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        host.installEventFilter(self)
        self.hide()

        self.panel = QFrame(self)
        self.panel.setProperty("role", "detailPanel")
        outer = QVBoxLayout(self.panel)
        outer.setContentsMargins(1, 1, 1, 1)
        outer.setSpacing(0)

        # Header: artwork banner, close button, title and action controls.
        self.header = _Header()
        self.header.close_requested.connect(self.close_overlay)
        self.header.play_requested.connect(self._on_play)
        self.header.watchlist_requested.connect(self._toggle_watchlist)
        head = QVBoxLayout(self.header)
        head.setContentsMargins(36, 20, 36, 24)
        head.setSpacing(theme.SPACE_SM)

        top = QHBoxLayout()
        top.addStretch(1)
        self.close_button = QPushButton()
        self.close_button.setProperty("variant", "ring")
        self.close_button.setFixedSize(44, 44)
        self.close_button.setIcon(make_icon("close", theme.TEXT_PRIMARY, 20))
        self.close_button.setIconSize(QSize(20, 20))
        self.close_button.setToolTip("Close")
        self.close_button.setAccessibleName("Close details")
        self.close_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_button.clicked.connect(self.close_overlay)
        top.addWidget(self.close_button)
        head.addLayout(top)
        head.addStretch(1)

        self.logo_label = QLabel()
        self.logo_label.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom
        )
        self.logo_label.setVisible(False)
        head.addWidget(self.logo_label)

        self.title_label = QLabel("")
        self.title_label.setProperty("role", "detailTitle")
        self.title_label.setWordWrap(True)
        head.addWidget(self.title_label)

        self.tagline_label = QLabel(self.header)
        self.tagline_label.setProperty("role", "heroMeta")
        self.tagline_label.setWordWrap(True)
        self.tagline_label.hide()

        head.addSpacing(theme.SPACE_SM)
        buttons = QHBoxLayout()
        buttons.setSpacing(12)

        self.play_button = QPushButton("  Play")
        self.play_button.setProperty("variant", "modalPlay")
        self.play_button.setIcon(make_icon("play", "#000000", 18))
        self.play_button.setIconSize(QSize(18, 18))
        self.play_button.setFixedHeight(44)
        self.play_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.play_button.clicked.connect(self._on_play)
        buttons.addWidget(self.play_button)

        self.watchlist_button = QPushButton()
        self.watchlist_button.setProperty("variant", "ring")
        self.watchlist_button.setFixedSize(44, 44)
        self.watchlist_button.setIcon(make_icon("plus", theme.TEXT_PRIMARY, 20))
        self.watchlist_button.setIconSize(QSize(20, 20))
        self.watchlist_button.setToolTip("Add to My List")
        self.watchlist_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.watchlist_button.clicked.connect(self._toggle_watchlist)
        buttons.addWidget(self.watchlist_button)

        buttons.addStretch(1)
        head.addLayout(buttons)
        
        # Entire modal content: header and movie details scroll together.
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        scroll.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )

        # Container for both the trailer header and movie details.
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # Trailer header is now part of the scrollable content.
        content_layout.addWidget(self.header)

        # Movie details body.
        body = QWidget()
        body.setStyleSheet("background: transparent;")


        main_layout = QHBoxLayout(body)
        main_layout.setContentsMargins(36, 18, 36, 36)
        main_layout.setSpacing(32)

        # Left Column (62% width: Specs & Overview)
        left_col = QVBoxLayout()
        left_col.setSpacing(14)

        specs_row = QHBoxLayout()
        specs_row.setSpacing(10)

        self.year_label = QLabel("")
        self.year_label.setStyleSheet("color: #ffffff; font-size: 15px; font-weight: 700;")
        specs_row.addWidget(self.year_label)

        self.runtime_label = QLabel("")
        self.runtime_label.setStyleSheet("color: rgba(255, 255, 255, 0.85); font-size: 14px;")
        specs_row.addWidget(self.runtime_label)

        self.cert_label = QLabel("")
        self.cert_label.setStyleSheet(
            "background: rgba(255, 255, 255, 0.12); border: 1px solid rgba(255, 255, 255, 0.35); "
            "border-radius: 4px; padding: 2px 7px; font-size: 11px; font-weight: 700; color: #ffffff;"
        )
        specs_row.addWidget(self.cert_label)

        self.quality_badge = QLabel("HD")
        self.quality_badge.setStyleSheet(
            "border: 1px solid rgba(255, 255, 255, 0.35); border-radius: 4px; "
            "padding: 1px 6px; font-size: 10px; font-weight: 700; color: rgba(255, 255, 255, 0.9);"
        )
        specs_row.addWidget(self.quality_badge)

        self.rating_label = QLabel("")
        self.rating_label.setStyleSheet("color: #f5a623; font-size: 14px; font-weight: 700;")
        specs_row.addWidget(self.rating_label)

        self.facts_label = QLabel("")
        self.facts_label.setProperty("role", "muted")
        specs_row.addWidget(self.facts_label)

        specs_row.addStretch(1)
        left_col.addLayout(specs_row)

        self.genres_row = QHBoxLayout()
        self.genres_row.setSpacing(8)
        self.genres_row.addStretch(1)
        left_col.addLayout(self.genres_row)

        self.overview_label = QLabel("")
        self.overview_label.setWordWrap(True)
        self.overview_label.setStyleSheet(
            "color: rgba(255, 255, 255, 0.92); font-size: 14px; line-height: 1.55;"
        )
        left_col.addWidget(self.overview_label)

        self.credit_label = QLabel("")
        self.credit_label.setWordWrap(True)
        self.credit_label.setProperty("role", "muted")
        left_col.addWidget(self.credit_label)

        self.status_label = QLabel("")
        self.status_label.setProperty("role", "caption")
        left_col.addWidget(self.status_label)

        left_col.addStretch(1)
        main_layout.addLayout(left_col, 62)

        # Right Column (38% width: Cast, Genres, Mood tags)
        right_col = QVBoxLayout()
        right_col.setSpacing(14)

        self.cast_label = QLabel("")
        self.cast_label.setWordWrap(True)
        self.cast_label.setTextFormat(Qt.TextFormat.RichText)
        self.cast_label.setStyleSheet("font-size: 13px; line-height: 1.45;")
        right_col.addWidget(self.cast_label)

        self.genres_label = QLabel("")
        self.genres_label.setWordWrap(True)
        self.genres_label.setTextFormat(Qt.TextFormat.RichText)
        self.genres_label.setStyleSheet("font-size: 13px; line-height: 1.45;")
        right_col.addWidget(self.genres_label)

        self.mood_label = QLabel("")
        self.mood_label.setWordWrap(True)
        self.mood_label.setTextFormat(Qt.TextFormat.RichText)
        self.mood_label.setStyleSheet("font-size: 13px; line-height: 1.45;")
        right_col.addWidget(self.mood_label)

        right_col.addStretch(1)
        main_layout.addLayout(right_col, 38)

        content_layout.addWidget(body)
        self.scroll = scroll
        self.scroll.setWidget(content)
        outer.addWidget(self.scroll, 1)

    # ── Opening and closing ─────────────────────────────────────────────────
    def open(self, item: MediaItem, auto_play: bool = False) -> None:
        self.scroll.verticalScrollBar().setValue(0)
        self.item = item
        self.details = None
        self._auto_play = auto_play
        self._in_watchlist = False
        self.header.details = None
        self.header.stop_trailer()
        self.logo_label.setVisible(False)
        self.logo_label.clear()
        self.title_label.setVisible(True)
        self.title_label.setText(item.title)
        self.tagline_label.setText("")
        self.tagline_label.setVisible(False)
        self.year_label.setText(item.year)
        self.runtime_label.setText("")
        self.cert_label.setText("")
        self.cert_label.setVisible(False)
        self.rating_label.setText(f"\u2605 {item.rating:.1f}" if item.rating > 0 else "")
        self.facts_label.setText(
            "  \xb7  ".join(p for p in (item.year, item.kind_label) if p)
        )
        self._set_genres(item.genre_names)
        self.overview_label.setText(
            item.overview or "No synopsis is available for this title yet."
        )
        self.credit_label.setText("")
        self.cast_label.setText("")
        self.genres_label.setText("")
        self.mood_label.setText("")
        self.status_label.setText("Loading details\u2026")
        self.play_button.setAccessibleName(f"Play trailer for {item.title}")

        self.header.pixmap = None
        self.header.update()
        (self._store or get_store()).request(
            item.backdrop_url("w1280") or item.poster_url("w780"),
            1280,
            self._on_art,
            owner=self,
        )

        self._set_top_nav_visible(False)
        self._fit()
        self.setGeometry(self._host.rect())
        self.raise_()
        self.show()
        self.setFocus()
        self._animate_scrim(0.0, 1.0, 240)
        motion.reveal(self.panel, duration=340, rise=22.0)

    def close_overlay(self) -> None:
        if not self.isVisible():
            return
        self.header.stop_trailer()
        self.hide()
        self.item = None
        self._auto_play = False
        self._set_top_nav_visible(True)
        self.closed.emit()

    def hideEvent(self, event) -> None:  # noqa: N802
        super().hideEvent(event)
        self._set_top_nav_visible(True)

    def closeEvent(self, event) -> None:  # noqa: N802
        if event is not None:
            super().closeEvent(event)
        self._set_top_nav_visible(True)

    def _set_top_nav_visible(self, visible: bool) -> None:
        host = getattr(self, "_host", None)
        win = host.window() if host is not None else self.window()
        if win is not None:
            content = getattr(win, "content", None)
            top_bar = getattr(content, "top_bar", None) if content is not None else None
            if top_bar is None:
                from ui.content_area import TopNavBar
                top_bar = win.findChild(TopNavBar)
            if top_bar is not None and top_bar.isVisible() != visible:
                top_bar.setVisible(visible)

    def set_details(self, details: MediaDetails) -> None:
        if self.item is None or details.item.key != self.item.key:
            return
        self.details = details
        self.header.details = details
        self.status_label.setText(details.status)
        backdrop_url = details.backdrop_url("w1280")
        if backdrop_url:
            (self._store or get_store()).request(
                backdrop_url,
                1280,
                self._on_art,
                owner=self,
            )
        if details.logo_path:
            (self._store or get_store()).request(
                details.logo_url("w500"),
                500,
                self._on_logo,
                owner=self,
            )
        else:
            self.logo_label.setVisible(False)
            self.title_label.setVisible(True)
            self.title_label.setText(details.item.title)
        if details.tagline:
            self.tagline_label.setText(details.tagline)

        if self.item:
            self.year_label.setText(self.item.year)
        self.runtime_label.setText(details.runtime_text)
        self.cert_label.setText(details.certification or "PG-13")
        self.cert_label.setVisible(True)

        facts = [
            p for p in (self.item.year if self.item else "", self.item.kind_label if self.item else "", details.runtime_text) if p
        ]
        self.facts_label.setText("  \xb7  ".join(facts))
        if details.genres:
            self._set_genres(list(details.genres))
        if details.credits:
            self.credit_label.setText(
                f"{details.credit_label}: {', '.join(details.credits)}"
            )

        if details.cast:
            cast_names = ", ".join(details.cast[:6])
            self.cast_label.setText(f'<span style="color: #777;">Cast: </span><span style="color: #fff;">{cast_names}</span>')
        else:
            self.cast_label.setText("")

        if details.genres:
            genres_names = ", ".join(details.genres[:4])
            self.genres_label.setText(f'<span style="color: #777;">Genres: </span><span style="color: #fff;">{genres_names}</span>')
        else:
            self.genres_label.setText("")

        if details.tagline:
            self.mood_label.setText(f'<span style="color: #777;">This Movie Is: </span><span style="color: #fff;">{details.tagline.lower()}</span>')
        elif details.genres:
            moods = ", ".join(g.lower() for g in details.genres[:3])
            self.mood_label.setText(f'<span style="color: #777;">This Movie Is: </span><span style="color: #fff;">{moods}</span>')
        else:
            self.mood_label.setText("")

        if not details.trailer_key:
            self.play_button.setToolTip("No trailer is listed for this title.")
        elif self._auto_play:
            self.header.start_trailer(details)

    def _toggle_watchlist(self) -> None:
        self._in_watchlist = not self._in_watchlist
        if self._in_watchlist:
            self.watchlist_button.setIcon(make_icon("check", theme.TEXT_PRIMARY, 20))
            self.watchlist_button.setToolTip("In My List")
        else:
            self.watchlist_button.setIcon(make_icon("plus", theme.TEXT_PRIMARY, 20))
            self.watchlist_button.setToolTip("Add to My List")
        if self.header._is_playing:
            self.header._player.set_watchlist_state(self._in_watchlist)

    def _on_logo(self, pixmap: QPixmap | None) -> None:
        if self.item is None or pixmap is None or pixmap.isNull():
            self.logo_label.setVisible(False)
            self.title_label.setVisible(True)
            return
        scaled = pixmap.scaled(
            340,
            85,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.logo_label.setPixmap(scaled)
        self.logo_label.setVisible(True)
        self.title_label.setVisible(False)

    def set_error(self, message: str) -> None:
        self.status_label.setText(message)

    # ── Content helpers ─────────────────────────────────────────────────────
    def _set_genres(self, names: list[str]) -> None:
        while self.genres_row.count() > 1:
            item = self.genres_row.takeAt(0)
            if item is None:
                break
            widget = item.widget()
            if widget is not None:
                widget.hide()
                widget.setParent(None)
                widget.deleteLater()
        for name in names[:5]:
            chip = QLabel(name)
            chip.setProperty("role", "pill")
            self.genres_row.insertWidget(self.genres_row.count() - 1, chip)

    def _on_art(self, pixmap: QPixmap | None) -> None:
        self.header.pixmap = pixmap
        self.header.update()

    def _on_play(self) -> None:
        """Hand the title to the full player; the trailer stays a hover preview."""
        if self.item is not None:
            self.play_requested.emit(self.item)

    # ── Geometry ────────────────────────────────────────────────────────────
    def _fit(self) -> None:
        width = max(320, min(PANEL_MAX_W, self._host.width() - 48))
        height = max(540, min(self._host.height() - 32, 920))
        self.panel.setFixedSize(width, height)
        self.panel.move(
            (self._host.width() - width) // 2,
            (self._host.height() - height) // 2,
        )

    def eventFilter(self, watched, event) -> bool:  # noqa: N802
        if watched is self._host and event.type() == QEvent.Type.Resize and self.isVisible():
            self.setGeometry(self._host.rect())
            self._fit()
        return super().eventFilter(watched, event)

    # ── Scrim and input ─────────────────────────────────────────────────────
    def _animate_scrim(self, start: float, end: float, duration: int) -> None:
        if self._fade is not None:
            self._fade.stop()
        if not motion.motion_enabled():
            self._scrim = end
            self.update()
            return
        fade = QVariantAnimation(self)
        fade.setStartValue(start)
        fade.setEndValue(end)
        fade.setDuration(duration)
        fade.setEasingCurve(QEasingCurve.Type.OutCubic)
        fade.valueChanged.connect(self._on_scrim)
        self._fade = fade
        fade.start()

    def _on_scrim(self, value) -> None:
        self._scrim = float(value)
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        veil = QColor("#000000")
        veil.setAlphaF(0.72 * self._scrim)
        painter.fillRect(self.rect(), veil)
        painter.end()

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if not self.panel.geometry().contains(event.position().toPoint()):
            self.close_overlay()
        event.accept()

    def wheelEvent(self, event) -> None:  # noqa: N802
        event.accept()

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802
        if event.key() == Qt.Key.Key_Escape:
            self.close_overlay()
            return
        super().keyPressEvent(event)
