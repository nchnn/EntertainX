import sys
import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QComboBox, QLabel, QPushButton, QScrollArea

from ui.components.form_fields import IconLineEdit
from ui.content_area import ContentArea, TopNavBar
from ui.frameless import TitleBar

app = QApplication.instance() or QApplication(sys.argv)


def test_titlebar_has_no_profile_icon_beside_logo():
    bar = TitleBar()
    assert not hasattr(bar, "avatar_btn")
    assert bar.title_label.text() == "EntertainX"


def test_top_nav_three_sections_exist():
    ca = ContentArea(user={"username": "alice", "email": "alice@example.com"})
    top_bar = ca.top_bar
    assert isinstance(top_bar, TopNavBar)

    # Category switch lives on the sidebar, not a Film / Music / Games pill
    assert not hasattr(ca, "_category_toggle")
    assert all(button.text() not in {"Film", "Music", "Games"} for button in top_bar.findChildren(QPushButton))
    assert all("Reel" not in label.text() for label in top_bar.findChildren(QLabel))
    assert top_bar.search_stack.count() >= 2
    assert top_bar.search_stack.parent() is top_bar._right_container

    # Center section: Movies and TV Shows
    assert len(ca._tab_buttons) == 2
    assert ca._tab_buttons[0].text() == "Movies"
    assert ca._tab_buttons[1].text() == "TV Shows"

    # Right section: Saved and Profile buttons exist
    assert hasattr(top_bar, "saved_button")
    assert hasattr(top_bar, "profile_button")
    assert top_bar.saved_button.text() == "Saved"
    assert top_bar.profile_button.text() == "A"


def test_top_nav_left_section_controls():
    ca = ContentArea(user={"username": "alice"})
    top_bar = ca.top_bar

    # Movies is active initially
    movies_toolbar = top_bar.search_stack.widget(0)
    assert movies_toolbar is not None
    search_widgets = movies_toolbar.findChildren(IconLineEdit)
    genre_combos = movies_toolbar.findChildren(QComboBox)

    assert len(search_widgets) == 1
    assert len(genre_combos) == 1
    assert "movies" in search_widgets[0].placeholderText().lower()
    assert genre_combos[0].count() > 1
    assert genre_combos[0].itemText(0) == "All genres"


def test_top_nav_mathematical_centering():
    ca = ContentArea(user={"username": "alice"})
    top_bar = ca.top_bar

    for width in (1240, 1000, 900):
        top_bar.resize(width, 56)
        top_bar._layout_sections()

        center_geom = top_bar._center_container.geometry()
        expected_center_x = (width - center_geom.width()) // 2
        assert center_geom.x() == expected_center_x

        # Verify left section does not overlap center
        left_geom = top_bar._left_container.geometry()
        assert left_geom.x() + left_geom.width() <= center_geom.x()

        # Verify right section does not overlap center
        right_geom = top_bar._right_container.geometry()
        assert center_geom.x() + center_geom.width() <= right_geom.x()


def test_top_nav_navigation_movies_tv_saved():
    ca = ContentArea(user={"username": "alice"})
    top_bar = ca.top_bar

    # Initial: Movies active
    assert ca._tab_buttons[0].property("active") == "true"
    assert ca._tab_buttons[1].property("active") == "false"
    assert top_bar.saved_button.property("active") == "false"
    assert top_bar.search_stack.currentIndex() == 0

    # Switch to TV Shows
    ca._switch_subtab(1)
    assert ca._tab_buttons[0].property("active") == "false"
    assert ca._tab_buttons[1].property("active") == "true"
    assert top_bar.saved_button.property("active") == "false"
    assert top_bar.search_stack.currentIndex() == 1

    # Click Saved
    top_bar.saved_button.click()
    assert ca.current_page().__class__.__name__ == "MyListsPage"
    assert top_bar.saved_button.property("active") == "true"
    assert ca._tab_buttons[0].property("active") == "false"
    assert ca._tab_buttons[1].property("active") == "false"

    # Click Movies to return
    ca._tab_buttons[0].click()
    assert ca.current_page().__class__.__name__ == "MoviesPage"
    assert ca._tab_buttons[0].property("active") == "true"
    assert ca._tab_buttons[1].property("active") == "false"
    assert top_bar.saved_button.property("active") == "false"


def test_top_nav_film_music_games_switch_pages():
    ca = ContentArea(user={"username": "alice"})
    top_bar = ca.top_bar

    ca.show_category("Music")
    assert ca.current_page().__class__.__name__ == "MusicPage"
    assert not top_bar.search_stack.isVisible()

    ca.show_category("Games")
    assert ca.current_page().__class__.__name__ == "GamesPage"
    assert ca._segmented_toggle is None  # single-tab category: no toggle

    ca.show_category("Video")
    assert ca.current_page().__class__.__name__ == "MoviesPage"
    assert not top_bar.search_stack.isHidden()
    assert top_bar.search_stack.currentIndex() == 0
    assert ca._tab_buttons[0].text() == "Movies"


def test_top_nav_fixed_outside_scroll_area():
    ca = ContentArea(user={"username": "alice"})
    top_bar = ca.top_bar

    # TopNavBar should NOT be inside any QScrollArea
    parent = top_bar.parent()
    while parent is not None:
        assert not isinstance(parent, QScrollArea)
        parent = parent.parent()

    # The current page itself has a scroll area for content
    page = ca.current_page()
    assert hasattr(page, "scroll_area")
    assert isinstance(page.scroll_area, QScrollArea)
