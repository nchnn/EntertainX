"""Time-synced auto-scrolling lyrics panel highlighting lines in real time."""

from __future__ import annotations

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter
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

from theme import theme_manager as theme
from ui.components.icons import make_icon
from ui.components.music.audio_engine import get_audio_engine
from ui.components.music.models import LyricLine, Track


class LyricRowWidget(QLabel):
    """Clickable lyric line with highlighted active state."""

    clicked = Signal(int)  # time_ms

    def __init__(self, line: LyricLine, parent: QWidget | None = None) -> None:
        super().__init__(line.text or "• • •", parent)
        self.line = line
        self._is_active = False

        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setWordWrap(True)
        self.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.setContentsMargins(12, 10, 12, 10)
        self._apply_style()

    def set_active(self, active: bool) -> None:
        if self._is_active != active:
            self._is_active = active
            self._apply_style()

    def _apply_style(self) -> None:
        if self._is_active:
            self.setStyleSheet(
                f"color: {theme.TEXT_PRIMARY}; font-size: 20px; font-weight: 700; "
                f"background-color: rgba(255, 255, 255, 0.06); border-radius: 8px;"
            )
        else:
            self.setStyleSheet(
                f"color: {theme.TEXT_MUTED}; font-size: 16px; font-weight: 500; "
                f"background: transparent;"
            )

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.line.time_ms)
            event.accept()
            return
        super().mousePressEvent(event)


class LyricsView(QFrame):
    """Time-synced lyrics view matching streaming service presentation."""

    close_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._engine = get_audio_engine()
        self._lyrics: list[LyricLine] = []
        self._rows: list[LyricRowWidget] = []
        self._active_index: int = -1

        self.setObjectName("LyricsView")
        self.setStyleSheet(
            f"QFrame#LyricsView {{ background-color: {theme.BG_DARK}; "
            f"border-left: 1px solid {theme.BORDER}; }}"
        )
        self.setMinimumWidth(320)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        # ── Header ──────────────────────────────────────────────────────────
        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        header_row.setSpacing(8)

        self.title_label = QLabel("Lyrics")
        self.title_label.setStyleSheet(
            f"color: {theme.TEXT_PRIMARY}; font-size: {theme.FONT_SIZE_LG}px; font-weight: 700;"
        )
        header_row.addWidget(self.title_label, 1)

        self.btn_close = QPushButton()
        self.btn_close.setFixedSize(28, 28)
        self.btn_close.setIcon(make_icon("close", theme.TEXT_MUTED, 16))
        self.btn_close.setStyleSheet("background: transparent; border: none;")
        self.btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_close.clicked.connect(self.close_requested.emit)
        header_row.addWidget(self.btn_close)

        main_layout.addLayout(header_row)

        self.track_info_label = QLabel("No track playing")
        self.track_info_label.setStyleSheet(
            f"color: {theme.TEXT_MUTED}; font-size: {theme.FONT_SIZE_XS}px;"
        )
        main_layout.addWidget(self.track_info_label)

        # ── Scroll Area ─────────────────────────────────────────────────────
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setStyleSheet(
            "QScrollArea { background: transparent; border: none; } "
            "QScrollBar:vertical { width: 6px; background: transparent; } "
            f"QScrollBar::handle:vertical {{ background: {theme.BORDER}; border-radius: 3px; }} "
            "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }"
        )

        self.lyrics_container = QWidget()
        self.lyrics_container.setStyleSheet("background: transparent;")
        self.lyrics_layout = QVBoxLayout(self.lyrics_container)
        self.lyrics_layout.setContentsMargins(0, 20, 0, 40)
        self.lyrics_layout.setSpacing(12)
        self.lyrics_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.scroll_area.setWidget(self.lyrics_container)
        main_layout.addWidget(self.scroll_area, 1)

        # Empty notice label
        self.empty_label = QLabel("No lyrics available for this song")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setStyleSheet(
            f"color: {theme.TEXT_MUTED}; font-size: {theme.FONT_SIZE_MD}px; padding: 40px 0;"
        )
        self.lyrics_layout.addWidget(self.empty_label)

        # ── Footer ──────────────────────────────────────────────────────────
        footer_label = QLabel("Lyrics provided by lrclib.net")
        footer_label.setStyleSheet(
            f"color: {theme.TEXT_DISABLED}; font-size: 10px; font-weight: 500;"
        )
        footer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(footer_label)

        # Connect audio engine
        self._engine.track_changed.connect(self._on_track_changed)
        self._engine.lyrics_loaded.connect(self._on_lyrics_loaded)
        self._engine.position_changed.connect(self._on_position_changed)

        if self._engine.current_track:
            self._on_track_changed(self._engine.current_track)
        if self._engine.current_lyrics:
            self._on_lyrics_loaded(self._engine.current_lyrics)

    def _on_track_changed(self, track: Track | None) -> None:
        if track:
            self.track_info_label.setText(f"{track.title} • {track.artist}")
        else:
            self.track_info_label.setText("No track playing")
            self._on_lyrics_loaded([])

    def _on_lyrics_loaded(self, lyrics: list[LyricLine]) -> None:
        self._lyrics = lyrics
        self._active_index = -1

        # Clear existing row widgets
        while self.lyrics_layout.count() > 0:
            item = self.lyrics_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        self._rows = []

        if not lyrics:
            self.empty_label = QLabel("No lyrics available for this song")
            self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.empty_label.setStyleSheet(
                f"color: {theme.TEXT_MUTED}; font-size: {theme.FONT_SIZE_MD}px; padding: 40px 0;"
            )
            self.lyrics_layout.addWidget(self.empty_label)
            return

        for line in lyrics:
            row = LyricRowWidget(line, parent=self.lyrics_container)
            row.clicked.connect(self._on_line_clicked)
            self.lyrics_layout.addWidget(row)
            self._rows.append(row)

    def _on_line_clicked(self, time_ms: int) -> None:
        self._engine.seek(time_ms)

    def _on_position_changed(self, pos_ms: int) -> None:
        if not self._rows or not self._lyrics:
            return

        # Find active line
        new_active = -1
        for i, line in enumerate(self._lyrics):
            if line.time_ms <= pos_ms:
                new_active = i
            else:
                break

        if new_active != self._active_index:
            self._active_index = new_active
            for i, row in enumerate(self._rows):
                row.set_active(i == self._active_index)

            # Auto-scroll active line into view
            if 0 <= self._active_index < len(self._rows):
                target_widget = self._rows[self._active_index]
                target_y = target_widget.pos().y()
                scroll_bar = self.scroll_area.verticalScrollBar()
                viewport_h = self.scroll_area.viewport().height()
                scroll_bar.setValue(max(0, target_y - viewport_h // 3))
