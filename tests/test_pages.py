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
        SettingsPage(),
    ]
    for page in pages:
        assert page.title
        assert page.title == page.header.title


def test_movies_page_builds_and_has_no_key_state(app):
    """MoviesPage shows setup_state when no TMDB key is configured."""
    import os

    os.environ.pop("TMDB_API_KEY", None)
    from api.movies import TmdbClient
    from ui.pages.video_movies import MoviesPage

    provider = TmdbClient(api_key="")  # no key
    page = MoviesPage(provider=provider)
    assert page.title == "Movies"
    assert hasattr(page, "browse_box")
    assert hasattr(page, "setup_state")
    assert hasattr(page, "search")
    assert hasattr(page, "genre_filter")


def test_movies_genre_combo_has_entries(app):
    """The genre filter should contain at least Drama and Action."""
    from api.movies import TmdbClient
    from ui.pages.video_movies import MoviesPage

    page = MoviesPage(provider=TmdbClient(api_key=""))
    genres = [page.genre_filter.itemText(i) for i in range(page.genre_filter.count())]
    assert "All genres" in genres
    assert "Drama" in genres
    assert "Action" in genres


def test_my_lists_shows_empty_state(app):
    from ui.pages.my_lists import MyListsPage

    page = MyListsPage()
    assert isinstance(page.empty_state, EmptyState)
    assert not page.empty_state.isHidden()
    assert "No saved titles" in page.empty_state.title_label.text()


def test_settings_page_shows_signed_in_user(app):
    from PySide6.QtWidgets import QLabel

    from ui.pages.settings import SettingsPage

    page = SettingsPage(user={"username": "chris", "email": "chris@example.com"})
    texts = [child.text() for child in page.findChildren(QLabel)]
    assert "chris" in texts
    assert "chris@example.com" in texts


def test_settings_page_has_no_logout_button(app):
    """Logging out belongs to the sidebar so there is only one such action."""
    from PySide6.QtWidgets import QPushButton

    from ui.pages.settings import SettingsPage

    page = SettingsPage(user={"username": "chris", "email": "chris@example.com"})
    buttons = page.findChildren(QPushButton)
    assert buttons == []
    assert not hasattr(page, "logout_button")

    from PySide6.QtWidgets import QLabel

    texts = [child.text() for child in page.findChildren(QLabel)]
    assert any("sidebar" in text.lower() for text in texts)


def test_settings_cards_are_exposed(app):
    from ui.pages.settings import SettingsPage

    page = SettingsPage(user={})
    assert page.profile_card is not None
    assert page.appearance_card is not None
    assert page.session_card is not None


def test_card_grid_reflows_to_available_width(app):
    """Resizing the viewport must drop columns, not clip the last one."""
    from PySide6.QtWidgets import QFrame, QScrollArea

    from theme import theme_manager as theme
    from ui.components.media_card import CardGrid, MediaCard

    cards = [MediaCard("film", f"Title {i}", "Subtitle") for i in range(8)]
    grid = CardGrid(cards)
    grid.setMinimumSize(0, 0)

    area = QScrollArea()
    area.setFrameShape(QFrame.Shape.NoFrame)
    area.setWidgetResizable(True)
    area.setWidget(grid)
    area.resize(600, 400)
    area.show()
    app.processEvents()
    assert grid._columns == 2

    area.resize(980, 400)
    app.processEvents()
    assert grid._columns == 4
    assert all(card.width() >= theme.CARD_MIN_WIDTH for card in cards)

    area.resize(600, 400)
    app.processEvents()
    assert grid._columns == 2, "grid did not reflow back down"

    # The grid must stay shrinkable or the page canvas locks wider than the
    # viewport after a resize.
    assert grid.minimumSizeHint().width() == theme.CARD_MIN_WIDTH
    area.close()


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
