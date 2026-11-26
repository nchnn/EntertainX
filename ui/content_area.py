from __future__ import annotations

from typing import Callable

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QHBoxLayout,
    QMenu,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from theme import theme_manager as theme
from ui.components.icons import make_icon

from auth.auth_manager import AuthManager

from ui.pages.movies import MoviesPage
from ui.pages.tv_shows import TVShowsPage
from ui.pages.music import MusicPage
from ui.pages.chess import ChessPage
from ui.pages.fireboy import FireboyPage
from ui.pages.games import BrowseGamesPage
from ui.pages.my_lists import MyListsPage
from ui.pages.settings import SettingsPage


class TopNavBar(QWidget):
    """Fixed top navigation bar with Left (Search & Filter), Center (Tabs), Right (Saved & Profile)."""

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
        self.setFixedHeight(56)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._content_area = content_area
        self._user = user or {}
        self._on_theme = on_theme
        self._on_settings = on_settings
        self._on_logout = on_logout
        self._menu_open = False

        # ── Left Section: Search and Filter ─────────────────────────────────
        self._left_container = QWidget(self)
        self._left_layout = QHBoxLayout(self._left_container)
        self._left_layout.setContentsMargins(0, 0, 0, 0)
        self._left_layout.setSpacing(theme.SPACE_MD)
        self._left_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        self.search_stack = QStackedWidget(self._left_container)
        self._left_layout.addWidget(self.search_stack)

        # ── Center Section: Main Navigation Tabs ────────────────────────────
        self._center_container = QWidget(self)
        self.center_layout = QHBoxLayout(self._center_container)
        self.center_layout.setContentsMargins(0, 0, 0, 0)
        self.center_layout.setSpacing(0)
        self.center_layout.setAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)

        # ── Right Section: Saved and Profile ────────────────────────────────
        self._right_container = QWidget(self)
        self._right_layout = QHBoxLayout(self._right_container)
        self._right_layout.setContentsMargins(0, 0, 0, 0)
        self._right_layout.setSpacing(theme.SPACE_MD)
        self._right_layout.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.saved_button = QPushButton("Saved")
        self.saved_button.setObjectName("SavedButton")
        self.saved_button.setAccessibleName("Saved")
        self.saved_button.setProperty("variant", "tab")
        self.saved_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.saved_button.setIcon(make_icon("list", theme.TEXT_MUTED, 15))
        self.saved_button.setToolTip("Saved Titles (My Lists)")
        self.saved_button.clicked.connect(self._on_saved_clicked)
        self._right_layout.addWidget(self.saved_button, 0, Qt.AlignmentFlag.AlignVCenter)

        self.profile_button = QPushButton("U")
        self.profile_button.setObjectName("ProfileButton")
        self.profile_button.setAccessibleName("Profile")
        self.profile_button.setProperty("variant", "user-avatar")
        self.profile_button.setFixedSize(32, 32)
        self.profile_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._update_profile_avatar(self._user)
        self.profile_button.clicked.connect(self._show_profile_menu)
        self._right_layout.addWidget(self.profile_button, 0, Qt.AlignmentFlag.AlignVCenter)

    def setup_search_stack(self, movies_toolbar: QWidget, tv_toolbar: QWidget) -> None:
        self.search_stack.addWidget(movies_toolbar)
        self.search_stack.addWidget(tv_toolbar)
        blank = QWidget()
        self.search_stack.addWidget(blank)

    def set_search_index(self, index: int) -> None:
        if index < self.search_stack.count():
            self.search_stack.setCurrentIndex(index)

    def show_video_search(self, visible: bool) -> None:
        self._left_container.setVisible(visible)
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

        self._categories: dict[str, list[tuple[str, QWidget]]] = {
            "Video": [
                ("Movies", MoviesPage()),
                ("TV Shows", TVShowsPage()),
            ],
            "Music": [
                ("Music", MusicPage()),
            ],
            "Games": [
                ("Chess", ChessPage()),
                ("Fireboy & Watergirl", FireboyPage()),
                ("Browse Games", BrowseGamesPage()),
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

    # ── Category navigation ─────────────────────────────────────────────────
    def show_category(self, name: str) -> None:
        if name not in self._categories:
            return

        if name == "My Lists":
            self._current_cat = name
            page = self._categories["My Lists"][0][1]
            self._stack.setCurrentWidget(page)
            self._tab_bar.show_video_search(False)
            self._tab_bar.saved_button.setProperty("active", "true")
            self._tab_bar.saved_button.setIcon(make_icon("list", theme.PRIMARY, 15))
            theme.restyle(self._tab_bar.saved_button)
            self._build_center_tabs("Video", force_inactive=True)
            self._tab_bar._layout_sections()
            return

        tabs = self._categories[name]
        last = self._last_tab.get(name, 0)
        self._current_cat = name

        if name == "Video":
            self._tab_bar.show_video_search(True)
            self._tab_bar.saved_button.setProperty("active", "false")
            self._tab_bar.saved_button.setIcon(make_icon("list", theme.TEXT_MUTED, 15))
            theme.restyle(self._tab_bar.saved_button)
            self._build_center_tabs("Video", force_inactive=False)
            self._switch_subtab(last, save=False)
        else:
            self._tab_bar.show_video_search(False)
            self._tab_bar.saved_button.setProperty("active", "false")
            self._tab_bar.saved_button.setIcon(make_icon("list", theme.TEXT_MUTED, 15))
            theme.restyle(self._tab_bar.saved_button)
            self._build_center_tabs(name, force_inactive=False)
            self._switch_subtab(last, save=False)

        self._tab_bar._layout_sections()

    def _build_center_tabs(self, cat_name: str, force_inactive: bool = False) -> None:
        while self._tab_layout.count() > 0:
            item = self._tab_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.hide()
                widget.setParent(None)
                widget.deleteLater()

        if self._tab_group is not None:
            self._tab_group.deleteLater()
        self._tab_group = QButtonGroup(self)
        self._tab_group.setExclusive(True)

        tabs = self._categories.get(cat_name, [])
        self._tab_buttons = []

        for index, (tab_label, _) in enumerate(tabs):
            button = QPushButton(tab_label)
            button.setProperty("variant", "tab")
            button.setCheckable(True)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            if force_inactive:
                button.setChecked(False)
                button.setProperty("active", "false")
            button.clicked.connect(
                lambda checked=False, i=index, c=cat_name: self._handle_center_tab_click(c, i)
            )
            self._tab_group.addButton(button)
            self._tab_layout.addWidget(button)
            self._tab_buttons.append(button)

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
            self._tab_bar.saved_button.setProperty("active", "false")
            self._tab_bar.saved_button.setIcon(make_icon("list", theme.TEXT_MUTED, 15))
            theme.restyle(self._tab_bar.saved_button)

        if index < len(self._tab_buttons):
            for tab_index, button in enumerate(self._tab_buttons):
                active = tab_index == index
                button.setChecked(active)
                button.setProperty("active", "true" if active else "false")
                theme.restyle(button)

    # ── Introspection (used by tests) ───────────────────────────────────────
    def current_tab_index(self) -> int:
        for index, button in enumerate(self._tab_buttons):
            if button.isChecked():
                return index
        return 0

    def current_page(self) -> QWidget:
        return self._stack.currentWidget()
