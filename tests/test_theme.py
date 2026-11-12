from theme import theme_manager as theme


def test_palette_is_grey_dominant_with_pink_accent():
    assert theme.BG == "#242326"
    assert theme.BG_SIDEBAR == "#303034"
    assert theme.BG_CARD == "#3B393F"
    assert theme.BG_ELEVATED == "#454249"
    assert theme.BORDER == "#504C53"
    assert theme.PRIMARY == "#E8AAB9"
    assert theme.TEXT_PRIMARY == "#F4F1F2"


def test_legacy_names_still_resolve():
    assert theme.BG_DARK == theme.BG
    assert theme.SECONDARY == theme.ACCENT_HOVER


def test_stylesheet_contains_every_surface_and_variant():
    qss = theme.build_stylesheet()
    for color in (
        theme.BG,
        theme.BG_SIDEBAR,
        theme.BG_CARD,
        theme.BG_ELEVATED,
        theme.BORDER,
        theme.PRIMARY,
        theme.TEXT_PRIMARY,
        theme.TEXT_MUTED,
        theme.DANGER,
        theme.SUCCESS,
    ):
        assert color in qss
    for selector in (
        'QPushButton[variant="primary"]',
        'QPushButton[variant="nav"][active="true"]',
        'QPushButton[variant="tab"][active="true"]',
        'QPushButton[variant="playDisc"]',
        'QFrame[role="card"]',
        'QFrame[role="mediaCard"]:hover',
        'QLineEdit:focus',
        'QCheckBox::indicator:checked',
    ):
        assert selector in qss


def test_accent_override_regenerates_tint(app):
    qss = theme.build_stylesheet(primary="#123456")
    assert "#123456" in qss
    assert "rgba(18, 52, 86, 0.16)" in qss


def test_apply_theme_sets_application_stylesheet(app):
    theme.apply_theme(app, primary="#123456", secondary="#abcdef")
    assert "#123456" in app.styleSheet()
    theme.apply_theme(app)
    assert theme.PRIMARY in app.styleSheet()


def test_restyle_repolishes_widget(app):
    from PySide6.QtWidgets import QPushButton

    button = QPushButton("x")
    button.setProperty("variant", "nav")
    button.setProperty("active", "true")
    theme.restyle(button)
    assert button.property("active") == "true"
