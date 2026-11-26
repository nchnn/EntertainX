import pytest

from ui.components.layout import EmptyState


def test_every_page_builds_with_a_header(app):
    from ui.pages.chess import ChessPage
    from ui.pages.fireboy import FireboyPage
    from ui.pages.music import MusicPage
    from ui.pages.my_lists import MyListsPage
    from ui.pages.settings import SettingsPage
    from ui.pages.movies import MoviesPage
    from ui.pages.tv_shows import TVShowsPage

    pages = [
        MoviesPage(),
        TVShowsPage(),
        MusicPage(),
        ChessPage(),
        FireboyPage(),
        MyListsPage(),
        SettingsPage(),
    ]
    for page in pages:
        assert page.title
        assert page.title == page.header.title


def test_games_page_hosts_catalog_and_player(app):
    from ui.pages.games import GamesPage
    from ui.pages.games.catalog import CatalogPage
    from ui.pages.games.player import GamePlayerWidget

    page = GamesPage()
    assert page.count() == 2
    assert isinstance(page.widget(0), CatalogPage)
    assert isinstance(page.widget(1), GamePlayerWidget)
    assert page.currentIndex() == 0


def test_games_catalog_renders_a_card_per_entry(app, monkeypatch):
    import ui.pages.games.catalog as catalog_mod
    from api.games import GameEntry

    # Keep the test offline: the real fetch runs on a worker thread.
    monkeypatch.setattr(catalog_mod, "run_async", lambda *args, **kwargs: None)

    entries = [
        GameEntry(
            name=f"Game {i}",
            directory=f"game-{i}",
            image="cover.png",
            tags=["action"],
            thumbnail_url=f"https://example.test/game-{i}/cover.png",
            backup_thumbnail_url="",
            embed_url=f"https://example.test/game-{i}/index.html",
        )
        for i in range(3)
    ]

    page = catalog_mod.CatalogPage()
    page._on_catalog_loaded(entries)

    assert len(page._grid.cards) == 3
    assert [card.entry.name for card in page._grid.visible_cards()] == [
        "Game 0",
        "Game 1",
        "Game 2",
    ]
    assert page._count_lbl.text() == "3 games available"
    assert page._genre_combo.itemText(1) == "Action"


def test_games_catalog_only_loads_visible_thumbnails(app, monkeypatch, wait_for):
    import ui.pages.games.catalog as catalog_mod
    import ui.pages.games.game_card as card_mod
    from api.games import GameEntry

    monkeypatch.setattr(catalog_mod, "run_async", lambda *args, **kwargs: None)

    class RecordingStore:
        def __init__(self) -> None:
            self.urls: list[str] = []

        def request(self, url, width, callback, owner=None) -> None:
            self.urls.append(url)

    store = RecordingStore()
    monkeypatch.setattr(card_mod, "get_store", lambda: store)

    entries = [
        GameEntry(
            name=f"Game {i}",
            directory=f"game-{i}",
            image="cover.png",
            tags=["action"],
            thumbnail_url=f"https://example.test/game-{i}/cover.png",
            backup_thumbnail_url="",
            embed_url=f"https://example.test/game-{i}/index.html",
        )
        for i in range(120)
    ]

    page = catalog_mod.CatalogPage()
    page.resize(1200, 800)
    page.show()
    app.processEvents()
    page._on_catalog_loaded(entries)

    assert wait_for(lambda: not page._pending_entries, timeout=5)
    assert wait_for(lambda: bool(store.urls), timeout=2)

    # The limiter must never request every cover at once.
    assert 0 < len(store.urls) < len(entries)


def test_games_page_opens_the_player_for_a_selected_game(app, monkeypatch):
    import ui.pages.games.catalog as catalog_mod
    from api.games import GameEntry
    from ui.pages.games import GamesPage

    monkeypatch.setattr(catalog_mod, "run_async", lambda *args, **kwargs: None)

    entry = GameEntry(
        name="2048",
        directory="2048",
        image="cover.png",
        tags=["puzzle"],
        thumbnail_url="https://example.test/2048/cover.png",
        backup_thumbnail_url="",
        embed_url="https://example.test/2048/index.html",
    )

    page = GamesPage()
    page._open_game(entry)

    assert page.currentIndex() == 1
    assert page._player._title_label.text() == "2048"
    assert page._player._web_view.url().toString() == entry.embed_url

    page._close_game()
    assert page.currentIndex() == 0


def test_movies_page_builds_and_has_no_key_state(app):
    """MoviesPage shows setup_state when no TMDB key is configured."""
    import os

    os.environ.pop("TMDB_API_KEY", None)
    from api.movies import TmdbClient
    from ui.pages.movies import MoviesPage

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
    from ui.pages.movies import MoviesPage

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
    """Logging out belongs to the top navigation profile menu."""
    from PySide6.QtWidgets import QPushButton

    from ui.pages.settings import SettingsPage

    page = SettingsPage(user={"username": "chris", "email": "chris@example.com"})
    buttons = page.findChildren(QPushButton)
    assert buttons == []
    assert not hasattr(page, "logout_button")

    from PySide6.QtWidgets import QLabel

    texts = [child.text() for child in page.findChildren(QLabel)]
    assert any("navigation" in text.lower() for text in texts)


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
    from ui.components.video.media_card import CardGrid, MediaCard

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

    from ui.pages import chess, fireboy

    page = getattr(chess, page_name, None) or getattr(fireboy, page_name)
    instance = page()
    play_buttons = [
        button
        for button in instance.findChildren(QPushButton)
        if button.text() == "Play"
    ]
    assert play_buttons
    assert all(not button.isEnabled() for button in play_buttons)
