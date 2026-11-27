from __future__ import annotations

import os
from typing import Callable

from PySide6.QtCore import (
    Property,
    QEasingCurve,
    QEvent,
    QPoint,
    QPropertyAnimation,
    QRect,
    QRectF,
    QSize,
    Qt,
    QVariantAnimation,
    Signal,
)
from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from theme import theme_manager as theme
from ui.components.form_fields import IconLineEdit
from ui.components.icons import make_icon

from auth.auth_manager import AuthManager

from ui.pages.movies import MoviesPage
from ui.pages.tv_shows import TVShowsPage
from ui.pages.music import MusicPage
from ui.pages.games import GamesPage
from ui.pages.my_lists import MyListsPage
from ui.pages.settings import SettingsPage


class SegmentedToggle(QWidget):
    """Segmented pill switch with an animated sliding highlight capsule."""

    tab_clicked = Signal(int)

    def __init__(self, tabs: list[str], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._tabs = tabs
        self._current_index = 0
        self.setFixedHeight(36)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setObjectName("SegmentedToggle")
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        font = QFont("Segoe UI", 10)
        font.setPixelSize(13)
        self.setFont(font)

        self.setStyleSheet("""
            QWidget#SegmentedToggle {
                background-color: rgba(255, 255, 255, 0.08);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 18px;
            }
        """)

        self._highlight_pill = QWidget(self)
        self._highlight_pill.setObjectName("HighlightPill")
        self._highlight_pill.setStyleSheet("""
            QWidget#HighlightPill {
                background-color: #E8AAB9;
                border-radius: 16px;
            }
        """)

        self._buttons: list[QPushButton] = []
        for i, title in enumerate(tabs):
            btn = QPushButton(title, self)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFixedHeight(32)
            btn.setFont(font)
            btn.setProperty("variant", "tab")
            btn.clicked.connect(lambda checked=False, idx=i: self._on_btn_clicked(idx))
            self._buttons.append(btn)

        self._anim = QPropertyAnimation(self._highlight_pill, b"geometry", self)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.setDuration(220)
        self.setFixedWidth(self._content_width())

    @property
    def buttons(self) -> list[QPushButton]:
        return self._buttons

    def _tab_widths(self) -> list[int]:
        metrics = self.fontMetrics()
        widths: list[int] = []
        for title in self._tabs:
            widths.append(max(metrics.horizontalAdvance(title) + 36, 84))
        return widths

    def _content_width(self) -> int:
        if not self._tabs:
            return 4
        return sum(self._tab_widths()) + 4

    def _spans(self) -> list[tuple[int, int]]:
        spans: list[tuple[int, int]] = []
        x = 2
        for width in self._tab_widths():
            spans.append((x, width))
            x += width
        return spans

    def sizeHint(self) -> QSize:
        return QSize(self._content_width(), 36)

    def minimumSizeHint(self) -> QSize:
        return self.sizeHint()

    def _target_rect(self, index: int) -> QRect:
        spans = self._spans()
        if index < 0 or index >= len(spans):
            return QRect(2, 2, 0, 32)
        x, width = spans[index]
        return QRect(x, 2, width, 32)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if not self._tabs:
            return
        for i, btn in enumerate(self._buttons):
            x, width = self._spans()[i]
            btn.setGeometry(x, 2, width, 32)
            btn.raise_()
        if self._current_index < 0:
            self._highlight_pill.hide()
        else:
            self._highlight_pill.show()
            self._highlight_pill.setGeometry(self._target_rect(self._current_index))
        self._update_button_styles()

    def set_active_index(self, index: int, animate: bool = True) -> None:
        if index < 0 or index >= len(self._tabs):
            return
        self._current_index = index
        self._highlight_pill.setVisible(True)
        target = self._target_rect(index)
        if self._anim.state() == QPropertyAnimation.State.Running:
            self._anim.stop()
        if animate and os.environ.get("ENTERTAINX_REDUCE_MOTION") != "1" and self.isVisible():
            self._anim.setStartValue(self._highlight_pill.geometry())
            self._anim.setEndValue(target)
            self._anim.start()
        else:
            self._highlight_pill.setGeometry(target)
        self._update_button_styles()

    def _on_btn_clicked(self, index: int) -> None:
        self.set_active_index(index, animate=True)
        self.tab_clicked.emit(index)

    def set_all_inactive(self) -> None:
        """Deactivate all buttons (no pill highlight)."""
        self._current_index = -1
        self._highlight_pill.setVisible(False)
        self._update_button_styles()

    def _update_button_styles(self) -> None:
        for i, btn in enumerate(self._buttons):
            active = i == self._current_index
            btn.setProperty("active", "true" if active else "false")
            if active:
                btn.setStyleSheet("""
                    QPushButton {
                        color: #1A1719;
                        font-weight: 700;
                        font-size: 13px;
                        font-family: 'Figtree', 'Segoe UI', -apple-system, sans-serif;
                        background: transparent;
                        border: none;
                        padding: 0px 14px;
                    }
                """)
            else:
                btn.setStyleSheet("""
                    QPushButton {
                        color: #9E979B;
                        font-weight: 500;
                        font-size: 13px;
                        font-family: 'Figtree', 'Segoe UI', -apple-system, sans-serif;
                        background: transparent;
                        border: none;
                        padding: 0px 14px;
                    }
                    QPushButton:hover {
                        color: #F4F1F2;
                    }
                """)


class ExpandingSearchField(QWidget):
    """Circular search button that smoothly expands into an input field on focus."""

    expanded = Signal()
    collapsed = Signal()
    layout_changed = Signal()

    def __init__(self, inner_edit: IconLineEdit, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.inner_edit = inner_edit
        self.inner_edit.setParent(self)
        self.setFixedHeight(36)
        self._collapsed_w = 36
        self._expanded_w = 230
        self.setFixedWidth(self._collapsed_w)

        self._btn = QPushButton(self)
        self._btn.setIcon(make_icon("search", theme.TEXT_MUTED, 16))
        self._btn.setFixedSize(36, 36)
        self._btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn.setToolTip("Search (Ctrl+K)")
        self._btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.08);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 18px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.14);
                border-color: rgba(255, 255, 255, 0.22);
            }
        """)
        self._btn.clicked.connect(self.expand)

        self.inner_edit.setVisible(False)
        self.inner_edit.setFixedHeight(36)
        self.inner_edit.setStyleSheet("""
            QLineEdit {
                background-color: rgba(255, 255, 255, 0.08);
                border: 1px solid #E8AAB9;
                border-radius: 18px;
                color: #F4F1F2;
                padding-left: 12px;
                padding-right: 28px;
                font-size: 13px;
                font-family: 'Figtree', 'Segoe UI', -apple-system, sans-serif;
            }
        """)
        self.inner_edit.installEventFilter(self)

        self._anim = QPropertyAnimation(self, b"field_width", self)
        self._anim.setDuration(200)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    def _get_field_width(self) -> int:
        return self.width()

    def _set_field_width(self, w: int) -> None:
        self.setFixedWidth(w)
        if self.inner_edit.isVisible():
            self.inner_edit.setGeometry(0, 0, w, 36)
        self.layout_changed.emit()

    field_width = Property(int, _get_field_width, _set_field_width)

    def expand(self) -> None:
        already = self.inner_edit.isVisible() and self.width() >= self._expanded_w - 2
        self._btn.setVisible(False)
        self.inner_edit.setVisible(True)
        self.inner_edit.setGeometry(0, 0, self.width(), 36)
        self.inner_edit.setFocus()
        if not already:
            self.expanded.emit()
        self._animate_to(self._expanded_w)

    def collapse(self) -> None:
        if self.inner_edit.text().strip():
            return
        self._animate_to(self._collapsed_w, on_finish=self._on_collapsed)

    def _on_collapsed(self) -> None:
        self.inner_edit.setVisible(False)
        self._btn.setVisible(True)
        self.collapsed.emit()

    def _animate_to(self, w: int, on_finish: Callable | None = None) -> None:
        if self._anim.state() == QPropertyAnimation.State.Running:
            self._anim.stop()
        if os.environ.get("ENTERTAINX_REDUCE_MOTION") == "1":
            self._set_field_width(w)
            if on_finish:
                on_finish()
            return
        self._anim.setStartValue(self.width())
        self._anim.setEndValue(w)
        try:
            self._anim.finished.disconnect()
        except Exception:
            pass
        if on_finish:
            self._anim.finished.connect(on_finish)
        self._anim.start()

    def eventFilter(self, watched, event: QEvent) -> bool:
        if watched is self.inner_edit:
            if event.type() == QEvent.Type.FocusIn:
                self.expand()
            elif event.type() == QEvent.Type.FocusOut:
                self.collapse()
            elif event.type() == QEvent.Type.KeyPress:
                if hasattr(event, "key") and event.key() == Qt.Key.Key_Escape:  # type: ignore[union-attr]
                    self.inner_edit.clear()
                    self.inner_edit.clearFocus()
                    self.collapse()
                    return True
        return super().eventFilter(watched, event)


class SavedNavButton(QPushButton):
    """Pill button for Saved / Watchlist with an accent badge count."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("Saved", parent)
        self.setObjectName("SavedButton")
        self.setAccessibleName("Saved")
        self.setFixedHeight(36)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setIcon(make_icon("list", theme.TEXT_MUTED, 15))
        self.setToolTip("Saved Titles (My Lists)")

        self.badge = QLabel("3", self)
        self.badge.setObjectName("SavedBadge")
        self.badge.setFixedSize(20, 20)
        self.badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.badge.setStyleSheet("""
            QLabel#SavedBadge {
                background-color: #E8AAB9;
                color: #1A1719;
                border-radius: 10px;
                font-weight: 700;
                font-size: 11px;
                font-family: 'Figtree', 'Segoe UI', -apple-system, sans-serif;
            }
        """)

        self.setProperty("active", "false")
        self._update_style()

    def set_badge_count(self, count: int) -> None:
        self.badge.setText(str(count))
        self.badge.setVisible(count > 0)

    def set_active(self, active: bool) -> None:
        self.setProperty("active", "true" if active else "false")
        self.setIcon(make_icon("list", theme.PRIMARY if active else theme.TEXT_MUTED, 15))
        self._update_style()

    def _update_style(self) -> None:
        active = self.property("active") == "true"
        if active:
            self.setStyleSheet("""
                QPushButton#SavedButton {
                    background-color: rgba(232, 170, 185, 0.16);
                    border: 1px solid #E8AAB9;
                    border-radius: 18px;
                    color: #E8AAB9;
                    font-size: 13px;
                    font-weight: 600;
                    font-family: 'Figtree', 'Segoe UI', -apple-system, sans-serif;
                    text-align: left;
                    padding-left: 14px;
                    padding-right: 36px;
                }
            """)
        else:
            self.setStyleSheet("""
                QPushButton#SavedButton {
                    background-color: rgba(255, 255, 255, 0.08);
                    border: 1px solid rgba(255, 255, 255, 0.12);
                    border-radius: 18px;
                    color: #F4F1F2;
                    font-size: 13px;
                    font-weight: 500;
                    font-family: 'Figtree', 'Segoe UI', -apple-system, sans-serif;
                    text-align: left;
                    padding-left: 14px;
                    padding-right: 36px;
                }
                QPushButton#SavedButton:hover {
                    background-color: rgba(255, 255, 255, 0.14);
                    border-color: rgba(255, 255, 255, 0.22);
                }
            """)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.badge.move(self.width() - 28, (self.height() - 20) // 2)


class TopNavBar(QWidget):
    """Sticky top navigation bar: transparent at top, frosted glass pill when scrolled."""

    saved_clicked = Signal()
    settings_requested = Signal()
    theme_requested = Signal()
    logout_requested = Signal()

    def __init__(
        self,
        content_area: ContentArea | None = None,
        user: dict | None = None,
        on_theme: Callable | None = None,
        on_settings: Callable | None = None,
        on_logout: Callable | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("TabBar")
        self.setFixedHeight(64)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        self._content_area = content_area
        self._user = user or {}
        self._on_theme = on_theme
        self._on_settings = on_settings
        self._on_logout = on_logout
        self._menu_open = False
        self._scroll_progress = 0.0
        self._scrolled = False

        self._scroll_anim = QVariantAnimation(self)
        self._scroll_anim.setDuration(220)
        self._scroll_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._scroll_anim.valueChanged.connect(self._on_scroll_anim_step)

        # ── Left Section (reserved; category switch lives on the sidebar) ────
        self._left_container = QWidget(self)
        self._left_layout = QHBoxLayout(self._left_container)
        self._left_layout.setContentsMargins(0, 0, 0, 0)
        self._left_layout.setSpacing(0)
        self._left_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        # ── Center Section: section tabs (Movies / TV, game modes, …) ──────
        self._center_container = QWidget(self)
        self.center_layout = QHBoxLayout(self._center_container)
        self.center_layout.setContentsMargins(0, 0, 0, 0)
        self.center_layout.setSpacing(0)
        self.center_layout.setAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)

        # ── Right Section: search, genre, Saved, profile ────────────────────
        self._right_container = QWidget(self)
        self._right_layout = QHBoxLayout(self._right_container)
        self._right_layout.setContentsMargins(0, 0, 0, 0)
        self._right_layout.setSpacing(theme.SPACE_SM)
        self._right_layout.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.search_stack = QStackedWidget(self._right_container)
        self.search_stack.setFixedHeight(36)
        self._right_layout.addWidget(self.search_stack, 0, Qt.AlignmentFlag.AlignVCenter)

        self.saved_button = SavedNavButton(self._right_container)
        self.saved_button.clicked.connect(self._on_saved_clicked)
        self._right_layout.addWidget(self.saved_button, 0, Qt.AlignmentFlag.AlignVCenter)

        self.profile_button = QPushButton("I", self._right_container)
        self.profile_button.setObjectName("ProfileButton")
        self.profile_button.setAccessibleName("Profile")
        self.profile_button.setFixedSize(36, 36)
        self.profile_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.profile_button.setStyleSheet("""
            QPushButton#ProfileButton {
                background-color: #E8AAB9;
                color: #1A1719;
                border: 1px solid rgba(255, 255, 255, 0.25);
                border-radius: 18px;
                font-family: 'Instrument Serif', Georgia, serif;
                font-weight: 700;
                font-size: 16px;
                padding: 0px;
            }
            QPushButton#ProfileButton:hover {
                background-color: #F3C2CE;
                border-color: #FFFFFF;
            }
        """)
        self._update_profile_avatar(self._user)
        self.profile_button.clicked.connect(self._show_profile_menu)
        self._right_layout.addWidget(self.profile_button, 0, Qt.AlignmentFlag.AlignVCenter)

    def setup_search_stack(self, movies_toolbar: QWidget, tv_toolbar: QWidget) -> None:
        self.search_stack.addWidget(movies_toolbar)
        self.search_stack.addWidget(tv_toolbar)
        blank = QWidget()
        self.search_stack.addWidget(blank)
        for toolbar in (movies_toolbar, tv_toolbar):
            self._adopt_video_toolbar(toolbar)

    def _adopt_video_toolbar(self, toolbar: QWidget) -> None:
        """Turn the page search into a collapsed icon and keep the genre pill beside it."""
        layout = toolbar.layout()
        if layout is None:
            return
        edits = toolbar.findChildren(IconLineEdit)
        if not edits:
            return
        edit = edits[0]
        edit.setMinimumWidth(0)
        edit.setMaximumWidth(16777215)
        edit.setMinimumHeight(36)
        edit.setMaximumHeight(36)
        field = ExpandingSearchField(edit, toolbar)
        field.layout_changed.connect(self._layout_sections)
        layout.insertWidget(0, field)
        combos = toolbar.findChildren(QComboBox)
        if combos:
            combo = combos[0]
            field.expanded.connect(lambda c=combo: self._set_nav_combo_visible(c, False))
            field.collapsed.connect(lambda c=combo: self._set_nav_combo_visible(c, True))

    def _set_nav_combo_visible(self, combo: QComboBox, visible: bool) -> None:
        combo.setVisible(visible)
        self._layout_sections()

    def set_search_index(self, index: int) -> None:
        if index < self.search_stack.count():
            self.search_stack.setCurrentIndex(index)

    def show_video_search(self, visible: bool) -> None:
        self.search_stack.setVisible(visible)
        if not visible and self.search_stack.count() > 2:
            self.search_stack.setCurrentIndex(2)

    def _on_saved_clicked(self) -> None:
        self.saved_clicked.emit()
        if self._content_area is not None:
            self._content_area.show_category("My Lists")

    def _update_profile_avatar(self, user: dict) -> None:
        username = user.get("username", "User") if user else "User"
        initial = (username.strip() or "U")[0].upper()
        self.profile_button.setText(initial)

        email = user.get("email", "") if user else ""
        email_line = f"<br><span style='color:#B8B2B5;'>{email}</span>" if email else ""
        tooltip = (
            f"<b>{username}</b>{email_line}<br>"
            f"<span style='color:#8FC9A8; font-size:11px;'>Signed in</span><br>"
            f"<span style='color:{theme.PRIMARY}; font-size:11px;'>Click for Profile, Theme & Logout</span>"
        )
        self.profile_button.setToolTip(tooltip)

    def set_user_session(
        self,
        user: dict | None,
        on_theme: Callable | None = None,
        on_settings: Callable | None = None,
        on_logout: Callable | None = None,
    ) -> None:
        self._user = user or {}
        if on_theme is not None:
            self._on_theme = on_theme
        if on_settings is not None:
            self._on_settings = on_settings
        if on_logout is not None:
            self._on_logout = on_logout
        self._update_profile_avatar(self._user)

    def _show_profile_menu(self) -> None:
        self._menu_open = True
        menu = QMenu(self)
        menu.setObjectName("UserMenu")

        action_profile = menu.addAction(make_icon("user", theme.PRIMARY, 16), "Profile & Settings")
        action_theme = menu.addAction(make_icon("palette", theme.TEXT_SECONDARY, 16), "Customize Theme...")
        menu.addSeparator()
        action_logout = menu.addAction(make_icon("logout", theme.DANGER, 16), "Log Out")

        pt = self.profile_button.mapToGlobal(QPoint(0, self.profile_button.height() + 4))
        chosen = menu.exec(pt)
        self._menu_open = False

        if chosen == action_profile:
            if self._on_settings is not None:
                self._on_settings()
            elif self._content_area is not None:
                self._content_area.show_category("Settings")
            else:
                self.settings_requested.emit()
        elif chosen == action_theme:
            if self._on_theme is not None:
                self._on_theme()
            else:
                self.theme_requested.emit()
        elif chosen == action_logout:
            if self._on_logout is not None:
                self._on_logout()
            else:
                self.logout_requested.emit()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._layout_sections()

    def on_content_scroll(self, scroll_y: int) -> None:
        """Called by ContentArea when the page scrolls."""
        should_scroll = scroll_y > 40
        if should_scroll == self._scrolled:
            return
        self._scrolled = should_scroll
        target = 1.0 if should_scroll else 0.0
        if self._scroll_anim.state() == QVariantAnimation.State.Running:
            self._scroll_anim.stop()
        if os.environ.get("ENTERTAINX_REDUCE_MOTION") == "1":
            self._scroll_progress = target
            self.update()
            return
        self._scroll_anim.setStartValue(self._scroll_progress)
        self._scroll_anim.setEndValue(target)
        self._scroll_anim.start()

    def _on_scroll_anim_step(self, value: float) -> None:
        self._scroll_progress = value
        self.update()

    def paintEvent(self, event) -> None:
        """Draw background: transparent at top, frosted glass pill when scrolled."""
        p = self._scroll_progress
        if p <= 0.001:
            return  # fully transparent at top
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        # Frosted pill background
        bg = QColor(28, 27, 28, int(220 * p))  # #1c1b1c with alpha
        border_c = QColor(80, 76, 83, int(180 * p))  # theme.BORDER with alpha
        inset = int(12 * p)
        rect = QRectF(inset, 4, self.width() - 2 * inset, self.height() - 8)
        radius = 22.0
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(bg)
        painter.drawRoundedRect(rect, radius, radius)
        # Subtle border
        from PySide6.QtGui import QPen
        painter.setPen(QPen(border_c, 1.0))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(rect, radius, radius)
        painter.end()

    def _layout_sections(self) -> None:
        total_w = self.width()
        total_h = self.height()
        if total_w <= 0 or total_h <= 0:
            return

        # 1. Center Section: exact mathematical center
        center_hint = self._center_container.sizeHint()
        center_w = max(center_hint.width(), 160)
        center_x = (total_w - center_w) // 2

        # 2. Right Section: aligned to right edge with 16px right margin
        right_margin = 16
        right_hint = self._right_container.sizeHint()
        right_w = right_hint.width()
        right_x = max(center_x + center_w + theme.SPACE_MD, total_w - right_w - right_margin)
        right_w_actual = max(0, total_w - right_x - right_margin)
        self._right_container.setGeometry(right_x, 0, right_w_actual, total_h)

        # 3. Left Section: aligned to left edge with 16px left margin
        left_margin = 16
        max_left_w = max(0, center_x - left_margin - theme.SPACE_MD)
        left_hint = self._left_container.sizeHint()
        left_w = min(left_hint.width(), max_left_w)
        self._left_container.setGeometry(left_margin, 0, left_w, total_h)

        self._center_container.setGeometry(center_x, 0, center_w, total_h)


class ContentArea(QWidget):
    category_changed = Signal(str)
    #: (MediaItem, MediaDetails) — forwarded from a browse page's Play button.
    playback_requested = Signal(object, object)

    def __init__(
        self,
        user: dict | None = None,
        auth_manager: AuthManager | None = None,
        on_theme: Callable | None = None,
        on_logout: Callable | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._user = user or {}
        self._auth = auth_manager
        self._on_theme = on_theme
        self._on_logout = on_logout
        self._last_tab: dict[str, int] = {}
        self._current_cat = ""
        self._tab_buttons: list[QPushButton] = []
        self._tab_group: QButtonGroup | None = None
        self._segmented_toggle: SegmentedToggle | None = None

        self._categories: dict[str, list[tuple[str, QWidget]]] = {
            "Video": [
                ("Movies", MoviesPage()),
                ("TV Shows", TVShowsPage()),
            ],
            "Music": [
                ("Music", MusicPage()),
            ],
            "Games": [
                ("Games", GamesPage()),
            ],
            "My Lists": [
                ("My Lists", MyListsPage()),
            ],
            "Settings": [
                ("Settings", SettingsPage(user=self._user)),
            ],
        }

        # Admin page: visible only when the session has the admin role
        if self._user.get("role") == "admin" and self._auth is not None:
            from ui.pages.admin import AdminPage

            self._categories["Admin"] = [
                ("Admin", AdminPage(auth_manager=self._auth)),
            ]

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self._tab_bar = TopNavBar(
            self,
            user=self._user,
            on_theme=self._on_theme,
            on_settings=lambda: self.show_category("Settings"),
            on_logout=self._on_logout,
        )
        self._tab_bar.saved_clicked.connect(lambda: self.show_category("My Lists"))
        self._tab_layout = self._tab_bar.center_layout
        outer.addWidget(self._tab_bar)

        self._stack = QStackedWidget()
        outer.addWidget(self._stack)

        self._page_index: dict[str, dict[str, int]] = {}
        for cat, tabs in self._categories.items():
            self._page_index[cat] = {}
            for tab_label, widget in tabs:
                idx = self._stack.addWidget(widget)
                self._page_index[cat][tab_label] = idx
                signal = getattr(widget, "playback_requested", None)
                if signal is not None:
                    signal.connect(self.playback_requested)

        movies_page = self._categories["Video"][0][1]
        tvshows_page = self._categories["Video"][1][1]
        if hasattr(movies_page, "toolbar_box") and hasattr(tvshows_page, "toolbar_box"):
            self._tab_bar.setup_search_stack(
                getattr(movies_page, "toolbar_box"),
                getattr(tvshows_page, "toolbar_box"),
            )

        self.show_category("Video")

    @property
    def top_bar(self) -> TopNavBar:
        return self._tab_bar

    # -- Category navigation --------------------------------------------------
    def show_category(self, name: str) -> None:
        if name not in self._categories:
            return

        if name == "My Lists":
            self._current_cat = name
            page = self._categories["My Lists"][0][1]
            self._stack.setCurrentWidget(page)
            self._tab_bar.show_video_search(False)
            self._tab_bar.saved_button.set_active(True)
            self._build_center_tabs("Video", force_inactive=True)
            self.category_changed.emit(name)
            self._tab_bar._layout_sections()
            return

        tabs = self._categories[name]
        last = self._last_tab.get(name, 0)
        self._current_cat = name

        self._tab_bar.saved_button.set_active(False)

        if name == "Video":
            self._tab_bar.show_video_search(True)
        else:
            self._tab_bar.show_video_search(False)

        self._build_center_tabs(name, force_inactive=False)
        self._switch_subtab(last, save=False)
        self.category_changed.emit(name)

        self._tab_bar._layout_sections()

    def _build_center_tabs(self, cat_name: str, force_inactive: bool = False) -> None:
        # Clear existing widgets from center layout
        while self._tab_layout.count() > 0:
            item = self._tab_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.hide()
                widget.setParent(None)
                widget.deleteLater()

        if self._tab_group is not None:
            self._tab_group.deleteLater()
            self._tab_group = None

        tabs = self._categories.get(cat_name, [])
        self._tab_buttons = []
        self._segmented_toggle = None

        if not tabs:
            return

        # Two or more sub-pages share the same centered pill (Movies/TV, games).
        if len(tabs) >= 2:
            labels = [t[0] for t in tabs]
            toggle = SegmentedToggle(labels)
            toggle.tab_clicked.connect(
                lambda idx, c=cat_name: self._handle_center_tab_click(c, idx)
            )
            self._tab_layout.addWidget(toggle, 0, Qt.AlignmentFlag.AlignVCenter)
            self._segmented_toggle = toggle
            self._tab_buttons = toggle.buttons

            if force_inactive:
                toggle.set_all_inactive()
            return

    def _handle_center_tab_click(self, cat_name: str, index: int) -> None:
        if self._current_cat != cat_name:
            self.show_category(cat_name)
        self._switch_subtab(index)

    def _switch_subtab(self, index: int, save: bool = True) -> None:
        category = self._current_cat
        if category not in self._categories:
            return
        tabs = self._categories[category]
        if index >= len(tabs):
            index = 0

        tab_label = tabs[index][0]
        page_index = self._page_index[category][tab_label]
        self._stack.setCurrentIndex(page_index)

        if save:
            self._last_tab[category] = index

        if category == "Video":
            self._tab_bar.set_search_index(index)
            self._tab_bar.saved_button.set_active(False)

        # Update toggle or buttons
        if self._segmented_toggle is not None:
            self._segmented_toggle.set_active_index(index, animate=True)
        elif index < len(self._tab_buttons):
            for tab_index, button in enumerate(self._tab_buttons):
                active = tab_index == index
                button.setChecked(active)
                button.setProperty("active", "true" if active else "false")
                theme.restyle(button)

    # -- Introspection (used by tests) ----------------------------------------
    def current_tab_index(self) -> int:
        if self._segmented_toggle is not None:
            return self._segmented_toggle._current_index
        for index, button in enumerate(self._tab_buttons):
            if button.isChecked():
                return index
        return 0

    def current_page(self) -> QWidget:
        return self._stack.currentWidget()
