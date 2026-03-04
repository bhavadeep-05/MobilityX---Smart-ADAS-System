"""
gui/video_widget.py  –  OpenCV frame → Qt display widget
Converts BGR numpy arrays to QPixmap and renders them.
Includes a pause/resume button and snapshot button.
"""
import numpy as np
import cv2

from PyQt6.QtWidgets import (QWidget, QLabel, QVBoxLayout,
                              QHBoxLayout, QPushButton, QSizePolicy)
from PyQt6.QtCore   import Qt, QSize
from PyQt6.QtGui    import QImage, QPixmap

from gui.styles import ACCENT_CYAN, ACCENT_BLUE, BG_PANEL, BG_CARD, BG_CARD2, BG_BORDER, BG_DARK, TEXT_SECONDARY


class VideoWidget(QWidget):
    """
    Displays annotated OpenCV frames.
    Exposes:
        push_frame(np.ndarray)  – call from main window when frame_ready fires
        is_paused -> bool
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._paused      = False
        self._last_pixmap = None
        self._snap_count  = 0
        self._setup_ui()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── frame canvas ──
        self._canvas = QLabel()
        self._canvas.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._canvas.setSizePolicy(QSizePolicy.Policy.Expanding,
                                   QSizePolicy.Policy.Expanding)
        self._canvas.setStyleSheet(f"background-color: #000; border-radius: 10px;")
        self._canvas.setText("Loading models…")
        self._canvas.setStyleSheet(
            f"background: {BG_DARK}; color: {TEXT_SECONDARY}; "
            f"font-size: 16px; font-weight: 500; letter-spacing: 1px;"
            f"border-radius: 10px;"
        )
        root.addWidget(self._canvas, stretch=1)

        # ── control bar ──
        bar = QWidget()
        bar.setFixedHeight(46)
        bar.setStyleSheet(
            f"background:{BG_PANEL};"
            f"border-top:1px solid {BG_BORDER};"
            f"border-bottom-left-radius:10px;"
            f"border-bottom-right-radius:10px;"
        )
        bar_l = QHBoxLayout(bar)
        bar_l.setContentsMargins(12, 0, 12, 0)
        bar_l.setSpacing(8)

        self._pause_btn = QPushButton("⏸  Pause")
        self._pause_btn.setFixedWidth(120)
        self._pause_btn.clicked.connect(self._toggle_pause)

        self._snap_btn = QPushButton("📷  Snapshot")
        self._snap_btn.setFixedWidth(120)
        self._snap_btn.clicked.connect(self._take_snapshot)

        for btn in (self._pause_btn, self._snap_btn):
            btn.setStyleSheet(
                f"QPushButton{{background:{BG_CARD};color:{TEXT_SECONDARY};"
                f"border:1px solid {BG_BORDER};border-radius:7px;padding:6px 14px;"
                f"font-size:12px;font-weight:500;}}"
                f"QPushButton:hover{{border-color:{ACCENT_CYAN};color:{ACCENT_CYAN};"
                f"background:{BG_CARD2};}}"
                f"QPushButton:pressed{{background:{BG_DARK};}}"
            )

        bar_l.addStretch()
        bar_l.addWidget(self._pause_btn)
        bar_l.addWidget(self._snap_btn)
        bar_l.addStretch()

        root.addWidget(bar)

    # ── public API ───────────────────────────────────────────────────────────
    @property
    def is_paused(self) -> bool:
        return self._paused

    def push_frame(self, frame: np.ndarray):
        if self._paused:
            return
        h, w, ch = frame.shape
        qimg = QImage(frame.data, w, h, ch * w, QImage.Format.Format_BGR888)
        pix  = QPixmap.fromImage(qimg)
        pix  = pix.scaled(self._canvas.size(),
                          Qt.AspectRatioMode.KeepAspectRatio,
                          Qt.TransformationMode.SmoothTransformation)
        self._canvas.setPixmap(pix)
        self._last_pixmap = pix

    # ── slots ─────────────────────────────────────────────────────────────────
    def _toggle_pause(self):
        self._paused = not self._paused
        self._pause_btn.setText("▶  Resume" if self._paused else "⏸  Pause")
        if not self._paused and self._last_pixmap:
            self._canvas.setPixmap(self._last_pixmap)

    def _take_snapshot(self):
        if self._last_pixmap:
            self._snap_count += 1
            path = f"snapshot_{self._snap_count:03d}.png"
            self._last_pixmap.save(path)
