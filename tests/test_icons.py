import pytest

from ui.components.icons import _GLYPHS, app_icon, brand_pixmap, make_icon


@pytest.mark.parametrize("name", sorted(_GLYPHS))
def test_every_glyph_renders(app, name):
    icon = make_icon(name, "#E8AAB9", 18)
    assert not icon.isNull()
    assert not icon.pixmap(18, 18).isNull()


def test_unknown_glyph_raises(app):
    with pytest.raises(KeyError):
        make_icon("does-not-exist", "#E8AAB9")


def test_icon_carries_active_tint(app):
    from PySide6.QtGui import QIcon

    icon = make_icon("film", "#B8B2B5", 18, active_color="#E8AAB9")
    active = icon.pixmap(18, 18, QIcon.Mode.Normal, QIcon.State.On)
    assert not active.isNull()


def test_brand_pixmap_is_high_dpi(app):
    pixmap = brand_pixmap(32)
    assert pixmap.devicePixelRatio() == 2.0
    assert pixmap.width() == 64


def test_app_icon_has_common_sizes(app):
    icon = app_icon()
    for size in (16, 32, 64):
        assert not icon.pixmap(size, size).isNull()
