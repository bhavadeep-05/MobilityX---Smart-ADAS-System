"""
gui/settings_dialog.py  –  ADAS settings modal
"""
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                              QPushButton, QSlider, QComboBox, QCheckBox,
                              QGroupBox, QDialogButtonBox, QSpinBox,
                              QDoubleSpinBox)
from PyQt6.QtCore import Qt

from adas_engine import EngineConfig
from gui.styles import APP_STYLESHEET, ACCENT_CYAN, TEXT_SECONDARY


class SettingsDialog(QDialog):
    """
    Modal settings editor.
    Call exec() and then read .config for the result.
    """

    def __init__(self, config: EngineConfig, parent=None):
        super().__init__(parent)
        self.setWindowTitle("⚙  ADAS Settings")
        self.setMinimumWidth(400)
        self.setStyleSheet(APP_STYLESHEET)
        self.config = config
        self._setup_ui()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(12)
        root.setContentsMargins(20, 20, 20, 20)

        # ── Model ──────────────────────────────────────────────────────────
        model_box = QGroupBox("Detection Model")
        ml = QVBoxLayout(model_box)

        model_row = QHBoxLayout()
        model_row.addWidget(QLabel("YOLOv8 variant:"))
        self._model_combo = QComboBox()
        self._model_combo.addItems(["yolov8n.pt", "yolov8s.pt", "yolov8m.pt"])
        self._model_combo.setCurrentText(self.config.model_path)
        model_row.addWidget(self._model_combo)
        ml.addLayout(model_row)

        conf_row = QHBoxLayout()
        conf_row.addWidget(QLabel("Confidence threshold:"))
        self._conf_slider = QSlider(Qt.Orientation.Horizontal)
        self._conf_slider.setRange(10, 95)
        self._conf_slider.setValue(int(self.config.confidence * 100))
        self._conf_slider.setTickInterval(5)
        self._conf_val_lbl = QLabel(f"{self.config.confidence:.2f}")
        self._conf_val_lbl.setFixedWidth(36)
        self._conf_slider.valueChanged.connect(
            lambda v: self._conf_val_lbl.setText(f"{v/100:.2f}")
        )
        conf_row.addWidget(self._conf_slider)
        conf_row.addWidget(self._conf_val_lbl)
        ml.addLayout(conf_row)

        root.addWidget(model_box)

        # ── TTC Thresholds ─────────────────────────────────────────────────
        ttc_box = QGroupBox("TTC Alert Thresholds")
        tl = QVBoxLayout(ttc_box)

        warn_row = QHBoxLayout()
        warn_row.addWidget(QLabel("Warning threshold (s):"))
        self._ttc_warn = QDoubleSpinBox()
        self._ttc_warn.setRange(1.0, 10.0)
        self._ttc_warn.setSingleStep(0.5)
        self._ttc_warn.setValue(self.config.ttc_warning_s)
        warn_row.addWidget(self._ttc_warn)
        tl.addLayout(warn_row)

        crit_row = QHBoxLayout()
        crit_row.addWidget(QLabel("Critical threshold (s):"))
        self._ttc_crit = QDoubleSpinBox()
        self._ttc_crit.setRange(0.5, 5.0)
        self._ttc_crit.setSingleStep(0.5)
        self._ttc_crit.setValue(self.config.ttc_critical_s)
        crit_row.addWidget(self._ttc_crit)
        tl.addLayout(crit_row)

        root.addWidget(ttc_box)

        # ── Feature toggles ────────────────────────────────────────────────
        feat_box = QGroupBox("Features")
        fl = QVBoxLayout(feat_box)

        self._seg_chk   = QCheckBox("Road Segmentation overlay")
        self._lane_chk  = QCheckBox("Lane Detection overlay")
        self._audio_chk = QCheckBox("Audio Alerts")

        self._seg_chk.setChecked(self.config.enable_segmentation)
        self._lane_chk.setChecked(self.config.enable_lanes)
        self._audio_chk.setChecked(self.config.enable_audio)

        for chk in (self._seg_chk, self._lane_chk, self._audio_chk):
            fl.addWidget(chk)

        root.addWidget(feat_box)

        # ── Buttons ────────────────────────────────────────────────────────
        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(self._apply)
        btns.rejected.connect(self.reject)
        root.addWidget(btns)

    def _apply(self):
        self.config.model_path          = self._model_combo.currentText()
        self.config.confidence          = self._conf_slider.value() / 100.0
        self.config.ttc_warning_s       = self._ttc_warn.value()
        self.config.ttc_critical_s      = self._ttc_crit.value()
        self.config.enable_segmentation = self._seg_chk.isChecked()
        self.config.enable_lanes        = self._lane_chk.isChecked()
        self.config.enable_audio        = self._audio_chk.isChecked()
        self.accept()
