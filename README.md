# 🚗 MobilityX — AI Driver Assistance System

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/YOLOv8-Ultralytics-purple?logo=yolo" />
  <img src="https://img.shields.io/badge/PyQt6-GUI-green?logo=qt&logoColor=white" />
  <img src="https://img.shields.io/badge/PyTorch-AI-red?logo=pytorch&logoColor=white" />
  <img src="https://img.shields.io/badge/OpenCV-Vision-blue?logo=opencv&logoColor=white" />
</p>

> **MobilityX** is a real-time Advanced Driver Assistance System (ADAS) built with Python. It processes video feeds using state-of-the-art AI models to detect vehicles and pedestrians, segment drivable road area, identify lane markings, estimate distances and time-to-collision (TTC), and issue live audio alerts — all inside a premium dark-themed PyQt6 desktop application.

---

##  Features

| Feature | Description |
|---|---|
| 🚙 **Object Detection** | YOLOv8-powered detection of vehicles, pedestrians, motorcycles, and more |
| 🛣️ **Road Segmentation** | SegFormer (NVIDIA) highlights the drivable road area with a translucent overlay |
| 🏁 **Lane Detection** | Hough-transform lane fitting with a filled safe-zone polygon |
| 📏 **Distance Estimation** | Real-time closest-vehicle distance estimated from bounding-box height |
| ⏱️ **Time-to-Collision (TTC)** | Relative-speed TTC computation with smoothed frame-over-frame tracking |
| ⚠️ **Blind Spot Detection** | Lateral-zone alerting for vehicles in the left/right blind spots |
| 🔊 **Voice Alerts** | Throttled text-to-speech warnings via `pyttsx3` (non-blocking background thread) |
| 📊 **Live Dashboard** | Live telemetry sidebar: speed, distance, TTC, risk bar, FPS, session stats |
| 🎨 **Premium Dark UI** | Deep-navy PyQt6 interface with HUD overlays, glow accents, and cinematic bars |
| ⚙️ **Settings Dialog** | Configurable confidence threshold, YOLOv8 model size, and feature toggles |


##  Project Structure

```
MobilityX/
│
├── app.py                  # Application entry point & branded splash screen
├── adas_engine.py          # Core QThread ADAS engine (AI processing pipeline)
├── requirements.txt        # Python dependencies
│
├── gui/
│   ├── main_window.py      # Main application window & layout
│   ├── dashboard_widget.py # Live metrics side panel
│   ├── video_widget.py     # OpenCV → PyQt6 video renderer
│   ├── alert_widget.py     # Real-time alert banner widget
│   ├── settings_dialog.py  # Configuration dialog
│   └── styles.py           # Global stylesheet & design tokens
│
├── yolov8n.pt              # YOLOv8 Nano weights (fast)
├── yolov8s.pt              # YOLOv8 Small weights (default)
└── yolov8m.pt              # YOLOv8 Medium weights (accurate)
```

---

##  Getting Started

### Prerequisites

- Python **3.10+**
- A CUDA-capable GPU is recommended (CPU inference is supported but slower)

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/MobilityX.git
cd MobilityX
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

> **Note:** `transformers` will automatically download the SegFormer model (`nvidia/segformer-b0-finetuned-ade-512-512`) on first run. This requires an internet connection (~60 MB download).

### 3. Run the Application

```bash
python app.py
```

---

## ⚙️ Configuration

Click the **⚙ Settings** button inside the application to configure:

| Setting | Options | Default |
|---|---|---|
| YOLOv8 Model | `yolov8n.pt` · `yolov8s.pt` · `yolov8m.pt` | `yolov8s.pt` |
| Confidence Threshold | 0.1 – 0.9 | `0.40` |
| Road Segmentation | Enable / Disable | Enabled |
| Lane Detection | Enable / Disable | Enabled |
| Audio Alerts | Enable / Disable | Enabled |
| TTC Warning Threshold | seconds | `3.0 s` |
| TTC Critical Threshold | seconds | `1.5 s` |

---

##  AI Pipeline

```
Video Frame
    │
    ├──▶ SegFormer  →  Road segmentation overlay
    │
    ├──▶ Hough Lines  →  Lane boundary detection
    │
    └──▶ YOLOv8
              │
              ├──▶ Distance estimation  →  TTC calculation
              │
              ├──▶ Centroid Tracker  →  Object ID assignment
              │
              ├──▶ Blind spot check  →  Lateral alerts
              │
              └──▶ Audio Manager  →  Voice warnings
```

---

##  Dependencies

| Package | Purpose |
|---|---|
| `torch` | Deep learning backend (CUDA support) |
| `ultralytics` | YOLOv8 object detection |
| `transformers` | SegFormer road segmentation |
| `opencv-python` | Video capture & frame processing |
| `PyQt6` | Desktop GUI framework |
| `pyttsx3` | Offline text-to-speech alerts |
| `numpy` | Numerical computations |

---

##  Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Commit your changes: `git commit -m "Add your feature"`
4. Push to the branch: `git push origin feature/your-feature`
5. Open a Pull Request

---

## 📄 License
This project is for educational and research purposes.

---

<p align="center">Built using Python · YOLOv8 · SegFormer · PyQt6 · OpenCV</p>
