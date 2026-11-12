from ui.components.media_card import CardGrid, MediaCard


def test_media_card_exposes_text(app):
    card = MediaCard("film", "Neon Divide", "Sci-Fi", "2024  ·  1h 58m")
    assert card.title == "Neon Divide"
    assert card.subtitle_label.full_text() == "Sci-Fi"
    assert card.meta_label.full_text() == "2024  ·  1h 58m"


def test_media_card_matches_title_subtitle_and_meta(app):
    card = MediaCard("music", "Soft Static", "Mira Vale", "10 tracks")
    assert card.matches("")
    assert card.matches("soft")
    assert card.matches("mira")
    assert card.matches("tracks")
    assert not card.matches("nothing-here")


def test_card_grid_add_and_clear(app):
    grid = CardGrid([MediaCard("play", "One", "Channel")])
    assert len(grid.cards) == 1

    grid.add_card(MediaCard("play", "Two", "Channel"))
    assert [card.title for card in grid.cards] == ["One", "Two"]

    grid.clear()
    assert grid.cards == []


def test_card_grid_reflows_without_error(app):
    cards = [MediaCard("film", f"Title {i}", "Genre") for i in range(7)]
    grid = CardGrid(cards)

    for width in (300, 640, 1200):
        grid.resize(width, 600)
        app.processEvents()
        assert grid._columns >= 1
        assert len(grid.cards) == 7
