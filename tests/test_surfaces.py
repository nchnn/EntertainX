from ui.components.layout import (
    Badge,
    Card,
    EmptyState,
    InlineBanner,
    PageHeader,
)


def test_inline_banner_shows_and_clears(app):
    banner = InlineBanner("error")
    assert banner.isHidden()

    banner.show_message("Invalid username or password")
    assert not banner.isHidden()
    assert banner.text == "Invalid username or password"

    banner.clear()
    assert banner.isHidden()
    assert banner.text == ""


def test_inline_banner_can_change_tone(app):
    banner = InlineBanner("error")
    banner.set_tone("success")
    assert banner.property("banner") == "success"


def test_page_header_exposes_title(app):
    header = PageHeader("Movies", "Find something to watch")
    assert header.title == "Movies"
    assert header.subtitle_label.text() == "Find something to watch"


def test_empty_state_exposes_title(app):
    state = EmptyState("list", "No saved titles yet", "Body copy", hint="Later")
    assert state.title_label.text() == "No saved titles yet"


def test_card_uses_role_property(app):
    card = Card()
    assert card.property("role") == "card"


def test_badge_uses_pill_role(app):
    badge = Badge("Preview")
    assert badge.property("role") == "pill"
    assert badge.text() == "Preview"
