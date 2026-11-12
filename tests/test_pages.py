import pytest

from ui.components.surfaces import EmptyState


def test_every_page_builds_with_a_header(app):
    from ui.pages.games_chess import ChessPage
    from ui.pages.games_fireboy import FireboyPage
    from ui.pages.games_browse import BrowseGamesPage
    from ui.pages.music import MusicPage
    from ui.pages.my_lists import MyListsPage
    from ui.pages.settings import SettingsPage
    from ui.pages.video_movies import MoviesPage
    from ui.pages.video_tvshows import TVShowsPage
    from ui.pages.video_youtube import YouTubePage

    pages = [
        YouTubePage(),
        MoviesPage(),
        TVShowsPage(),
        MusicPage(),
        ChessPage(),
        FireboyPage(),
        BrowseGamesPage(),
        MyListsPage(),
        SettingsPage(on_logout=lambda: None),
    ]
    for page in pages:
        assert page.title
        assert page.title == page.header.title


def test_movies_search_filters_cards(app):
    from ui.pages.video_movies import MoviesPage

    page = MoviesPage()
    assert len(page.visible_titles()) == 8

    page.search.setText("neon")
    assert page.visible_titles() == ["Neon Divide"]
    assert page.empty_state.isHidden()

    page.search.setText("zzzz")
    assert page.visible_titles() == []
    assert not page.empty_state.isHidden()


def test_movies_genre_combo_filters_cards(app):
    from ui.pages.video_movies import MoviesPage

    page = MoviesPage()
    page.genre_filter.setCurrentText("Drama")
    assert set(page.visible_titles()) == {"The Quiet Orbit", "Paper Lanterns"}

    page.genre_filter.setCurrentText("All genres")
    assert len(page.visible_titles()) == 8


def test_my_lists_shows_empty_state(app):
    from ui.pages.my_lists import MyListsPage

    page = MyListsPage()
    assert isinstance(page.empty_state, EmptyState)
    assert not page.empty_state.isHidden()
    assert "No saved titles" in page.empty_state.title_label.text()


def test_settings_page_shows_signed_in_user(app):
    from PySide6.QtWidgets import QLabel

    from ui.pages.settings import SettingsPage

    page = SettingsPage(
        on_logout=lambda: None,
        user={"username": "chris", "email": "chris@example.com"},
    )
    texts = [child.text() for child in page.findChildren(QLabel)]
    assert "chris" in texts
    assert "chris@example.com" in texts
    assert page.logout_button.isEnabled()


def test_settings_logout_button_calls_back(app):
    from ui.pages.settings import SettingsPage

    calls = []
    page = SettingsPage(on_logout=lambda: calls.append(True), user={})
    page.logout_button.click()
    assert calls == [True]


@pytest.mark.parametrize("page_name", ["ChessPage", "FireboyPage"])
def test_game_pages_disable_play_until_implemented(app, page_name):
    from PySide6.QtWidgets import QPushButton

    from ui.pages import games_chess, games_fireboy

    page = getattr(games_chess, page_name, None) or getattr(games_fireboy, page_name)
    instance = page()
    play_buttons = [
        button
        for button in instance.findChildren(QPushButton)
        if button.text() == "Play"
    ]
    assert play_buttons
    assert all(not button.isEnabled() for button in play_buttons)
