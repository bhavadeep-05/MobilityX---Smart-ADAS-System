"""
gui/main_window.py  –  MobilityX AI Driver Assistance
Layout:
  ┌──────────────────────────────┬──────────────────────────┐
  │                              │  DashboardWidget         │
  │       VideoWidget            │  (metrics + classes)     │
  │                              ├──────────────────────────┤
  │                              │  AlertWidget             │
  └──────────────────────────────┴──────────────────────────┘
  │                    StatusBar                            │
"""
import os
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QSplitter, QFileDialog, QMessageBox, QLabel, QStatusBar
)
from PyQt6.QtCore  import Qt, QTimer, pyqtSlot
from PyQt6.QtGui   import QAction, QIcon, QColor

from adas_engine          import AdasEngine, EngineConfig
from gui.video_widget     import VideoWidget
from gui.dashboard_widget import DashboardWidget
from gui.alert_widget     import AlertWidget
from gui.settings_dialog  import SettingsDialog
from gui.styles           import (APP_STYLESHEET, BG_PANEL, BG_DARK, BG_CARD, BG_CARD2,
                                   BG_BORDER, ACCENT_CYAN, ACCENT_BLUE, TEXT_SECONDARY,
                                   ACCENT_RED, ACCENT_AMBER, ACCENT_GREEN)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🚗 MobilityX  ·  AI Driver Assistance")
        self.resize(1480, 860)
        self.setMinimumSize(1060, 660)
        self.setStyleSheet(APP_STYLESHEET)

        self._config = EngineConfig()
        self._engine: AdasEngine | None = None
        self._session_time = 0

        self._build_ui()
        self._build_menu()
        self._build_statusbar()

        # clock ticker for status bar
        self._clock = QTimer(self)
        self._clock.timeout.connect(self._tick_clock)
        self._clock.start(1000)

    # ── UI construction ───────────────────────────────────────────────────────
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        # ── left: video ──
        self._video_widget = VideoWidget()

        # ── right: dashboard + alert ──
        right = QWidget()
        right.setFixedWidth(340)
        right.setStyleSheet(
            f"background:{BG_PANEL};border-radius:12px;"
            f"border:1px solid {BG_BORDER};"
        )
        right_lay = QVBoxLayout(right)
        right_lay.setContentsMargins(0, 0, 0, 0)
        right_lay.setSpacing(0)

        self._dashboard = DashboardWidget()
        self._alert_log = AlertWidget()

        # horizontal divider between dashboard and alert
        right_lay.addWidget(self._dashboard, stretch=3)

        div = QWidget()
        div.setFixedHeight(1)
        div.setStyleSheet(f"background:{BG_BORDER};")
        right_lay.addWidget(div)

        right_lay.addWidget(self._alert_log, stretch=4)

        # ── splitter so user can resize left/right ──
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setStyleSheet(
            f"QSplitter::handle {{ background: {BG_BORDER}; width: 3px; }}"
            f"QSplitter::handle:hover {{ background: {ACCENT_CYAN}; }}"
        )
        splitter.addWidget(self._video_widget)
        splitter.addWidget(right)
        splitter.setSizes([1120, 340])
        splitter.setCollapsible(0, False)
        splitter.setCollapsible(1, False)

        root.addWidget(splitter)

    def _build_menu(self):
        mb = self.menuBar()

        # ── File ──
        file_menu = mb.addMenu("&File")

        act_open = QAction("📂  Open Video…", self)
        act_open.setShortcut("Ctrl+O")
        act_open.triggered.connect(self._open_video)
        file_menu.addAction(act_open)

        act_webcam = QAction("📷  Use Webcam", self)
        act_webcam.setShortcut("Ctrl+W")
        act_webcam.triggered.connect(self._open_webcam)
        file_menu.addAction(act_webcam)

        file_menu.addSeparator()

        act_stop = QAction("⏹  Stop", self)
        act_stop.setShortcut("Ctrl+S")
        act_stop.triggered.connect(self._stop_engine)
        file_menu.addAction(act_stop)

        file_menu.addSeparator()

        act_quit = QAction("✕  Quit", self)
        act_quit.setShortcut("Ctrl+Q")
        act_quit.triggered.connect(self.close)
        file_menu.addAction(act_quit)

        # ── Settings ──
        set_menu = mb.addMenu("&Settings")
        act_cfg = QAction("⚙  Configure…", self)
        act_cfg.setShortcut("Ctrl+,")
        act_cfg.triggered.connect(self._open_settings)
        set_menu.addAction(act_cfg)

        # ── Help ──
        help_menu = mb.addMenu("&Help")
        act_about = QAction("ℹ  About", self)
        act_about.triggered.connect(self._show_about)
        help_menu.addAction(act_about)

    def _build_statusbar(self):
        sb = QStatusBar()
        self.setStatusBar(sb)
        sb.setStyleSheet(
            f"QStatusBar{{background:{BG_PANEL};color:{TEXT_SECONDARY};"
            f"font-size:11px;border-top:1px solid {BG_BORDER};"
            f"padding: 0 4px;}}"
            f"QStatusBar::item{{border:none;}}"
        )

        self._lbl_source   = QLabel("No source")
        self._lbl_device   = QLabel("—")
        self._lbl_session  = QLabel("Session: 0s")
        self._lbl_alerts   = QLabel("Alerts: 0")
        self._lbl_frames   = QLabel("Frames: 0")

        for lbl in (self._lbl_source, self._lbl_device,
                    self._lbl_session, self._lbl_alerts, self._lbl_frames):
            lbl.setStyleSheet(
                f"color:{TEXT_SECONDARY};padding:0 12px;"
                f"border-right:1px solid {BG_BORDER};"
            )
            sb.addPermanentWidget(lbl)

    # ── engine management ─────────────────────────────────────────────────────
    def _start_engine(self, source):
        self._stop_engine()

        self._engine = AdasEngine(source, self._config, parent=self)
        self._engine.frame_ready.connect(self._on_frame)
        self._engine.metrics_updated.connect(self._on_metrics)
        self._engine.alert_triggered.connect(self._on_alert)
        self._engine.start()

        src_txt = "Webcam" if source == 0 else os.path.basename(str(source))
        self._lbl_source.setText(f"▶ {src_txt}")
        self._alert_log.add_alert("info", f"Started: {src_txt}")

    def _stop_engine(self):
        if self._engine and self._engine.isRunning():
            self._engine.stop()
        self._engine = None
        self._lbl_source.setText("Stopped")

    # ── slots ─────────────────────────────────────────────────────────────────
    @pyqtSlot(object)
    def _on_frame(self, frame):
        self._video_widget.push_frame(frame)

    @pyqtSlot(dict)
    def _on_metrics(self, m: dict):
        self._dashboard.update_metrics(m)
        self._lbl_device.setText(m.get("device", "—"))
        self._lbl_session.setText(f"Session: {m.get('session_time', 0)}s")
        self._lbl_alerts.setText(f"Alerts: {m.get('total_alerts', 0)}")
        self._lbl_frames.setText(f"Frames: {m.get('frame_count', 0)}")

    @pyqtSlot(str, str)
    def _on_alert(self, level: str, message: str):
        self._alert_log.add_alert(level, message)

        # Flash status bar colour on critical alert
        if level == "critical":
            style = (f"QStatusBar{{background:#1a0010;color:{ACCENT_RED};"
                     f"font-size:11px;font-weight:700;"
                     f"border-top:2px solid {ACCENT_RED};}}"
                     f"QStatusBar::item{{border:none;}}")
            self.statusBar().setStyleSheet(style)
            QTimer.singleShot(1500, self._reset_statusbar_style)

    def _reset_statusbar_style(self):
        self.statusBar().setStyleSheet(
            f"QStatusBar{{background:{BG_PANEL};color:{TEXT_SECONDARY};"
            f"font-size:11px;border-top:1px solid {BG_BORDER};padding:0 4px;}}"
            f"QStatusBar::item{{border:none;}}"
        )

    def _tick_clock(self):
        pass   # session time is updated via metrics signal

    # ── menu actions ──────────────────────────────────────────────────────────
    def _open_video(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Video File", "",
            "Video Files (*.mp4 *.avi *.mov *.mkv *.wmv);;All Files (*)"
        )
        if path:
            self._start_engine(path)

    def _open_webcam(self):
        self._start_engine(0)

    def _open_settings(self):
        dlg = SettingsDialog(self._config, parent=self)
        if dlg.exec():
            # Restart engine with new config if currently running
            if self._engine and self._engine.isRunning():
                src = self._engine.source
                self._alert_log.add_alert("info", "Settings updated — restarting engine…")
                self._start_engine(src)

    def _show_about(self):
        QMessageBox.about(
            self,
            "About MobilityX",
            f"<h2 style='color:{ACCENT_CYAN};font-weight:800;'>🚗 MobilityX</h2>"
            f"<p style='color:{TEXT_SECONDARY};font-size:12px;'>AI Driver Assistance System</p>"
            "<p>Real-time perception powered by:</p>"
            "<ul>"
            "<li><b>YOLOv8</b> — Object Detection &amp; Distance Estimation</li>"
            "<li><b>SegFormer</b> — Road Segmentation</li>"
            "<li><b>Hough Transform</b> — Lane Detection</li>"
            "<li><b>Centroid Tracker</b> — Object Tracking</li>"
            "<li><b>TTC Engine</b> — Time-to-Collision Analysis</li>"
            "</ul>"
            "<p style='color:#5C7FAA;font-size:11px;'>Built with PyQt6 · OpenCV · PyTorch · Hugging Face Transformers</p>"
        )

    # ── close event ───────────────────────────────────────────────────────────
    def closeEvent(self, event):
        self._stop_engine()
        event.accept()
