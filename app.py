"""
app.py  –  MobilityX AI Driver Assistance – Application Entry Point
Run with:
    python app.py
"""
import sys
from PyQt6.QtWidgets import QApplication, QSplashScreen
from PyQt6.QtCore    import Qt, QTimer, QRect
from PyQt6.QtGui     import QPixmap, QColor, QFont, QPainter, QLinearGradient, QBrush

from gui.main_window import MainWindow
from gui.styles      import APP_STYLESHEET, ACCENT_CYAN, ACCENT_BLUE, BG_DARK


def _make_splash() -> QSplashScreen:
    """Generate a MobilityX branded splash screen programmatically."""
    w, h = 660, 280
    pix = QPixmap(w, h)
    pix.fill(QColor(BG_DARK))

    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    # ── Deep navy background gradient ──
    bg = QLinearGradient(0, 0, w, h)
    bg.setColorAt(0.0, QColor("#080C14"))
    bg.setColorAt(0.5, QColor("#0C1525"))
    bg.setColorAt(1.0, QColor("#080C14"))
    painter.fillRect(0, 0, w, h, bg)

    # ── Glow top accent bar ──
    bar_grad = QLinearGradient(0, 0, w, 0)
    bar_grad.setColorAt(0.0, QColor(0, 0, 0, 0))
    bar_grad.setColorAt(0.3, QColor(ACCENT_CYAN))
    bar_grad.setColorAt(0.7, QColor(ACCENT_BLUE))
    bar_grad.setColorAt(1.0, QColor(0, 0, 0, 0))
    painter.setBrush(QBrush(bar_grad))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRect(0, 0, w, 3)

    # ── Car emoji / logo ──
    logo_font = QFont("Segoe UI Emoji", 36)
    painter.setFont(logo_font)
    painter.setPen(QColor(ACCENT_CYAN))
    painter.drawText(QRect(40, 50, 60, 60), Qt.AlignmentFlag.AlignCenter, "🚗")

    # ── Brand name ──
    name_font = QFont("Segoe UI", 34, QFont.Weight.Black)
    painter.setFont(name_font)
    grad_text = QLinearGradient(110, 0, 340, 0)
    grad_text.setColorAt(0.0, QColor(ACCENT_CYAN))
    grad_text.setColorAt(1.0, QColor(ACCENT_BLUE))
    painter.setPen(QColor(ACCENT_CYAN))
    painter.drawText(110, 100, "MobilityX")

    # ── Subtitle ──
    sub_font = QFont("Segoe UI", 11)
    painter.setFont(sub_font)
    painter.setPen(QColor("#5C7FAA"))
    painter.drawText(112, 128, "AI DRIVER ASSISTANCE SYSTEM")

    # ── Thin separator ──
    sep_grad = QLinearGradient(40, 0, w - 40, 0)
    sep_grad.setColorAt(0.0, QColor(0, 0, 0, 0))
    sep_grad.setColorAt(0.3, QColor(ACCENT_CYAN))
    sep_grad.setColorAt(0.7, QColor(ACCENT_BLUE))
    sep_grad.setColorAt(1.0, QColor(0, 0, 0, 0))
    painter.setBrush(QBrush(sep_grad))
    painter.drawRect(40, 150, w - 80, 1)

    # ── Tech stack line ──
    tech_font = QFont("Segoe UI", 10)
    painter.setFont(tech_font)
    painter.setPen(QColor("#2D4A6E"))
    painter.drawText(40, 185, "YOLOv8  ·  SegFormer  ·  PyQt6  ·  OpenCV  ·  PyTorch")

    # ── Loading text ──
    painter.setPen(QColor("#1E2D4A"))
    painter.drawText(40, 210, "Initialising models, please wait…")

    # ── Bottom glow bar ──
    bot_grad = QLinearGradient(0, 0, w, 0)
    bot_grad.setColorAt(0.0, QColor(0, 0, 0, 0))
    bot_grad.setColorAt(0.4, QColor(ACCENT_BLUE))
    bot_grad.setColorAt(0.6, QColor(ACCENT_CYAN))
    bot_grad.setColorAt(1.0, QColor(0, 0, 0, 0))
    painter.setBrush(QBrush(bot_grad))
    painter.drawRect(0, h - 3, w, 3)

    painter.end()

    splash = QSplashScreen(pix, Qt.WindowType.WindowStaysOnTopHint)
    splash.setStyleSheet(
        "QSplashScreen { border: 1px solid #1E2D4A; border-radius: 6px; }"
    )
    return splash


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("MobilityX")
    app.setOrganizationName("MobilityX Lab")
    app.setStyleSheet(APP_STYLESHEET)

    # ── Splash ──
    splash = _make_splash()
    splash.show()
    app.processEvents()

    # ── Main window (models load lazily on engine start, so this is instant) ──
    window = MainWindow()

    # Show window after a brief splash delay
    def _launch():
        splash.finish(window)
        window.show()

    QTimer.singleShot(1800, _launch)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
