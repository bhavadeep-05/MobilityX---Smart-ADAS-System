"""
gui/alert_widget.py  –  Scrollable colour-coded alert log
"""
import csv
import time

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
                              QLabel, QScrollArea, QFrame, QPushButton,
                              QFileDialog)
from PyQt6.QtCore  import Qt, QDateTime
from PyQt6.QtGui   import QColor

from gui.styles import (BG_CARD, BG_CARD2, BG_PANEL, BG_BORDER, BG_DARK,
                         TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
                         ACCENT_CYAN, ACCENT_RED, ACCENT_AMBER)


LEVEL_STYLE = {
    "critical": (ACCENT_RED,    "🚨"),
    "warning":  (ACCENT_AMBER,  "⚠"),
    "info":     (ACCENT_CYAN,   "ℹ"),
}


class AlertEntry(QFrame):
    def __init__(self, level: str, message: str, parent=None):
        super().__init__(parent)
        color, icon = LEVEL_STYLE.get(level, (TEXT_SECONDARY, "•"))
        ts = QDateTime.currentDateTime().toString("hh:mm:ss")

        self.setStyleSheet(
            f"QFrame{{background:{BG_CARD};border-left:3px solid {color};"
            f"border-radius:6px;margin:1px 2px;"
            f"border-top:1px solid {BG_BORDER};border-right:1px solid {BG_BORDER};"
            f"border-bottom:1px solid {BG_BORDER};}}"
        )

        lay = QHBoxLayout(self)
        lay.setContentsMargins(8, 5, 8, 5)
        lay.setSpacing(8)

        icon_lbl = QLabel(icon)
        icon_lbl.setStyleSheet(f"color:{color};font-size:14px;min-width:18px; background:transparent;border:none;")
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignTop)

        body = QVBoxLayout()
        body.setSpacing(0)

        msg_lbl = QLabel(message)
        msg_lbl.setStyleSheet(
            f"color:{TEXT_PRIMARY};font-size:12px;font-weight:600;background:transparent;border:none;"
        )
        msg_lbl.setWordWrap(True)

        ts_lbl = QLabel(ts)
        ts_lbl.setStyleSheet(
            f"color:{TEXT_SECONDARY};font-size:10px;background:transparent;border:none;"
        )

        body.addWidget(msg_lbl)
        body.addWidget(ts_lbl)

        lay.addWidget(icon_lbl, alignment=Qt.AlignmentFlag.AlignTop)
        lay.addLayout(body, stretch=1)


class AlertWidget(QWidget):
    """Scrollable alert log with Clear + Export CSV buttons."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._entries: list[tuple[str, str, str]] = []  # (ts, level, msg)
        self._setup_ui()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 6)
        root.setSpacing(6)

        # header row
        hdr_row = QHBoxLayout()
        hdr = QLabel("ALERT  LOG")
        hdr.setStyleSheet(
            f"color:{ACCENT_CYAN};font-size:10px;font-weight:700;letter-spacing:2px;"
            f"background:transparent;border:none;"
        )
        hdr_row.addWidget(hdr)
        hdr_row.addStretch()

        self._count_lbl = QLabel("0 alerts")
        self._count_lbl.setStyleSheet(
            f"color:{TEXT_SECONDARY};font-size:10px;"
        )
        hdr_row.addWidget(self._count_lbl)
        root.addLayout(hdr_row)

        # scroll area
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setStyleSheet(
            f"QScrollArea{{background:{BG_DARK};border:1px solid {BG_BORDER};"
            f"border-radius:8px;}}"
        )

        self._inner = QWidget()
        self._inner.setStyleSheet(f"background:{BG_DARK};")
        self._inner_layout = QVBoxLayout(self._inner)
        self._inner_layout.setContentsMargins(4, 4, 4, 4)
        self._inner_layout.setSpacing(3)
        self._inner_layout.addStretch()

        self._scroll.setWidget(self._inner)
        root.addWidget(self._scroll, stretch=1)

        # buttons
        btn_row = QHBoxLayout()
        self._clear_btn  = QPushButton("🗑  Clear")
        self._export_btn = QPushButton("💾  Export CSV")

        for btn in (self._clear_btn, self._export_btn):
            btn.setStyleSheet(
                f"QPushButton{{background:{BG_CARD};color:{TEXT_SECONDARY};"
                f"border:1px solid {BG_BORDER};border-radius:7px;padding:5px 10px;"
                f"font-size:11px;font-weight:500;}}"
                f"QPushButton:hover{{border-color:{ACCENT_CYAN};color:{ACCENT_CYAN};"
                f"background:{BG_CARD2};}}"
            )
        self._clear_btn.clicked.connect(self._clear)
        self._export_btn.clicked.connect(self._export_csv)

        btn_row.addWidget(self._clear_btn)
        btn_row.addStretch()
        btn_row.addWidget(self._export_btn)
        root.addLayout(btn_row)

    # ── public API ────────────────────────────────────────────────────────────
    def add_alert(self, level: str, message: str):
        ts = QDateTime.currentDateTime().toString("hh:mm:ss")
        self._entries.append((ts, level, message))
        self._count_lbl.setText(f"{len(self._entries)} alerts")

        entry = AlertEntry(level, message)
        # Insert before the trailing stretch
        count = self._inner_layout.count()
        self._inner_layout.insertWidget(count - 1, entry)

        # Auto-scroll to bottom
        self._scroll.verticalScrollBar().setValue(
            self._scroll.verticalScrollBar().maximum()
        )

    def _clear(self):
        self._entries.clear()
        self._count_lbl.setText("0 alerts")
        # Remove all widgets except the stretch
        while self._inner_layout.count() > 1:
            item = self._inner_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _export_csv(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Alert Log", "adas_alerts.csv",
            "CSV Files (*.csv)"
        )
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["Timestamp", "Level", "Message"])
            w.writerows(self._entries)
