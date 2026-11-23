"""Modal detail panel for one title, laid over the page like Netflix's."""

from __future__ import annotations

from PySide6.QtCore import (
    QEasingCurve,
    QEvent,
    QRectF,
    QSize,
    Qt,
    QTimer,
    QUrl,
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
from ui.components.hover_preview import COUNTDOWN_MS, COUNTDOWN_STEP_MS, embed_hover_html
from ui.components.icons import make_icon

try:
    from PySide6.QtWebEngineWidgets import QWebEngineView
    _HAVE_WEBENGINE = True
except ImportError:
    _HAVE_WEBENGINE = False
    QWebEngineView = None  # type: ignore[assignment, misc]

HEADER_H = 300
PANEL_MAX_W = 880


class _Header(QWidget):
    """Artwork banner; the title and buttons are children painted on top."""

    close_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.pixmap: QPixmap | None = None
        self.details: MediaDetails | None = None
        self.setFixedHeight(HEADER_H)
        self.setMouseTracking(True)

        self._countdown_active = False
        self._countdown_progress = 0.0
        self._countdown_remaining = COUNTDOWN_MS
        self._is_playing = False

        self._countdown_timer = QTimer(self)
        self._countdown_timer.setInterval(COUNTDOWN_STEP_MS)
        self._countdown_timer.timeout.connect(self._on_countdown_tick)

        if _HAVE_WEBENGINE and QWebEngineView is not None:
            self.web_view = QWebEngineView(self)
            self.web_view.setGeometry(0, 0, self.width(), HEADER_H)
            self.web_view.titleChanged.connect(self._on_web_title)
            self.web_view.hide()
        else:
            self.web_view = None

    def _on_web_title(self, title: str) -> None:
        if title == "action:close":
            self.close_requested.emit()

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        if self.web_view is not None:
            self.web_view.setGeometry(0, 0, event.size().width(), HEADER_H)

    def enterEvent(self, event) -> None:  # noqa: N802
        super().enterEvent(event)
        if self.details and self.details.trailer_key and not self._is_playing:
            self.start_countdown()

    def leaveEvent(self, event) -> None:  # noqa: N802
        super().leaveEvent(event)
        self.stop_countdown()
        if self._is_playing:
            self.stop_trailer()

    def start_countdown(self) -> None:
        self._countdown_active = True
        self._countdown_progress = 0.0
        self._countdown_remaining = COUNTDOWN_MS
        self._countdown_timer.start()

    def stop_countdown(self) -> None:
        self._countdown_timer.stop()
        self._countdown_active = False
        self._countdown_progress = 0.0
        self.update()

    def _on_countdown_tick(self) -> None:
        self._countdown_remaining -= COUNTDOWN_STEP_MS
        self._countdown_progress = 1.0 - max(0.0, self._countdown_remaining) / float(COUNTDOWN_MS)
        if self._countdown_remaining <= 0:
            self.stop_countdown()
            self.start_trailer()
        self.update()

    def start_trailer(self, details: MediaDetails | None = None) -> None:
        d = details or self.details
        if d is None or not d.trailer_key:
            return
        if self.web_view is None:
            return
        self.stop_countdown()
        key = d.trailer_key
        logo_url = d.logo_url("w500") if d.logo_path else ""
        title = d.item.title if d.item else ""
        html = embed_hover_html(key, logo_url, title, muted=True, show_close=True)
        self.web_view.setHtml(html, QUrl("https://entertainx.local/"))
        self.web_view.setGeometry(0, 0, self.width(), HEADER_H)
        self.web_view.show()
        self.web_view.raise_()
        self._is_playing = True
        self.update()

    def stop_trailer(self) -> None:
        self.stop_countdown()
        self._is_playing = False
        if self.web_view is not None:
            self.web_view.setHtml("")
            self.web_view.hide()
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        bounds = QRectF(self.rect())
        radius = float(theme.RADIUS_XL)
        # Round only the top corners: clip a taller rounded rect.
        painter.setClipPath(rounded_path(bounds.adjusted(0, 0, 0, radius * 2), radius))
        painter.fillRect(bounds, QColor(theme.BG_ELEVATED))
        if not self._is_playing:
            if self.pixmap is not None and not self.pixmap.isNull():
                draw_cover(painter, bounds, self.pixmap, 0.5, 0.25)
            fill_vertical_scrim(painter, bounds, 0.30, 1.0, theme.BG_CARD)

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

        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        host.installEventFilter(self)
        self.hide()

        self.panel = QFrame(self)
        self.panel.setProperty("role", "detailPanel")
        outer = QVBoxLayout(self.panel)
        outer.setContentsMargins(1, 1, 1, 1)
        outer.setSpacing(0)

        # Header: artwork, title, buttons.
        self.header = _Header()
        self.header.close_requested.connect(self.close_overlay)
        head = QVBoxLayout(self.header)
        head.setContentsMargins(32, 20, 32, 24)
        head.setSpacing(theme.SPACE_SM)

        top = QHBoxLayout()
        top.addStretch(1)
        self.close_button = QPushButton()
        self.close_button.setProperty("variant", "ring")
        self.close_button.setFixedSize(38, 38)
        self.close_button.setIcon(make_icon("close", theme.TEXT_PRIMARY, 16))
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

        self.tagline_label = QLabel("")
        self.tagline_label.setProperty("role", "heroMeta")
        self.tagline_label.setWordWrap(True)
        head.addWidget(self.tagline_label)

        head.addSpacing(theme.SPACE_SM)
        buttons = QHBoxLayout()
        self.play_button = QPushButton("  Play Trailer")
        self.play_button.setProperty("variant", "hero")
        self.play_button.setIcon(make_icon("play", theme.TEXT_ON_ACCENT, 18))
        self.play_button.setIconSize(QSize(18, 18))
        self.play_button.setMinimumWidth(168)
        self.play_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.play_button.clicked.connect(self._on_play)
        buttons.addWidget(self.play_button)
        buttons.addStretch(1)
        head.addLayout(buttons)
        outer.addWidget(self.header)

        # Body: scrolls if a long cast list or overview needs room.
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        body = QWidget()
        column = QVBoxLayout(body)
        column.setContentsMargins(32, 8, 32, 28)
        column.setSpacing(theme.SPACE_MD)

        facts = QHBoxLayout()
        facts.setSpacing(theme.SPACE_MD)
        self.rating_label = QLabel("")
        self.rating_label.setProperty("role", "rating")
        self.facts_label = QLabel("")
        self.facts_label.setProperty("role", "muted")
        self.cert_label = QLabel("")
        self.cert_label.setProperty("role", "pill")
        facts.addWidget(self.rating_label)
        facts.addWidget(self.facts_label)
        facts.addWidget(self.cert_label)
        facts.addStretch(1)
        column.addLayout(facts)

        self.genres_row = QHBoxLayout()
        self.genres_row.setSpacing(theme.SPACE_SM)
        self.genres_row.addStretch(1)
        column.addLayout(self.genres_row)

        self.overview_label = QLabel("")
        self.overview_label.setWordWrap(True)
        self.overview_label.setProperty("role", "heroOverview")
        self.overview_label.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum
        )
        column.addWidget(self.overview_label)

        self.credit_label = QLabel("")
        self.credit_label.setWordWrap(True)
        self.credit_label.setTextFormat(Qt.TextFormat.PlainText)
        self.credit_label.setProperty("role", "muted")
        column.addWidget(self.credit_label)

        self.cast_label = QLabel("")
        self.cast_label.setWordWrap(True)
        self.cast_label.setProperty("role", "muted")
        column.addWidget(self.cast_label)

        self.status_label = QLabel("")
        self.status_label.setProperty("role", "caption")
        column.addWidget(self.status_label)
        column.addStretch(1)

        scroll.setWidget(body)
        outer.addWidget(scroll, 1)

    # ── Opening and closing ─────────────────────────────────────────────────
    def open(self, item: MediaItem) -> None:
        self.item = item
        self.details = None
        self.header.details = None
        self.header.stop_trailer()
        self.logo_label.setVisible(False)
        self.logo_label.clear()
        self.title_label.setVisible(True)
        self.title_label.setText(item.title)
        self.tagline_label.setText("")
        self.tagline_label.setVisible(False)
        self.rating_label.setText(f"\u2605 {item.rating:.1f}" if item.rating > 0 else "")
        self.facts_label.setText(
            "  \xb7  ".join(p for p in (item.year, item.kind_label) if p)
        )
        self.cert_label.setVisible(False)
        self._set_genres(item.genre_names)
        self.overview_label.setText(
            item.overview or "No synopsis is available for this title yet."
        )
        self.credit_label.setText("")
        self.cast_label.setText("")
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
        self.closed.emit()

    def set_details(self, details: MediaDetails) -> None:
        if self.item is None or details.item.key != self.item.key:
            return
        self.details = details
        self.header.details = details
        self.status_label.setText(details.status)
        backdrop_url = details.textless_backdrop_url("w1280") or details.backdrop_url("w1280")
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
            self.tagline_label.setVisible(True)
        facts = [
            p for p in (self.item.year, self.item.kind_label, details.runtime_text) if p
        ]
        self.facts_label.setText("  \xb7  ".join(facts))
        self.cert_label.setText(details.certification)
        self.cert_label.setVisible(bool(details.certification))
        if details.genres:
            self._set_genres(list(details.genres))
        if details.credits:
            self.credit_label.setText(
                f"{details.credit_label}: {', '.join(details.credits)}"
            )
        if details.cast:
            self.cast_label.setText(f"Starring: {', '.join(details.cast)}")
        if not details.trailer_key:
            self.play_button.setToolTip("No trailer is listed for this title.")

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
        if self.details and self.details.trailer_key and self.header.web_view is not None:
            self.header.start_trailer(self.details)
        elif self.item is not None:
            self.play_requested.emit(self.item)

    # ── Geometry ────────────────────────────────────────────────────────────
    def _fit(self) -> None:
        width = max(320, min(PANEL_MAX_W, self._host.width() - 64))
        height = max(420, min(self._host.height() - 48, 640))
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
