"""Central visual identity for EntertainX.

Every colour, radius, spacing step, and font used by the UI lives here. Widgets
opt into a look through Qt dynamic properties (``variant``/``role``) instead of
carrying their own colour literals, so the whole application restyles from one
call to :func:`apply_theme`.

Phase 8 (per-user accent colours + light mode) can call
``apply_theme(app, primary=..., secondary=...)`` to regenerate the stylesheet
without touching a single widget.
"""

from __future__ import annotations

from PySide6.QtWidgets import QApplication, QWidget

# ── Surfaces ────────────────────────────────────────────────────────────────
BG = "#242326"
BG_SIDEBAR = "#303034"
BG_CARD = "#3B393F"
BG_ELEVATED = "#454249"
BG_INPUT = "#2E2C31"
BG_INPUT_FOCUS = "#343238"
BORDER = "#504C53"
BORDER_STRONG = "#605A62"

# ── Accent ──────────────────────────────────────────────────────────────────
PRIMARY = "#E8AAB9"
SECONDARY = "#FFEBEF"
ACCENT_HOVER = SECONDARY
ACCENT_PRESSED = "#D995A6"
TEXT_ON_ACCENT = "#2B2226"

# ── Text ────────────────────────────────────────────────────────────────────
TEXT_PRIMARY = "#F4F1F2"
TEXT_SECONDARY = "#D6D0D2"
TEXT_MUTED = "#B8B2B5"
TEXT_DISABLED = "#7C757B"

# ── Status ──────────────────────────────────────────────────────────────────
DANGER = "#E8808C"
SUCCESS = "#8FC9A8"
WARNING = "#E6C084"

# ── Auth stage ──────────────────────────────────────────────────────────────
# The split auth screen paints its own ground so the glow can sit behind the
# poster fan; the values stay here so Phase 8 can re-tint the whole surface.
AUTH_STAGE_TOP = "#2C252B"
AUTH_STAGE_BOTTOM = "#222023"
AUTH_PANE_TOP = "#2A272C"
AUTH_PANE_BOTTOM = "#222023"
AUTH_POSTER_DARK = "#3C3037"
AUTH_POSTER_DARK_END = "#2A2328"
AUTH_POSTER_WARM = "#3E3138"
AUTH_POSTER_WARM_END = "#2A2227"
SHADOW = "#000000"

# ── Geometry ────────────────────────────────────────────────────────────────
RADIUS_SM = 6
RADIUS_MD = 10
RADIUS_LG = 14
RADIUS_XL = 18
RADIUS_PILL = 999

SPACE_XS = 4
SPACE_SM = 8
SPACE_MD = 12
SPACE_LG = 16
SPACE_XL = 24
SPACE_XXL = 32

# ── Typography ──────────────────────────────────────────────────────────────
FONT_FAMILY = '"Segoe UI", "Inter", "Helvetica Neue", Arial, sans-serif'
FONT_SIZE_XS = 11
FONT_SIZE_SM = 12
FONT_SIZE_BASE = 13
FONT_SIZE_MD = 14
FONT_SIZE_LG = 16
FONT_SIZE_XL = 20
FONT_SIZE_H1 = 28
FONT_SIZE_H2 = 22
FONT_SIZE_DISPLAY = 34

# ── Layout constants shared by chrome ───────────────────────────────────────
TITLEBAR_HEIGHT = 42
SIDEBAR_WIDTH = 236
CONTROL_HEIGHT = 44
CARD_MIN_WIDTH = 210
CARD_THUMB_HEIGHT = 150

# Legacy aliases kept so older imports keep working.
BG_DARK = BG


def _rgba(color: str, alpha: float) -> str:
    """Return ``rgba(...)`` for a ``#rrggbb`` colour, else the colour itself."""
    if not color.startswith("#") or len(color) != 7:
        return color
    r, g, b = (int(color[i : i + 2], 16) for i in (1, 3, 5))
    return f"rgba({r}, {g}, {b}, {alpha})"


_QSS_TEMPLATE = """
/* ── Base ─────────────────────────────────────────────────────────────── */
QWidget {
    color: %(text)s;
    font-family: %(font)s;
    font-size: %(size_base)spx;
}
QMainWindow, QDialog {
    background-color: %(bg)s;
}
QWidget#WindowRoot, QWidget#BodyRoot {
    background-color: %(bg)s;
}
QWidget#WindowRoot {
    background-color: %(bg)s;
    border: 1px solid #3A373D;
}
QWidget#TitleBar {
    background-color: %(bg_sidebar)s;
    border-bottom: 1px solid %(border)s;
}
QWidget#Sidebar {
    background-color: %(bg_sidebar)s;
    border-right: 1px solid %(border)s;
}
QWidget#TabBar {
    background-color: %(bg)s;
    border-bottom: 1px solid %(border)s;
}
QWidget#AuthBackdrop {
    background-color: %(bg)s;
}
QScrollArea, QScrollArea > QWidget > QWidget {
    background: transparent;
    border: none;
}

QLabel {
    background: transparent;
    color: %(text)s;
}
QLabel[role="h1"] {
    font-size: %(size_h1)spx;
    font-weight: 600;
    color: %(text)s;
}
QLabel[role="h2"] {
    font-size: %(size_h2)spx;
    font-weight: 600;
    color: %(text)s;
}
QLabel[role="h3"] {
    font-size: %(size_lg)spx;
    font-weight: 600;
    color: %(text)s;
}
QLabel[role="muted"] {
    color: %(text_muted)s;
    font-size: %(size_sm)spx;
}
QLabel[role="caption"] {
    color: %(text_muted)s;
    font-size: %(size_xs)spx;
}
QLabel[role="brand"] {
    color: %(text)s;
    font-size: 17px;
    font-weight: 700;
    letter-spacing: 0.4px;
}
QLabel[role="accent"] {
    color: %(accent)s;
}
QLabel[role="error"] {
    color: %(danger)s;
    font-size: %(size_sm)spx;
}
QLabel[role="success"] {
    color: %(success)s;
    font-size: %(size_sm)spx;
}
QLabel[role="fieldLabel"] {
    color: %(text_secondary)s;
    font-size: %(size_sm)spx;
    font-weight: 600;
}
QLabel[role="username"] {
    color: %(text)s;
    font-size: %(size_base)spx;
    font-weight: 600;
}
QLabel[role="pill"] {
    background-color: %(accent_soft)s;
    color: %(accent)s;
    border-radius: %(radius_pill)spx;
    padding: 2px 9px;
    font-size: %(size_xs)spx;
    font-weight: 600;
}
QLabel[role="avatar"] {
    background-color: %(accent)s;
    color: %(on_accent)s;
    border-radius: 15px;
    font-size: %(size_base)spx;
    font-weight: 700;
}
QLabel[role="authKicker"] {
    color: %(accent)s;
    font-size: %(size_xs)spx;
    font-weight: 600;
}
QLabel[role="authDisplay"] {
    color: %(text)s;
    font-size: %(size_display)spx;
    font-weight: 600;
    letter-spacing: -0.6px;
}
QLabel[role="authDisplayAccent"] {
    color: %(accent)s;
    font-size: %(size_display)spx;
    font-weight: 600;
    letter-spacing: -0.6px;
}
QLabel[role="authLead"] {
    color: %(text_secondary)s;
    font-size: %(size_md)spx;
}
QLabel[role="warning"] {
    color: %(warning)s;
    font-size: %(size_sm)spx;
}

/* ── Surfaces ─────────────────────────────────────────────────────────── */
QFrame[role="card"] {
    background-color: %(bg_card)s;
    border: 1px solid %(border)s;
    border-radius: %(radius_lg)spx;
}
QFrame[role="panel"] {
    background-color: %(bg_card)s;
    border: 1px solid %(border)s;
    border-radius: %(radius_md)spx;
}
QFrame[role="mediaCard"] {
    background-color: %(bg_card)s;
    border: 1px solid %(border)s;
    border-radius: %(radius_md)spx;
}
QFrame[role="mediaCard"]:hover {
    background-color: %(bg_elevated)s;
    border: 1px solid %(accent)s;
}
QFrame[role="chip"] {
    background-color: %(bg_elevated)s;
    border: 1px solid %(border)s;
    border-radius: %(radius_pill)spx;
}
QFrame[role="divider"] {
    background-color: %(border)s;
    border: none;
    max-height: 1px;
    min-height: 1px;
}
QFrame[role="thumb"] {
    background-color: %(bg_elevated)s;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 %(bg_elevated)s, stop:1 %(bg_card)s);
    border: 1px solid %(border)s;
    border-radius: %(radius_md)spx;
}
QFrame[role="iconTile"] {
    background-color: %(accent_soft)s;
    border: 1px solid %(accent_soft_strong)s;
    border-radius: %(radius_lg)spx;
}
QFrame[banner="error"] {
    background-color: %(danger_soft)s;
    border: 1px solid %(danger_border)s;
    border-radius: %(radius_md)spx;
}
QFrame[banner="success"] {
    background-color: %(success_soft)s;
    border: 1px solid %(success_border)s;
    border-radius: %(radius_md)spx;
}
QFrame[banner="info"] {
    background-color: %(accent_soft)s;
    border: 1px solid %(accent_soft_strong)s;
    border-radius: %(radius_md)spx;
}
QFrame[role="authPane"] {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 %(auth_pane_top)s, stop:1 %(auth_pane_bottom)s);
    border: none;
}
QFrame[role="authPane"][split="true"] {
    border-left: 1px solid %(border)s;
}
QFrame[role="authFooter"] {
    background: transparent;
    border-top: 1px solid %(border)s;
}
QFrame[role="segmented"] {
    background-color: %(bg_input)s;
    border: 1px solid %(border)s;
    border-radius: %(radius_md)spx;
}
QFrame[role="segmentIndicator"] {
    background-color: %(accent_soft)s;
    border: 1px solid %(accent_soft_strong)s;
    border-radius: %(radius_sm)spx;
}
QFrame[role="accentRule"] {
    background-color: %(accent)s;
    border: none;
    border-radius: 2px;
}
QLabel[bannerText="error"] {
    color: %(danger)s;
    font-size: %(size_sm)spx;
}
QLabel[bannerText="success"] {
    color: %(success)s;
    font-size: %(size_sm)spx;
}
QLabel[bannerText="info"] {
    color: %(text_secondary)s;
    font-size: %(size_sm)spx;
}

/* ── Buttons ──────────────────────────────────────────────────────────── */
QPushButton {
    background-color: %(bg_elevated)s;
    color: %(text)s;
    border: 1px solid %(border)s;
    border-radius: %(radius_md)spx;
    padding: 9px 16px;
    font-size: %(size_base)spx;
}
QPushButton:hover {
    background-color: %(button_hover)s;
    border-color: %(border_strong)s;
}
QPushButton:pressed {
    background-color: %(bg_card)s;
}
QPushButton:focus {
    border-color: %(accent)s;
}
QPushButton:disabled {
    background-color: %(bg_card)s;
    color: %(text_disabled)s;
    border-color: %(bg_elevated)s;
}

QPushButton[variant="primary"] {
    background-color: %(accent)s;
    color: %(on_accent)s;
    border: 1px solid %(accent)s;
    font-weight: 600;
    padding: 11px 18px;
}
QPushButton[variant="primary"]:hover {
    background-color: %(accent_hover)s;
    border-color: %(accent_hover)s;
}
QPushButton[variant="primary"]:pressed {
    background-color: %(accent_pressed)s;
    border-color: %(accent_pressed)s;
}
QPushButton[variant="primary"]:focus {
    border: 1px solid %(text)s;
}
QPushButton[variant="primary"]:disabled {
    background-color: %(bg_elevated)s;
    border-color: %(bg_elevated)s;
    color: %(text_disabled)s;
}

QPushButton[variant="playDisc"] {
    background-color: %(accent)s;
    border: 1px solid %(accent_pressed)s;
    border-radius: 19px;
    padding: 0px;
}
QPushButton[variant="playDisc"]:hover {
    background-color: %(accent_hover)s;
    border-color: %(accent_hover)s;
}
QPushButton[variant="playDisc"]:pressed {
    background-color: %(accent_pressed)s;
}
QPushButton[variant="playDisc"]:focus {
    border: 2px solid %(on_accent)s;
}

QPushButton[variant="subtle"] {
    background-color: transparent;
    border: 1px solid %(border)s;
    color: %(text_secondary)s;
}
QPushButton[variant="subtle"]:hover {
    background-color: %(bg_elevated)s;
    color: %(text)s;
    border-color: %(border_strong)s;
}

QPushButton[variant="link"] {
    background: transparent;
    border: none;
    color: %(accent)s;
    padding: 2px 4px;
    font-size: %(size_base)spx;
    font-weight: 600;
}
QPushButton[variant="link"]:hover {
    color: %(accent_hover)s;
}
QPushButton[variant="link"]:pressed {
    color: %(accent_pressed)s;
}

QPushButton[variant="segment"] {
    background: transparent;
    border: 1px solid transparent;
    border-radius: %(radius_sm)spx;
    color: %(text_muted)s;
    padding: 7px 12px;
    font-size: %(size_base)spx;
    font-weight: 600;
}
QPushButton[variant="segment"][active="false"]:hover {
    background-color: rgba(255, 255, 255, 0.03);
    color: %(text)s;
}
QPushButton[variant="segment"][active="true"] {
    color: %(text)s;
}
QPushButton[variant="segment"]:focus {
    border-color: %(accent)s;
}

QPushButton[variant="icon"] {
    background-color: %(bg_elevated)s;
    border: 1px solid %(border)s;
    border-radius: %(radius_md)spx;
    padding: 0px;
}
QPushButton[variant="icon"]:hover {
    background-color: %(button_hover)s;
    border-color: %(accent_soft_strong)s;
}
QPushButton[variant="icon"]:pressed {
    background-color: %(bg_card)s;
    border-color: %(accent_pressed)s;
}
QPushButton[variant="icon"]:focus {
    border: 1px solid %(accent)s;
}
QPushButton[variant="icon"]:disabled {
    background-color: %(bg_card)s;
    border-color: %(bg_elevated)s;
}

QPushButton[variant="nav"] {
    background: transparent;
    border: none;
    border-radius: %(radius_md)spx;
    color: %(text_muted)s;
    padding: 10px 12px;
    text-align: left;
    font-size: %(size_md)spx;
}
QPushButton[variant="nav"]:hover {
    background-color: rgba(255, 255, 255, 0.055);
    color: %(text)s;
}
QPushButton[variant="nav"][active="true"] {
    background-color: %(accent_soft_strong)s;
    color: %(accent)s;
    font-weight: 600;
}

QPushButton[variant="tab"] {
    background: transparent;
    border: none;
    border-bottom: 2px solid transparent;
    border-radius: 0px;
    color: %(text_muted)s;
    padding: 12px 18px;
    font-size: %(size_base)spx;
}
QPushButton[variant="tab"]:hover {
    color: %(text)s;
    border-bottom: 2px solid %(accent_soft_strong)s;
}
QPushButton[variant="tab"][active="true"] {
    color: %(accent)s;
    border-bottom: 2px solid %(accent)s;
    font-weight: 600;
}
QPushButton[variant="tab"]:disabled {
    color: %(text_disabled)s;
    border-bottom-color: transparent;
}

QPushButton[variant="window"] {
    background: transparent;
    border: none;
    border-radius: 0px;
    color: %(text_muted)s;
    padding: 0px;
    font-size: 13px;
}
QPushButton[variant="window"]:hover {
    background-color: rgba(255, 255, 255, 0.09);
    color: %(text)s;
}
QPushButton[variant="window"]:pressed {
    background-color: rgba(255, 255, 255, 0.14);
}
QPushButton[variant="window"][windowRole="close"]:hover {
    background-color: #C05661;
    color: #FFFFFF;
}

/* ── Inputs ───────────────────────────────────────────────────────────── */
QLineEdit {
    background-color: %(bg_input)s;
    color: %(text)s;
    border: 1px solid %(border)s;
    border-radius: %(radius_md)spx;
    padding: 10px 12px;
    font-size: %(size_base)spx;
    selection-background-color: %(accent)s;
    selection-color: %(on_accent)s;
}
QLineEdit:hover {
    border-color: %(border_strong)s;
}
QLineEdit:focus {
    border: 1px solid %(accent)s;
    background-color: %(bg_input_focus)s;
}
QLineEdit[error="true"] {
    border: 1px solid %(danger)s;
}
QLineEdit[error="true"]:focus {
    border: 1px solid %(danger)s;
}
QLineEdit:disabled {
    color: %(text_disabled)s;
    background-color: %(bg_card)s;
}
QLineEdit::placeholder {
    color: %(text_muted)s;
}
QLineEdit[iconField="true"] {
    padding: 0px;
}

QComboBox {
    background-color: %(bg_input)s;
    color: %(text)s;
    border: 1px solid %(border)s;
    border-radius: %(radius_md)spx;
    padding: 8px 12px;
    min-width: 120px;
}
QComboBox:hover {
    border-color: %(border_strong)s;
}
QComboBox:focus {
    border-color: %(accent)s;
}
QComboBox::drop-down {
    border: none;
    width: 24px;
}
QComboBox QAbstractItemView {
    background-color: %(bg_elevated)s;
    color: %(text)s;
    border: 1px solid %(border)s;
    selection-background-color: %(accent_soft_strong)s;
    selection-color: %(text)s;
    outline: none;
}

/* ── Checkbox ─────────────────────────────────────────────────────────── */
QCheckBox {
    background: transparent;
    color: %(text_secondary)s;
    spacing: 9px;
    font-size: %(size_base)spx;
}
QCheckBox:hover {
    color: %(text)s;
}
QCheckBox::indicator {
    width: 17px;
    height: 17px;
    border: 1px solid %(border_strong)s;
    border-radius: 5px;
    background-color: %(bg_input)s;
}
QCheckBox::indicator:hover {
    border-color: %(accent)s;
}
QCheckBox::indicator:checked {
    background-color: %(accent)s;
    border-color: %(accent)s;
    image: url("%(check_icon)s");
}

/* ── Table ────────────────────────────────────────────────────────────── */
QTableWidget {
    background-color: %(bg_card)s;
    color: %(text)s;
    border: 1px solid %(border)s;
    border-radius: %(radius_md)spx;
    gridline-color: %(border)s;
    selection-background-color: %(accent_soft)s;
    selection-color: %(text)s;
    font-size: %(size_sm)spx;
}
QTableWidget::item {
    padding: 6px 10px;
}
QTableWidget::item:selected {
    background-color: %(accent_soft)s;
    color: %(text)s;
}
QTableWidget::item:alternate {
    background-color: %(bg_elevated)s;
}
QHeaderView::section {
    background-color: %(bg_sidebar)s;
    color: %(text_secondary)s;
    border: none;
    border-bottom: 1px solid %(border)s;
    border-right: 1px solid %(border)s;
    padding: 8px 10px;
    font-size: %(size_sm)spx;
    font-weight: 600;
}
QHeaderView::section:last {
    border-right: none;
}

/* ── Scrollbars ───────────────────────────────────────────────────────── */
QScrollBar:vertical {
    background: transparent;
    width: 10px;
    margin: 0px;
}
QScrollBar::handle:vertical {
    background: #5A555C;
    border-radius: 5px;
    min-height: 32px;
}
QScrollBar::handle:vertical:hover {
    background: #736C74;
}
QScrollBar:horizontal {
    background: transparent;
    height: 10px;
    margin: 0px;
}
QScrollBar::handle:horizontal {
    background: #5A555C;
    border-radius: 5px;
    min-width: 32px;
}
QScrollBar::handle:horizontal:hover {
    background: #736C74;
}
QScrollBar::add-line, QScrollBar::sub-line {
    width: 0px;
    height: 0px;
}
QScrollBar::add-page, QScrollBar::sub-page {
    background: transparent;
}

/* ── Misc ─────────────────────────────────────────────────────────────── */
QToolTip {
    background-color: %(bg_elevated)s;
    color: %(text)s;
    border: 1px solid %(border)s;
    padding: 6px 9px;
    border-radius: %(radius_sm)spx;
}
QMenu {
    background-color: %(bg_elevated)s;
    color: %(text)s;
    border: 1px solid %(border)s;
    border-radius: %(radius_md)spx;
    padding: 6px;
}
QMenu::item {
    padding: 7px 18px;
    border-radius: %(radius_sm)spx;
}
QMenu::item:selected {
    background-color: %(accent_soft_strong)s;
    color: %(text)s;
}
"""


def build_stylesheet(primary: str | None = None, secondary: str | None = None) -> str:
    """Generate the application stylesheet from the current tokens.

    ``primary``/``secondary`` allow per-user accent overrides (Phase 8) without
    forking this module.
    """
    accent = primary or PRIMARY
    accent_hover = secondary or ACCENT_HOVER
    tokens = {
        "bg": BG,
        "bg_sidebar": BG_SIDEBAR,
        "bg_card": BG_CARD,
        "bg_elevated": BG_ELEVATED,
        "bg_input": BG_INPUT,
        "bg_input_focus": BG_INPUT_FOCUS,
        "auth_pane_top": AUTH_PANE_TOP,
        "auth_pane_bottom": AUTH_PANE_BOTTOM,
        "border": BORDER,
        "border_strong": BORDER_STRONG,
        "button_hover": "#4C474E",
        "accent": accent,
        "accent_hover": accent_hover,
        "accent_pressed": ACCENT_PRESSED,
        "accent_soft": _rgba(accent, 0.16),
        "accent_soft_strong": _rgba(accent, 0.30),
        "on_accent": TEXT_ON_ACCENT,
        "text": TEXT_PRIMARY,
        "text_secondary": TEXT_SECONDARY,
        "text_muted": TEXT_MUTED,
        "text_disabled": TEXT_DISABLED,
        "danger": DANGER,
        "danger_soft": _rgba(DANGER, 0.12),
        "danger_border": _rgba(DANGER, 0.35),
        "success": SUCCESS,
        "success_soft": _rgba(SUCCESS, 0.12),
        "success_border": _rgba(SUCCESS, 0.35),
        "warning": WARNING,
        "font": FONT_FAMILY,
        "size_xs": FONT_SIZE_XS,
        "size_sm": FONT_SIZE_SM,
        "size_base": FONT_SIZE_BASE,
        "size_md": FONT_SIZE_MD,
        "size_lg": FONT_SIZE_LG,
        "size_h1": FONT_SIZE_H1,
        "size_h2": FONT_SIZE_H2,
        "size_display": FONT_SIZE_DISPLAY,
        "radius_sm": RADIUS_SM,
        "radius_md": RADIUS_MD,
        "radius_lg": RADIUS_LG,
        "radius_pill": RADIUS_PILL,
        "check_icon": _check_icon_path(),
    }
    return _QSS_TEMPLATE % tokens


def _check_icon_path() -> str:
    """Absolute path to the checkbox tick, if the asset is present."""
    from pathlib import Path

    icon = Path(__file__).resolve().parent.parent / "assets" / "icons" / "check.svg"
    if icon.exists():
        return str(icon).replace("\\", "/")
    return ""


QSS = build_stylesheet()


def apply_theme(
    app: QApplication,
    primary: str | None = None,
    secondary: str | None = None,
) -> None:
    """Apply (or re-apply) the application stylesheet."""
    app.setStyleSheet(build_stylesheet(primary, secondary))


def restyle(widget: QWidget) -> None:
    """Re-evaluate style selectors after a dynamic property changes."""
    style = widget.style()
    style.unpolish(widget)
    style.polish(widget)
    widget.update()
