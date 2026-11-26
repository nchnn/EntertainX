import pytest
from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QFont, QPixmap
from PySide6.QtWidgets import QWidget

from api.images import ImageStore
from api.movies import MediaDetails, MediaItem, pick_english_image, pick_logo, pick_textless_image
from ui.components.video.hover_preview import (
    CARD_W,
    IMG_H,
    HoverPreview,
    embed_hover_html,
)
from ui.components.video.title_detail import TitleDetailOverlay, embed_modal_html
from ui.components.video.top10_panel import (
    NUMERAL_OVERLAP,
    NUMERAL_OVERLAP_10,
    TILE_W,
    TILE_H,
    Top10Panel,
    Top10Tile,
    _rank_font,
)


def _make_item(ident: int = 1, title: str = "Test Movie") -> MediaItem:
    return MediaItem(
        id=ident,
        media_type="movie",
        title=title,
        overview="Overview text",
        poster_path="",
        backdrop_path="",
        release_date="2026-05-01",
        rating=8.2,
        votes=1240,
        genre_ids=(28, 12),
    )


def test_pick_logo_prefers_english():
    images = {
        "logos": [
            {"file_path": "/es_logo.png", "iso_639_1": "es", "vote_average": 9.0, "vote_count": 10},
            {"file_path": "/en_logo.png", "iso_639_1": "en", "vote_average": 8.0, "vote_count": 5},
            {"file_path": "/neutral_logo.png", "iso_639_1": None, "vote_average": 7.0, "vote_count": 2},
        ]
    }
    assert pick_logo(images) == "/en_logo.png"


def test_pick_logo_falls_back_when_no_english():
    images = {
        "logos": [
            {"file_path": "/neutral.png", "iso_639_1": None, "vote_average": 6.5, "vote_count": 3},
        ]
    }
    assert pick_logo(images) == "/neutral.png"


def test_pick_logo_empty_when_no_logos():
    assert pick_logo({}) == ""
    assert pick_logo({"logos": []}) == ""


def test_media_details_logo_url():
    item = _make_item()
    details = MediaDetails(
        item=item,
        logo_path="/official_logo.png",
        trailer_key="test_key_123",
    )
    assert details.logo_url("w500") == "https://image.tmdb.org/t/p/w500/official_logo.png"
    assert details.trailer_key == "test_key_123"


def test_top10_tile_geometry_and_font(app):
    item = _make_item()
    tile1 = Top10Tile(1, item)
    assert tile1.overlap == NUMERAL_OVERLAP
    assert tile1.width() == TILE_W + NUMERAL_OVERLAP
    assert tile1.height() == TILE_H

    tile10 = Top10Tile(10, item)
    assert tile10.overlap == NUMERAL_OVERLAP_10
    assert tile10.width() == TILE_W + NUMERAL_OVERLAP_10

    font = _rank_font(180)
    assert font.weight() == QFont.Weight.Black


def test_top10_panel_set_items(app):
    panel = Top10Panel("Top 10 Today")
    items = [_make_item(i, f"Movie {i}") for i in range(1, 11)]
    panel.set_items(items)
    assert len(panel._tiles) == 10
    assert panel._tiles[0].rank == 1
    assert panel._tiles[9].rank == 10


def test_embed_hover_html():
    html = embed_hover_html(
        "dQw4w9WgXcQ",
        "https://image.tmdb.org/t/p/w500/logo.png",
        "Avengers: Doomsday",
        muted=True,
    )
    assert "dQw4w9WgXcQ" in html
    assert "https://image.tmdb.org/t/p/w500/logo.png" in html
    assert "toggleMute" in html
    assert "isMuted = true" in html


def test_hover_preview_initialization_and_fill(app):
    host = QWidget()
    host.resize(1000, 800)
    preview = HoverPreview(host)
    item = _make_item()

    preview._fill(item)
    assert preview.cert_label.text() in ("PG-13", "TV-14")
    assert preview.quality_badge.text() == "HD"
    assert "Action" in preview.genres_label.text()
    assert not preview.mute_button.isHidden()


def test_hover_preview_mute_toggle(app):
    host = QWidget()
    preview = HoverPreview(host)
    assert preview._muted is False

    preview._toggle_mute()
    assert preview._muted is True

    preview._toggle_mute()
    assert preview._muted is False


def test_hover_preview_watchlist_toggle(app):
    host = QWidget()
    preview = HoverPreview(host)
    assert preview._in_watchlist is False

    preview._toggle_watchlist()
    assert preview._in_watchlist is True
    assert preview.watchlist_button.toolTip() == "In My List"

    preview._toggle_watchlist()
    assert preview._in_watchlist is False
    assert preview.watchlist_button.toolTip() == "Add to My List"


def test_hover_preview_countdown_progress(app):
    host = QWidget()
    preview = HoverPreview(host)
    preview._start_countdown()
    assert preview._countdown_active is True
    assert preview._countdown_progress == 0.0

    preview._on_countdown_tick()
    assert preview._countdown_progress > 0.0

    preview._stop_countdown()
    assert preview._countdown_active is False
    assert preview._countdown_progress == 0.0


def test_hover_preview_set_details_and_logo(app):
    host = QWidget()
    store = ImageStore(fetch=lambda url: b"")
    preview = HoverPreview(host, store)
    item = _make_item()
    preview._item = item

    details = MediaDetails(
        item=item,
        certification="PG-13",
        runtime_text="2h 45m",
        trailer_key="abc12345",
        logo_path="/logo.png",
    )
    preview.set_details(details)
    assert preview.cert_label.text() == "PG-13"
    assert preview.runtime_label.text() == "2h 45m"
    assert preview._details == details


def test_title_detail_overlay_official_logo(app):
    host = QWidget()
    host.resize(1000, 800)
    store = ImageStore(fetch=lambda url: b"")
    detail = TitleDetailOverlay(host, store=store)
    item = _make_item()

    detail.open(item)
    assert not detail.title_label.isHidden()
    assert detail.logo_label.isHidden()

    pix = QPixmap(200, 60)
    pix.fill(Qt.GlobalColor.white)
    detail._on_logo(pix)
    assert not detail.logo_label.isHidden()
    assert detail.title_label.isHidden()


def test_pick_english_image_prefers_english_over_textless():
    candidates = [
        {"file_path": "/textless.jpg", "iso_639_1": None, "vote_count": 50},
        {"file_path": "/french.jpg", "iso_639_1": "fr", "vote_count": 40},
        {"file_path": "/english.jpg", "iso_639_1": "en", "vote_count": 10},
    ]
    assert pick_english_image(candidates, "/fallback.jpg") == "/english.jpg"


def test_pick_english_image_fallback_when_none():
    candidates = [
        {"file_path": "/textless.jpg", "iso_639_1": None, "vote_count": 50},
    ]
    assert pick_english_image(candidates, "/default.jpg") == "/default.jpg"
    assert pick_english_image([], "/default.jpg") == "/default.jpg"


def test_pick_textless_image_prefers_null_language():
    candidates = [
        {"file_path": "/english.jpg", "iso_639_1": "en", "vote_count": 50},
        {"file_path": "/textless.jpg", "iso_639_1": None, "vote_count": 40},
    ]
    assert pick_textless_image(candidates, "/fallback.jpg") == "/textless.jpg"


def test_embed_hover_html_disables_actions_and_hides_youtube_logo():
    html = embed_hover_html(
        "Dr060OLTodE",
        "https://example.com/logo.png",
        "Test Film",
        muted=True,
        show_close=True,
    )
    # Action disabling & anti-branding: scale(1.5) and pointer-events: none
    assert "transform: scale(1.5);" in html
    assert "pointer-events: none;" in html
    assert "controls=0" in html
    assert "disablekb=1" in html
    assert "close-btn" in html
    assert "sendAction('close')" in html


def test_title_detail_header_hover_and_countdown(app):
    host = QWidget()
    host.resize(1000, 800)
    store = ImageStore(fetch=lambda url: b"")
    detail = TitleDetailOverlay(host, store=store)
    item = _make_item()
    detail.open(item)

    details = MediaDetails(
        item=item,
        trailer_key="abc_key_123",
        english_backdrop_path="/en_art.jpg",
    )
    detail.set_details(details)
    assert detail.header.details == details

    # Hover enter triggers countdown
    detail.header.enterEvent(None)
    assert detail.header._countdown_active is True
    assert detail.header._countdown_progress == 0.0

    # Countdown tick advances progress
    detail.header._on_countdown_tick()
    assert detail.header._countdown_progress > 0.0

    # Hover leave stops countdown and stops trailer
    detail.header.leaveEvent(None)
    assert detail.header._countdown_active is False
    assert detail.header._is_playing is False


def test_embed_modal_html_cinematic_banner():
    html = embed_modal_html(
        "abc12345",
        "https://example.com/logo.png",
        "Way of the Warrior Kid",
        muted=False,
        in_watchlist=True,
    )
    assert "transform: translate(-50%, -50%) scale(1.35);" in html
    assert "modal-play-btn" in html
    assert "modal-list-btn" in html
    assert "modal-circle-btn" in html
    assert "sendAction('play')" in html
    assert "sendAction('close')" in html
    assert "sendAction('watchlist')" in html
    assert "vq=hd1080" in html


def test_title_detail_two_column_layout_and_metadata(app):
    host = QWidget()
    host.resize(1000, 800)
    store = ImageStore(fetch=lambda url: b"")
    detail = TitleDetailOverlay(host, store=store)
    item = _make_item()
    detail.open(item)

    details = MediaDetails(
        item=item,
        certification="PG-13",
        runtime_text="1h 47m",
        trailer_key="abc12345",
        logo_path="/logo.png",
        cast=("Chris Pratt", "Jude Hill", "Linda Cardellini"),
        genres=("Drama", "Family"),
        tagline="A mentor changes everything.",
    )
    detail.set_details(details)

    assert detail.year_label.text() == item.year
    assert detail.runtime_label.text() == "1h 47m"
    assert detail.cert_label.text() == "PG-13"
    assert detail.quality_badge.text() == "HD"
    assert "Chris Pratt" in detail.cast_label.text()
    assert "Drama" in detail.genres_label.text()
    assert "mentor changes everything" in detail.mood_label.text()


def test_title_detail_toggles_top_nav_visibility_and_size(app):
    from ui.content_area import TopNavBar

    win = QWidget()
    top_nav = TopNavBar(parent=win)
    host = QWidget(win)
    host.resize(1280, 800)
    win.show()
    detail = TitleDetailOverlay(host)
    item = _make_item()

    assert not top_nav.isHidden()
    detail.open(item)
    assert top_nav.isHidden()
    assert detail.panel.width() <= 1140

    # Ensure header and body both scroll inside the scroll area
    assert detail.scroll.widget() is not None
    assert detail.header.parent() is detail.scroll.widget()
    detail.scroll.verticalScrollBar().setValue(100)

    detail.close_overlay()
    assert not top_nav.isHidden()

    # Re-open cleanly with no deleted C++ object errors
    detail.open(item)
    assert detail.scroll.verticalScrollBar().value() == 0
    detail.close_overlay()


def test_trailer_delayed_reveal_and_audio_fade_html():
    from ui.components.trailer.player import AUDIO_FADE_MS, REVEAL_DELAY_MS, TARGET_VOLUME

    for html in (
        embed_hover_html("dQw4w9WgXcQ", "https://example.com/logo.png", "Test", muted=False),
        embed_modal_html("dQw4w9WgXcQ", "https://example.com/logo.png", "Test", muted=False),
    ):
        # Always starts muted + playsinline so browser autoplay works without jumpscare
        assert "autoplay=1&mute=1" in html
        assert "playsinline=1" in html
        assert "isMuted = true;" in html
        assert f"REVEAL_DELAY_MS = {REVEAL_DELAY_MS};" in html
        assert f"AUDIO_FADE_MS = {AUDIO_FADE_MS};" in html
        assert f"TARGET_VOLUME = {TARGET_VOLUME};" in html
        assert "requestAnimationFrame" in html
        assert "revealTrailer" in html
        assert "cleanupTrailer" in html
        assert "infoDelivery" in html

