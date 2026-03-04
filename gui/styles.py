"""
gui/styles.py  –  MobilityX premium dark theme.
Deep-navy carbon palette with electric-blue / emerald / amber-alert accents.
"""

# ── Palette ───────────────────────────────────────────────────────────────────
ACCENT_CYAN   = "#00D4FF"      # electric blue
ACCENT_BLUE   = "#0077FF"      # deeper accent
ACCENT_RED    = "#FF2D55"      # alert red
ACCENT_AMBER  = "#FFB800"      # warning amber
ACCENT_GREEN  = "#00E676"      # safe green
ACCENT_PURPLE = "#8B5CF6"      # subtle purple

BG_DARK       = "#080C14"      # deepest background
BG_PANEL      = "#0E1421"      # side panel
BG_CARD       = "#131B2E"      # card surface
BG_CARD2      = "#192338"      # slightly lighter card
BG_BORDER     = "#1E2D4A"      # subtle border
BG_GLOW       = "#00D4FF22"    # glow overlay

TEXT_PRIMARY   = "#E8F0FE"
TEXT_SECONDARY = "#5C7FAA"
TEXT_MUTED     = "#2D4A6E"

# ── Brand colours (used in header gradient) ───────────────────────────────────
BRAND_GRAD_START = "#00D4FF"
BRAND_GRAD_END   = "#0077FF"

APP_STYLESHEET = f"""
/* ── Global ──────────────────────────────────────────────────────────────── */
QMainWindow, QDialog {{
    background-color: {BG_DARK};
    color: {TEXT_PRIMARY};
    font-family: "Segoe UI", "Inter", "Arial", sans-serif;
    font-size: 13px;
}}

QWidget {{
    background-color: transparent;
    color: {TEXT_PRIMARY};
}}

/* ── Menu bar ────────────────────────────────────────────────────────────── */
QMenuBar {{
    background-color: {BG_PANEL};
    color: {TEXT_PRIMARY};
    border-bottom: 1px solid {BG_BORDER};
    padding: 3px 6px;
    font-size: 12px;
}}
QMenuBar::item {{
    padding: 4px 10px;
    border-radius: 4px;
}}
QMenuBar::item:selected {{
    background: {BG_CARD2};
    color: {ACCENT_CYAN};
}}
QMenu {{
    background-color: {BG_PANEL};
    color: {TEXT_PRIMARY};
    border: 1px solid {BG_BORDER};
    border-radius: 8px;
    padding: 4px;
}}
QMenu::item {{
    padding: 6px 14px;
    border-radius: 4px;
}}
QMenu::item:selected {{
    background-color: {BG_CARD2};
    color: {ACCENT_CYAN};
}}
QMenu::separator {{
    height: 1px;
    background: {BG_BORDER};
    margin: 4px 8px;
}}

/* ── Status bar ──────────────────────────────────────────────────────────── */
QStatusBar {{
    background-color: {BG_PANEL};
    color: {TEXT_SECONDARY};
    border-top: 1px solid {BG_BORDER};
    font-size: 11px;
}}
QStatusBar::item {{ border: none; }}

/* ── Scroll bars ─────────────────────────────────────────────────────────── */
QScrollBar:vertical {{
    background: {BG_DARK};
    width: 6px;
    border-radius: 3px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {BG_BORDER};
    border-radius: 3px;
    min-height: 20px;
}}
QScrollBar::handle:vertical:hover {{
    background: {ACCENT_CYAN};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: none; }}

/* ── Push buttons ────────────────────────────────────────────────────────── */
QPushButton {{
    background-color: {BG_CARD};
    color: {TEXT_PRIMARY};
    border: 1px solid {BG_BORDER};
    border-radius: 7px;
    padding: 7px 16px;
    font-weight: 500;
}}
QPushButton:hover {{
    background-color: {BG_CARD2};
    border-color: {ACCENT_CYAN};
    color: {ACCENT_CYAN};
}}
QPushButton:pressed {{
    background-color: {BG_DARK};
    border-color: {ACCENT_BLUE};
}}
QPushButton#danger {{
    border-color: {ACCENT_RED};
    color: {ACCENT_RED};
}}
QPushButton#danger:hover {{
    background-color: #1a0010;
}}
QPushButton#accent {{
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                stop:0 {ACCENT_BLUE}, stop:1 {ACCENT_CYAN});
    color: #fff;
    border: none;
    font-weight: 700;
}}
QPushButton#accent:hover {{
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                stop:0 {ACCENT_CYAN}, stop:1 {ACCENT_BLUE});
}}

/* ── Sliders ─────────────────────────────────────────────────────────────── */
QSlider::groove:horizontal {{
    height: 4px;
    background: {BG_BORDER};
    border-radius: 2px;
}}
QSlider::handle:horizontal {{
    background: {ACCENT_CYAN};
    border: none;
    width: 14px; height: 14px;
    margin: -5px 0;
    border-radius: 7px;
}}
QSlider::sub-page:horizontal {{
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                stop:0 {ACCENT_BLUE}, stop:1 {ACCENT_CYAN});
    border-radius: 2px;
}}

/* ── Combo box ───────────────────────────────────────────────────────────── */
QComboBox {{
    background-color: {BG_CARD};
    border: 1px solid {BG_BORDER};
    border-radius: 7px;
    padding: 5px 10px;
    color: {TEXT_PRIMARY};
}}
QComboBox:hover {{ border-color: {ACCENT_CYAN}; }}
QComboBox::drop-down {{
    border: none;
    width: 20px;
}}
QComboBox QAbstractItemView {{
    background-color: {BG_PANEL};
    color: {TEXT_PRIMARY};
    selection-background-color: {BG_CARD2};
    border: 1px solid {BG_BORDER};
    border-radius: 6px;
}}

/* ── Check boxes ─────────────────────────────────────────────────────────── */
QCheckBox {{
    spacing: 8px;
    color: {TEXT_PRIMARY};
}}
QCheckBox::indicator {{
    width: 16px; height: 16px;
    border: 1px solid {BG_BORDER};
    border-radius: 4px;
    background: {BG_CARD};
}}
QCheckBox::indicator:checked {{
    background-color: {ACCENT_CYAN};
    border-color: {ACCENT_CYAN};
    image: none;
}}
QCheckBox::indicator:hover {{ border-color: {ACCENT_CYAN}; }}

/* ── Group boxes ─────────────────────────────────────────────────────────── */
QGroupBox {{
    border: 1px solid {BG_BORDER};
    border-radius: 10px;
    margin-top: 14px;
    padding: 10px;
    color: {TEXT_SECONDARY};
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 1px;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    padding: 0 5px;
    color: {ACCENT_CYAN};
}}

/* ── Labels ──────────────────────────────────────────────────────────────── */
QLabel {{ color: {TEXT_PRIMARY}; }}

/* ── Line edit ───────────────────────────────────────────────────────────── */
QLineEdit {{
    background-color: {BG_CARD};
    border: 1px solid {BG_BORDER};
    border-radius: 7px;
    padding: 5px 10px;
    color: {TEXT_PRIMARY};
}}
QLineEdit:focus {{ border-color: {ACCENT_CYAN}; }}

/* ── Splitter ────────────────────────────────────────────────────────────── */
QSplitter::handle {{
    background: {BG_BORDER};
    width: 3px;
}}
QSplitter::handle:hover {{ background: {ACCENT_CYAN}; }}
"""


def risk_color(level: str) -> str:
    """level: 'safe' | 'warning' | 'critical'"""
    return {
        "safe":     ACCENT_GREEN,
        "warning":  ACCENT_AMBER,
        "critical": ACCENT_RED,
    }.get(level, BG_BORDER)
