"""
gui/dashboard_widget.py  –  MobilityX live metrics panel
All metric cards displayed in a single unified sidebar.
"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
                              QLabel, QFrame, QProgressBar, QGridLayout)
from PyQt6.QtCore   import Qt, QPropertyAnimation, QEasingCurve, pyqtProperty, QSize
from PyQt6.QtGui    import (QColor, QPainter, QPen, QLinearGradient,
                             QFont, QBrush, QPainterPath)

from gui.styles import (BG_CARD, BG_CARD2, BG_BORDER, BG_PANEL, BG_DARK,
                        TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
                        ACCENT_CYAN, ACCENT_BLUE, ACCENT_RED,
                        ACCENT_AMBER, ACCENT_GREEN, ACCENT_PURPLE)


# ─────────────────────────────────────────────────────────────────────────────
#  Thin glowing divider line
# ─────────────────────────────────────────────────────────────────────────────
class GlowDivider(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(2)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        grad = QLinearGradient(0, 0, self.width(), 0)
        grad.setColorAt(0.0, QColor(0, 0, 0, 0))
        grad.setColorAt(0.3, QColor(ACCENT_CYAN))
        grad.setColorAt(0.7, QColor(ACCENT_BLUE))
        grad.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(grad))
        p.drawRect(0, 0, self.width(), 2)


# ─────────────────────────────────────────────────────────────────────────────
#  Animated risk / value bar
# ─────────────────────────────────────────────────────────────────────────────
class MiniBar(QWidget):
    """Thin horizontal bar that fills based on a 0-100 value."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(4)
        self._value = 0
        self._color = QColor(ACCENT_GREEN)

    def set_value(self, pct: int, color: str):
        self._value = max(0, min(100, pct))
        self._color = QColor(color)
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w = self.width()
        h = self.height()
        # track
        p.setBrush(QColor(BG_BORDER))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(0, 0, w, h, 2, 2)
        # fill
        fill_w = int(w * self._value / 100)
        if fill_w > 0:
            grad = QLinearGradient(0, 0, fill_w, 0)
            grad.setColorAt(0, self._color.darker(140))
            grad.setColorAt(1, self._color)
            p.setBrush(QBrush(grad))
            p.drawRoundedRect(0, 0, fill_w, h, 2, 2)


# ─────────────────────────────────────────────────────────────────────────────
#  Single metric card  (icon  title  value  unit  mini-bar)
# ─────────────────────────────────────────────────────────────────────────────
class MetricCard(QFrame):
    def __init__(self, icon: str, title: str, unit: str = "",
                 show_bar: bool = False, parent=None):
        super().__init__(parent)
        self._border_color = QColor(BG_BORDER)
        self._icon   = icon
        self._title  = title
        self._unit   = unit
        self._show_bar = show_bar

        self.setFixedHeight(82)
        self._apply_base_style()

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 8, 12, 6)
        root.setSpacing(2)

        # ── top row: icon + title ──
        top = QHBoxLayout()
        top.setSpacing(6)

        icon_lbl = QLabel(icon)
        icon_lbl.setStyleSheet(
            f"color:{ACCENT_CYAN};font-size:13px;background:transparent;border:none;"
        )
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(
            f"color:{TEXT_SECONDARY};font-size:9px;letter-spacing:1.5px;"
            f"font-weight:700;background:transparent;border:none;"
        )
        top.addWidget(icon_lbl)
        top.addWidget(title_lbl)
        top.addStretch()
        root.addLayout(top)

        # ── value + unit row ──
        val_row = QHBoxLayout()
        val_row.setSpacing(4)
        val_row.setContentsMargins(0, 0, 0, 0)

        self._value_lbl = QLabel("—")
        self._value_lbl.setStyleSheet(
            f"color:{TEXT_PRIMARY};font-size:24px;font-weight:700;"
            f"font-family:'Segoe UI';background:transparent;border:none;"
        )
        self._unit_lbl = QLabel(unit)
        self._unit_lbl.setStyleSheet(
            f"color:{TEXT_SECONDARY};font-size:11px;background:transparent;border:none;"
        )
        val_row.addWidget(self._value_lbl)
        val_row.addWidget(self._unit_lbl, alignment=Qt.AlignmentFlag.AlignBottom)
        val_row.addStretch()
        root.addLayout(val_row)

        # ── mini progress bar (optional) ──
        self._bar = MiniBar(self)
        if not show_bar:
            self._bar.setVisible(False)
        root.addWidget(self._bar)

    # ── style helpers ─────────────────────────────────────────────────────────
    def _apply_base_style(self, border: str = BG_BORDER):
        self.setStyleSheet(
            f"QFrame{{background:{BG_CARD};border-radius:10px;"
            f"border:1px solid {border};}}"
        )

    # ── animated border colour property ──────────────────────────────────────
    def get_border_color(self) -> QColor: return self._border_color
    def set_border_color(self, c: QColor):
        self._border_color = c
        self.setStyleSheet(
            f"QFrame{{background:{BG_CARD};border-radius:10px;"
            f"border:1px solid {c.name()};}}"
        )
    borderColor = pyqtProperty(QColor, get_border_color, set_border_color)

    # ── public API ─────────────────────────────────────────────────────────
    def set_value(self, val: str, level: str = "safe", bar_pct: int = 0):
        self._value_lbl.setText(val)
        color_map = {
            "safe":     ACCENT_GREEN,
            "warning":  ACCENT_AMBER,
            "critical": ACCENT_RED,
        }
        target_hex = color_map.get(level, BG_BORDER)
        target = QColor(target_hex)

        # value label colour
        self._value_lbl.setStyleSheet(
            f"color:{target_hex};font-size:24px;font-weight:700;"
            f"font-family:'Segoe UI';background:transparent;border:none;"
        )

        # animated border
        anim = QPropertyAnimation(self, b"borderColor", self)
        anim.setDuration(400)
        anim.setEndValue(target)
        anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
        anim.start()
        self._anim = anim

        if self._show_bar:
            self._bar.set_value(bar_pct, target_hex)


# ─────────────────────────────────────────────────────────────────────────────
#  Section header
# ─────────────────────────────────────────────────────────────────────────────
class SectionHeader(QLabel):
    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setStyleSheet(
            f"color:{TEXT_MUTED};font-size:9px;font-weight:700;"
            f"letter-spacing:2px;background:transparent;border:none;"
            f"padding: 6px 2px 2px 2px;"
        )


# ─────────────────────────────────────────────────────────────────────────────
#  DashboardWidget  –  All metrics unified in one panel
# ─────────────────────────────────────────────────────────────────────────────
class DashboardWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(280)
        self._setup_ui()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 8)
        root.setSpacing(4)

        # ── Brand header ──────────────────────────────────────────────────
        brand = QWidget()
        brand.setStyleSheet(
            f"background: qlineargradient(x1:0,y1:0,x2:1,y2:1,"
            f"stop:0 #0E1D35, stop:1 #091426);"
            f"border-radius:12px;border:1px solid {BG_BORDER};"
        )
        brand.setFixedHeight(64)
        brand_l = QHBoxLayout(brand)
        brand_l.setContentsMargins(14, 8, 14, 8)

        logo = QLabel("🚗")
        logo.setStyleSheet("font-size:28px;background:transparent;border:none;")

        name_col = QVBoxLayout()
        name_col.setSpacing(0)
        name_lbl = QLabel("MobilityX")
        name_lbl.setStyleSheet(
            "font-size:18px;font-weight:800;"
            f"color:{ACCENT_CYAN};"
            "letter-spacing:1px;background:transparent;border:none;"
        )
        sub_lbl = QLabel("AI DRIVER ASSISTANCE")
        sub_lbl.setStyleSheet(
            f"font-size:8px;font-weight:700;color:{TEXT_SECONDARY};"
            "letter-spacing:2px;background:transparent;border:none;"
        )
        name_col.addWidget(name_lbl)
        name_col.addWidget(sub_lbl)

        # Live dot indicator
        self._live_dot = QLabel("● LIVE")
        self._live_dot.setStyleSheet(
            f"font-size:9px;font-weight:700;color:{ACCENT_GREEN};"
            "background:transparent;border:none;"
        )

        brand_l.addWidget(logo)
        brand_l.addSpacing(6)
        brand_l.addLayout(name_col, stretch=1)
        brand_l.addWidget(self._live_dot, alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        root.addWidget(brand)

        root.addWidget(GlowDivider())

        # ── DRIVING METRICS ───────────────────────────────────────────────
        root.addWidget(SectionHeader("DRIVING METRICS"))

        grid1 = QGridLayout()
        grid1.setSpacing(6)

        self._dist_card  = MetricCard("📡", "DISTANCE",       "m",    show_bar=False)
        self._ttc_card   = MetricCard("⏱", "TIME TO COLL.",  "s",    show_bar=False)
        self._speed_card = MetricCard("🏎", "SPEED EST.",    "km/h", show_bar=False)
        self._risk_card  = MetricCard("⚠", "RISK LEVEL",    "%",    show_bar=True)

        grid1.addWidget(self._dist_card,  0, 0)
        grid1.addWidget(self._ttc_card,   0, 1)
        grid1.addWidget(self._speed_card, 1, 0)
        grid1.addWidget(self._risk_card,  1, 1)
        root.addLayout(grid1)

        # ── SYSTEM METRICS ────────────────────────────────────────────────
        root.addWidget(SectionHeader("SYSTEM METRICS"))

        grid2 = QGridLayout()
        grid2.setSpacing(6)

        self._fps_card   = MetricCard("💻", "FRAME RATE", "fps", show_bar=True)
        self._obj_card   = MetricCard("🎯", "OBJECTS",    "",    show_bar=False)

        grid2.addWidget(self._fps_card, 0, 0)
        grid2.addWidget(self._obj_card, 0, 1)
        root.addLayout(grid2)

        root.addWidget(GlowDivider())

        # ── DETECTED CLASSES ──────────────────────────────────────────────
        root.addWidget(SectionHeader("DETECTED CLASSES"))

        self._counts_lbl = QLabel("—")
        self._counts_lbl.setWordWrap(True)
        self._counts_lbl.setStyleSheet(
            f"color:{TEXT_PRIMARY};font-size:11px;line-height:1.7;"
            f"background:transparent;padding:2px 2px;"
        )
        root.addWidget(self._counts_lbl)

        root.addWidget(GlowDivider())

        # ── ALERT LOG section header ──────────────────────────────────────
        root.addWidget(SectionHeader("ALERT LOG"))

        root.addStretch()

    # ── public API ────────────────────────────────────────────────────────────
    def update_metrics(self, m: dict):
        dist   = m.get("distance",  0.0)
        ttc    = m.get("ttc",       0.0)
        risk   = m.get("risk",      0.0)
        speed  = m.get("speed",     0.0)
        fps    = m.get("fps",       0.0)
        objs   = m.get("objects",   0)
        counts = m.get("class_counts", {})

        # Distance
        d_level = "critical" if dist < 8 else "warning" if dist < 15 else "safe"
        self._dist_card.set_value(
            f"{dist:.1f}" if dist > 0 else "—",
            d_level if dist > 0 else "safe"
        )

        # TTC
        if ttc > 0:
            t_level = "critical" if ttc < 1.5 else "warning" if ttc < 3 else "safe"
        else:
            t_level = "safe"
        self._ttc_card.set_value(f"{ttc:.1f}" if ttc else "—", t_level)

        # Risk (0-1 → %)
        r_pct   = int(risk * 100)
        r_level = "critical" if r_pct > 70 else "warning" if r_pct > 40 else "safe"
        self._risk_card.set_value(f"{r_pct}", r_level, bar_pct=r_pct)

        # Speed
        self._speed_card.set_value(f"{speed:.0f}", "safe")

        # FPS
        f_pct   = min(100, int(fps / 30 * 100))
        f_level = "critical" if fps < 5 else "warning" if fps < 12 else "safe"
        self._fps_card.set_value(f"{fps:.0f}", f_level, bar_pct=f_pct)

        # Objects
        self._obj_card.set_value(str(objs), "safe")

        # Class counts
        if counts:
            lines = []
            for cls, cnt in sorted(counts.items(), key=lambda x: -x[1]):
                lines.append(
                    f"<span style='color:{ACCENT_CYAN};font-weight:600;'>{cls}</span>"
                    f"<span style='color:{TEXT_SECONDARY};'> × {cnt}</span>"
                )
            self._counts_lbl.setText("&nbsp;&nbsp;".join(lines))
        else:
            self._counts_lbl.setText(
                f"<span style='color:{TEXT_MUTED};'>No objects detected</span>"
            )
