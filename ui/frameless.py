"""Reusable frameless window with a custom title bar.

Windows keeps native resizing, snapping, and window menu behaviour because
``WM_NCHITTEST`` is answered directly, while the title bar uses Qt's
``startSystemMove`` for smooth, snap-aware dragging. Non-Windows platforms
still get a draggable window and a ``startSystemResize`` fallback.
"""

from __future__ import annotations

import ctypes
import sys
from ctypes import wintypes

from PySide6.QtCore import QEvent, QPoint, Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from theme import theme_manager as theme
from ui.components.icons import app_icon, brand_pixmap, make_icon

# winuser.h constants
_WM_NCHITTEST = 0x0084
_HTCLIENT = 1
_HTLEFT = 10
_HTRIGHT = 11
_HTTOP = 12
_HTTOPLEFT = 13
_HTTOPRIGHT = 14
_HTBOTTOM = 15
_HTBOTTOMLEFT = 16
_HTBOTTOMRIGHT = 17


class TitleBar(QWidget):
    """Brand strip with drag support and window controls."""

    minimize_requested = Signal()
    maximize_requested = Signal()
    close_requested = Signal()

    def __init__(self, title: str = "EntertainX", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("TitleBar")
        self.setFixedHeight(theme.TITLEBAR_HEIGHT)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._drag_offset: QPoint | None = None

        row = QHBoxLayout(self)
        row.setContentsMargins(theme.SPACE_MD, 0, 0, 0)
        # Window controls sit flush like a native title bar; only the brand
        # block needs an explicit gap.
        row.setSpacing(0)

        mark = QLabel()
        mark.setPixmap(brand_pixmap(20))
        mark.setFixedSize(20, 20)
        row.addWidget(mark, 0, Qt.AlignmentFlag.AlignVCenter)
        row.addSpacing(theme.SPACE_SM)

        self.title_label = QLabel(title)
        self.title_label.setProperty("role", "brand")
        row.addWidget(self.title_label, 0, Qt.AlignmentFlag.AlignVCenter)

        row.addStretch(1)

        self.minimize_button = self._window_button("minimize", "Minimize")
        self.maximize_button = self._window_button("maximize", "Maximize")
        self.close_button = self._window_button("close", "Close")
        self.close_button.setProperty("windowRole", "close")

        self.minimize_button.clicked.connect(self.minimize_requested)
        self.maximize_button.clicked.connect(self.maximize_requested)
        self.close_button.clicked.connect(self.close_requested)

        for button in (self.minimize_button, self.maximize_button, self.close_button):
            row.addWidget(button, 0, Qt.AlignmentFlag.AlignVCenter)

    # ── Construction helpers ────────────────────────────────────────────────
    def _window_button(self, icon_name: str, tooltip: str) -> QPushButton:
        button = QPushButton()
        button.setProperty("variant", "window")
        button.setIcon(make_icon(icon_name, theme.TEXT_SECONDARY, 16))
        button.setFixedSize(46, theme.TITLEBAR_HEIGHT)
        button.setToolTip(tooltip)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        return button

    # ── State ───────────────────────────────────────────────────────────────
    def set_maximized(self, maximized: bool) -> None:
        self.maximize_button.setIcon(
            make_icon("restore" if maximized else "maximize", theme.TEXT_SECONDARY, 16)
        )
        self.maximize_button.setToolTip("Restore" if maximized else "Maximize")

    # ── Dragging ────────────────────────────────────────────────────────────
    def _system_move(self) -> bool:
        window = self.window()
        handle = window.windowHandle() if window is not None else None
        if handle is None:
            return False
        try:
            return bool(handle.startSystemMove())
        except Exception:  # pragma: no cover - platform specific
            return False

    def mousePressEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        if event.button() == Qt.MouseButton.LeftButton and self._system_move():
            event.accept()
            return
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = (
                event.globalPosition().toPoint() - self.window().frameGeometry().topLeft()
            )
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if (
            self._drag_offset is not None
            and event.buttons() & Qt.MouseButton.LeftButton
        ):
            self.window().move(event.globalPosition().toPoint() - self._drag_offset)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        self._drag_offset = None
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self.maximize_requested.emit()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)


class FramelessWindow(QMainWindow):
    """A borderless main window with a shared title bar and swappable body."""

    EDGE_MARGIN = 7

    def __init__(self, title: str = "EntertainX", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setWindowIcon(app_icon())
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
        self.setMinimumSize(900, 620)

        self._root = QWidget()
        self._root.setObjectName("WindowRoot")
        shell = QVBoxLayout(self._root)
        shell.setContentsMargins(0, 0, 0, 0)
        shell.setSpacing(0)

        self._titlebar = TitleBar(title)
        shell.addWidget(self._titlebar)

        self._body = QWidget()
        self._body.setObjectName("BodyRoot")
        self._body_layout = QVBoxLayout(self._body)
        self._body_layout.setContentsMargins(0, 0, 0, 0)
        self._body_layout.setSpacing(0)
        shell.addWidget(self._body, 1)

        super().setCentralWidget(self._root)

        self._content: QWidget | None = None

        self._titlebar.minimize_requested.connect(self.showMinimized)
        self._titlebar.maximize_requested.connect(self.toggle_maximize)
        self._titlebar.close_requested.connect(self.close)

    # ── Content ─────────────────────────────────────────────────────────────
    @property
    def content(self) -> QWidget | None:
        return self._content

    @property
    def titlebar(self) -> TitleBar:
        return self._titlebar

    def set_content(self, widget: QWidget) -> None:
        """Replace everything below the title bar."""
        while self._body_layout.count():
            item = self._body_layout.takeAt(0)
            old = item.widget()
            if old is not None:
                old.setParent(None)
                old.deleteLater()
        self._content = widget
        self._body_layout.addWidget(widget)

    # ── Maximize / restore ──────────────────────────────────────────────────
    def is_maximized(self) -> bool:
        return bool(self.windowState() & Qt.WindowState.WindowMaximized)

    def toggle_maximize(self) -> None:
        if self.is_maximized():
            self.setWindowState(Qt.WindowState.WindowNoState)
        else:
            self.setWindowState(Qt.WindowState.WindowMaximized)

    def changeEvent(self, event) -> None:  # noqa: N802
        super().changeEvent(event)
        if event.type() == QEvent.Type.WindowStateChange:
            self._titlebar.set_maximized(self.is_maximized())

    # ── Native resize ───────────────────────────────────────────────────────
    def nativeEvent(self, event_type, message):  # noqa: N802
        if sys.platform == "win32":
            try:
                handled, result = self._windows_hit_test(message)
            except Exception:  # pragma: no cover - defensive, platform specific
                handled, result = False, 0
            if handled:
                return True, result
        return super().nativeEvent(event_type, message)

    def _windows_hit_test(self, message) -> tuple[bool, int]:
        msg = wintypes.MSG.from_address(int(message))
        if msg.message != _WM_NCHITTEST:
            return False, 0
        if self.is_maximized() or self.isFullScreen():
            return False, 0

        x = ctypes.c_short(msg.lParam & 0xFFFF).value
        y = ctypes.c_short((msg.lParam >> 16) & 0xFFFF).value

        rect = self.frameGeometry()
        margin = self.EDGE_MARGIN
        left = x < rect.left() + margin
        right = x >= rect.right() - margin
        top = y < rect.top() + margin
        bottom = y >= rect.bottom() - margin

        if top and left:
            return True, _HTTOPLEFT
        if top and right:
            return True, _HTTOPRIGHT
        if bottom and left:
            return True, _HTBOTTOMLEFT
        if bottom and right:
            return True, _HTBOTTOMRIGHT
        if left:
            return True, _HTLEFT
        if right:
            return True, _HTRIGHT
        if top:
            return True, _HTTOP
        if bottom:
            return True, _HTBOTTOM
        return False, 0
