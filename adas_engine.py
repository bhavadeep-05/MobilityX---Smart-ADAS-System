"""
adas_engine.py  –  Advanced ADAS Processing Engine (QThread-based)

Signals emitted to the GUI:
  frame_ready(np.ndarray)         – annotated BGR frame
  metrics_updated(dict)           – live telemetry dict
  alert_triggered(str, str)       – (level, message)  level: 'critical'|'warning'|'info'
"""

import time
import queue
import threading
import numpy as np
import cv2
import torch
import torch.nn.functional as F
import pyttsx3

from ultralytics import YOLO
from transformers import SegformerImageProcessor, SegformerForSemanticSegmentation
from PyQt6.QtCore import QThread, pyqtSignal


# ─────────────────────────────────────────────────────────────────────────────
#  CENTROID TRACKER  (lightweight, no extra deps)
# ─────────────────────────────────────────────────────────────────────────────
class CentroidTracker:
    def __init__(self, max_disappeared=10):
        self.next_id = 0
        self.objects = {}          # id → centroid
        self.disappeared = {}      # id → frame count
        self.max_disappeared = max_disappeared

    def register(self, centroid):
        self.objects[self.next_id] = centroid
        self.disappeared[self.next_id] = 0
        self.next_id += 1

    def deregister(self, oid):
        del self.objects[oid]
        del self.disappeared[oid]

    def update(self, centroids):
        if len(centroids) == 0:
            for oid in list(self.disappeared):
                self.disappeared[oid] += 1
                if self.disappeared[oid] > self.max_disappeared:
                    self.deregister(oid)
            return self.objects

        if len(self.objects) == 0:
            for c in centroids:
                self.register(c)
        else:
            ids = list(self.objects.keys())
            old_cs = list(self.objects.values())

            # distance matrix
            D = np.linalg.norm(np.array(old_cs)[:, None] - np.array(centroids)[None, :], axis=2)
            rows = D.min(axis=1).argsort()
            cols = D.argmin(axis=1)[rows]

            used_rows, used_cols = set(), set()
            for r, c in zip(rows, cols):
                if r in used_rows or c in used_cols:
                    continue
                oid = ids[r]
                self.objects[oid] = centroids[c]
                self.disappeared[oid] = 0
                used_rows.add(r)
                used_cols.add(c)

            for r in set(range(len(old_cs))) - used_rows:
                oid = ids[r]
                self.disappeared[oid] += 1
                if self.disappeared[oid] > self.max_disappeared:
                    self.deregister(oid)

            for c in set(range(len(centroids))) - used_cols:
                self.register(centroids[c])

        return self.objects


# ─────────────────────────────────────────────────────────────────────────────
#  AUDIO  (background thread)
# ─────────────────────────────────────────────────────────────────────────────
class AudioManager:
    def __init__(self):
        self._q = queue.Queue(maxsize=3)
        self._last_msgs: dict[str, float] = {}
        self._cooldown = 4.0   # seconds between same message
        self.current_message = "System Ready"   # ← displayed in audio panel
        t = threading.Thread(target=self._worker, daemon=True)
        t.start()

    def _worker(self):
        try:
            eng = pyttsx3.init()
            eng.setProperty("rate", 165)
            while True:
                text = self._q.get()
                if text is None:
                    break
                self.current_message = text
                eng.say(text)
                eng.runAndWait()
                self._q.task_done()
        except Exception:
            pass   # audio failure is non-fatal

    def speak(self, msg: str):
        now = time.time()
        last = self._last_msgs.get(msg, 0)
        if now - last < self._cooldown:
            return
        self._last_msgs[msg] = now
        if not self._q.full():
            self._q.put(msg)

    def stop(self):
        self._q.put(None)


# ─────────────────────────────────────────────────────────────────────────────
#  ENGINE CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────
class EngineConfig:
    def __init__(self):
        self.model_path         = "yolov8s.pt"
        self.confidence         = 0.40
        self.ttc_warning_s      = 3.0
        self.ttc_critical_s     = 1.5
        self.enable_segmentation = True
        self.enable_lanes        = True
        self.enable_audio        = True
        self.seg_alpha           = 0.14    # road overlay transparency


# ─────────────────────────────────────────────────────────────────────────────
#  DRAWING HELPERS
# ─────────────────────────────────────────────────────────────────────────────
VEHICLE_IDS   = {1, 2, 3, 5, 7}
PERSON_ID     = 0
ROAD_CLASSES  = {6, 7}

CLASS_COLORS = {
    "car":        (0, 200, 255),
    "truck":      (0, 120, 255),
    "bus":        (100, 80, 255),
    "motorcycle": (180, 80, 255),
    "bicycle":    (255, 180, 0),
    "person":     (255, 255, 255),
}
DEFAULT_COLOR = (200, 200, 200)


def _dist_color(dist: float):
    if dist < 8:
        return (0, 60, 255)
    if dist < 15:
        return (0, 210, 255)
    return (0, 230, 100)


def _estimate_distance(box_h: int) -> float:
    return 5000.0 / max(box_h, 1)


def _risk_score(dist: float, max_d: float = 30.0) -> float:
    if dist <= 0 or dist >= max_d:
        return 0.0
    return round((max_d - dist) / max_d, 2)


def _draw_rounded_rect(img, pt1, pt2, color, radius=8, thickness=2):
    x1, y1 = pt1
    x2, y2 = pt2
    cv2.rectangle(img, (x1+radius, y1), (x2-radius, y2), color, thickness)
    cv2.rectangle(img, (x1, y1+radius), (x2, y2-radius), color, thickness)
    cv2.ellipse(img, (x1+radius, y1+radius), (radius, radius), 180, 0, 90, color, thickness)
    cv2.ellipse(img, (x2-radius, y1+radius), (radius, radius), 270, 0, 90, color, thickness)
    cv2.ellipse(img, (x1+radius, y2-radius), (radius, radius),  90, 0, 90, color, thickness)
    cv2.ellipse(img, (x2-radius, y2-radius), (radius, radius),   0, 0, 90, color, thickness)


def _label_bg(img, text, pos, font, scale, color, text_color=(0, 0, 0), thickness=1):
    (tw, th), bl = cv2.getTextSize(text, font, scale, thickness)
    x, y = pos
    cv2.rectangle(img, (x-2, y-th-bl-2), (x+tw+2, y+2), color, -1)
    cv2.putText(img, text, (x, y-bl), font, scale, text_color, thickness, cv2.LINE_AA)


def _draw_modern_text(img, text, pos, size=0.6, color=(255, 255, 255), thickness=1):
    """Drop-shadow text: dark outline behind coloured foreground."""
    x, y = pos
    # shadow
    cv2.putText(img, text, (x + 2, y + 2),
                cv2.FONT_HERSHEY_SIMPLEX, size, (0, 0, 0), thickness + 2, cv2.LINE_AA)
    # foreground
    cv2.putText(img, text, (x, y),
                cv2.FONT_HERSHEY_SIMPLEX, size, color, thickness, cv2.LINE_AA)


# ─────────────────────────────────────────────────────────────────────────────
#  MAIN ENGINE  (QThread)
# ─────────────────────────────────────────────────────────────────────────────
class AdasEngine(QThread):
    frame_ready      = pyqtSignal(object)          # annotated np.ndarray
    metrics_updated  = pyqtSignal(dict)
    alert_triggered  = pyqtSignal(str, str)        # level, message

    def __init__(self, source, config: EngineConfig, parent=None):
        super().__init__(parent)
        self.source = source
        self.config = config
        self._running = False

        # ── models (loaded in run() on worker thread) ──
        self._detector  = None
        self._seg_proc  = None
        self._seg_model = None
        self.device     = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        # ── state ──
        self._prev_seg        = None
        self._prev_dist       = 0.0
        self._prev_frame_dist = 0.0
        self._prev_time       = time.time()
        self._tracker         = CentroidTracker()
        self._audio           = AudioManager()

        # session stats
        self._session_start  = time.time()
        self._total_alerts   = 0
        self._max_risk       = 0.0
        self._frame_count    = 0

    # ── lifecycle ────────────────────────────────────────────────────────────
    def stop(self):
        self._running = False
        self._audio.stop()
        self.wait(3000)

    def run(self):
        self._running = True
        self._load_models()

        cap = cv2.VideoCapture(self.source)
        if not cap.isOpened():
            self.alert_triggered.emit("critical", "Cannot open video source")
            return

        prev_fp_time = time.time()

        while self._running:
            ret, frame = cap.read()
            if not ret:
                break

            frame = cv2.resize(frame, (960, 540))
            self._frame_count += 1

            # ── AI processing ──
            if self.config.enable_segmentation:
                frame = self._segment_road(frame)

            if self.config.enable_lanes:
                frame = self._detect_lanes(frame)

            metrics = self._detect_objects(frame)

            # ── FPS ──
            now = time.time()
            elapsed = now - prev_fp_time
            fps = 1.0 / elapsed if elapsed > 0 else 0.0
            prev_fp_time = now

            metrics["fps"]           = round(fps, 1)
            metrics["session_time"]  = round(now - self._session_start)
            metrics["total_alerts"]  = self._total_alerts
            metrics["max_risk"]      = round(self._max_risk, 2)
            metrics["device"]        = str(self.device).upper()
            metrics["frame_count"]   = self._frame_count

            # ── On-frame HUD panels ──
            self._draw_modern_hud(frame, metrics)
            self._draw_audio_panel(frame)
            self._draw_fps_badge(frame, fps)

            # ── Cinematic black bars (top + bottom) ──
            frame[0:40, :, :]  = 0
            frame[-40:, :, :] = 0

            self.frame_ready.emit(frame.copy())
            self.metrics_updated.emit(dict(metrics))

        cap.release()

    # ── model loading ────────────────────────────────────────────────────────
    def _load_models(self):
        self._detector = YOLO(self.config.model_path)
        self._detector.to(self.device)

        if self.config.enable_segmentation:
            self._seg_proc  = SegformerImageProcessor.from_pretrained(
                "nvidia/segformer-b0-finetuned-ade-512-512")
            self._seg_model = SegformerForSemanticSegmentation.from_pretrained(
                "nvidia/segformer-b0-finetuned-ade-512-512").to(self.device)
            self._seg_model.eval()

    # ── road segmentation ────────────────────────────────────────────────────
    def _segment_road(self, frame: np.ndarray) -> np.ndarray:
        h, w = frame.shape[:2]
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        inputs = self._seg_proc(images=rgb, return_tensors="pt").to(self.device)

        with torch.no_grad():
            out = self._seg_model(**inputs)

        logits = out.logits
        up = F.interpolate(logits, size=(h, w), mode="bilinear", align_corners=False)
        seg = up.argmax(dim=1)[0].cpu().numpy()

        if self._prev_seg is not None:
            seg = (0.7 * self._prev_seg + 0.3 * seg).astype(np.uint8)
        self._prev_seg = seg

        road_mask = np.isin(seg, list(ROAD_CLASSES)).astype(np.uint8) * 255
        contours, _ = cv2.findContours(road_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if contours:
            all_pts = np.vstack([c for c in contours if c.shape[0] > 10]).squeeze()
            if all_pts.ndim == 2:
                x0, y0 = all_pts.min(axis=0)
                x1, y1 = all_pts.max(axis=0)

                overlay = frame.copy()
                for cnt in contours:
                    if cv2.contourArea(cnt) > 500:
                        cv2.drawContours(overlay, [cnt], -1, (0, 230, 100), -1)
                cv2.addWeighted(overlay, self.config.seg_alpha, frame, 1 - self.config.seg_alpha, 0, frame)

                cv2.rectangle(frame, (x0, y0), (x1, y1), (0, 230, 100), 1)
                _label_bg(frame, "DRIVABLE ROAD", (x0 + 4, y0 + 18),
                          cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 230, 100), (0, 0, 0))

        return frame

    # ── lane detection ───────────────────────────────────────────────────────
    def _detect_lanes(self, frame: np.ndarray) -> np.ndarray:
        h, w = frame.shape[:2]
        roi_y = int(h * 0.55)

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (7, 7), 0)
        edges = cv2.Canny(blur, 50, 150)

        # ROI trapezoid mask
        mask = np.zeros_like(edges)
        pts = np.array([[
            (int(w * 0.05), h),
            (int(w * 0.38), roi_y),
            (int(w * 0.62), roi_y),
            (int(w * 0.95), h),
        ]], dtype=np.int32)
        cv2.fillPoly(mask, pts, 255)
        masked = cv2.bitwise_and(edges, mask)

        lines = cv2.HoughLinesP(masked, 1, np.pi / 180,
                                 threshold=40, minLineLength=40, maxLineGap=60)

        left_pts, right_pts = [], []
        cx = w // 2

        if lines is not None:
            for line in lines:
                x1, y1, x2, y2 = line[0]
                if x2 == x1:
                    continue
                slope = (y2 - y1) / (x2 - x1)
                if abs(slope) < 0.4:
                    continue
                if slope < 0 and x1 < cx and x2 < cx:
                    left_pts.extend([(x1, y1), (x2, y2)])
                elif slope > 0 and x1 > cx and x2 > cx:
                    right_pts.extend([(x1, y1), (x2, y2)])

        lane_overlay = frame.copy()

        def fit_lane(pts, color):
            if len(pts) < 2:
                return
            xs = [p[0] for p in pts]
            ys = [p[1] for p in pts]
            try:
                poly = np.polyfit(ys, xs, 1)
                y_bot, y_top = h, roi_y
                x_bot = int(np.polyval(poly, y_bot))
                x_top = int(np.polyval(poly, y_top))
                cv2.line(lane_overlay, (x_bot, y_bot), (x_top, y_top), color, 4, cv2.LINE_AA)
            except Exception:
                pass

        fit_lane(left_pts,  (0, 180, 255))   # blue-ish left lane
        fit_lane(right_pts, (0, 180, 255))   # blue-ish right lane

        cv2.addWeighted(lane_overlay, 0.65, frame, 0.35, 0, frame)

        # Fill lane polygon if both sides detected
        if left_pts and right_pts:
            try:
                def lane_point(pts, y_val):
                    xs = [p[0] for p in pts]
                    ys = [p[1] for p in pts]
                    poly = np.polyfit(ys, xs, 1)
                    return int(np.polyval(poly, y_val))

                y_b, y_t = h, roi_y
                poly_pts = np.array([
                    [lane_point(left_pts, y_b),  y_b],
                    [lane_point(left_pts, y_t),  y_t],
                    [lane_point(right_pts, y_t), y_t],
                    [lane_point(right_pts, y_b), y_b],
                ], dtype=np.int32)
                fill = frame.copy()
                cv2.fillPoly(fill, [poly_pts], (0, 150, 255))
                cv2.addWeighted(fill, 0.18, frame, 0.82, 0, frame)
            except Exception:
                pass

        return frame

    # ── object detection ─────────────────────────────────────────────────────
    def _detect_objects(self, frame: np.ndarray) -> dict:
        cfg = self.config
        results = self._detector(
            frame, conf=cfg.confidence, verbose=False,
            half=(self.device.type == "cuda"),
        )
        boxes   = results[0].boxes
        names   = results[0].names
        h, w    = frame.shape[:2]

        closest_dist  = 0.0
        centroids     = []
        class_counts  = {}
        blind_left    = False
        blind_right   = False

        if boxes is not None:
            for box in boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                cls   = int(box.cls[0])
                conf  = float(box.conf[0])
                bname = names.get(cls, str(cls))
                bh    = y2 - y1
                dist  = _estimate_distance(bh)

                cx_b = (x1 + x2) // 2
                cy_b = (y1 + y2) // 2
                centroids.append((cx_b, cy_b))

                class_counts[bname] = class_counts.get(bname, 0) + 1

                if cls in VEHICLE_IDS:
                    if closest_dist == 0 or dist < closest_dist:
                        closest_dist = dist

                    # Blind spot: lateral zones
                    if cx_b < w * 0.2 and y2 > h * 0.4:
                        blind_left = True
                    if cx_b > w * 0.8 and y2 > h * 0.4:
                        blind_right = True

                color = (CLASS_COLORS.get(bname, DEFAULT_COLOR)
                         if cls not in VEHICLE_IDS
                         else _dist_color(dist))

                # Draw box
                _draw_rounded_rect(frame, (x1, y1), (x2, y2), color, radius=6, thickness=2)

                # Label
                label = f"{bname}  {dist:.1f}m  {int(conf*100)}%"
                _label_bg(frame, label, (x1+4, y1+18),
                          cv2.FONT_HERSHEY_SIMPLEX, 0.50, color, (0, 0, 0))

        # ── tracking IDs ──
        tracked = self._tracker.update(centroids)
        for tid, (cx, cy) in tracked.items():
            cv2.circle(frame, (cx, cy), 4, (255, 255, 0), -1)
            cv2.putText(frame, f"#{tid}", (cx+6, cy-4),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.38, (255, 255, 0), 1, cv2.LINE_AA)

        # ── distance smoothing ──
        if closest_dist != 0:
            self._prev_dist = (closest_dist if self._prev_dist == 0
                               else 0.8 * self._prev_dist + 0.2 * closest_dist)
        else:
            self._prev_dist = 0.0
        closest_dist = self._prev_dist

        # ── TTC ──
        now     = time.time()
        delta_t = max(now - self._prev_time, 1e-6)
        rel_spd = 0.0
        if self._prev_frame_dist != 0 and closest_dist != 0:
            rel_spd = (self._prev_frame_dist - closest_dist) / delta_t
        ttc = (closest_dist / rel_spd) if rel_spd > 0 else 0.0
        self._prev_frame_dist = closest_dist
        self._prev_time       = now

        # ── alerts ──
        alert_level = ""
        if ttc > 0:
            if ttc < cfg.ttc_critical_s:
                alert_level = "critical"
                self._fire_alert("critical", "EMERGENCY BRAKE",
                                 "Emergency braking required", frame, h, w)
            elif ttc < cfg.ttc_warning_s:
                alert_level = "warning"
                self._fire_alert("warning", "COLLISION WARNING",
                                 "Collision warning", frame, h, w)

        if closest_dist > 0 and closest_dist < 20:
            if self.config.enable_audio:
                self._audio.speak("Vehicle ahead")

        if blind_left:
            self._fire_alert("warning", "◀ BLIND SPOT LEFT",
                             "Vehicle on your left", frame, h, w, overlay_only=True)
        if blind_right:
            self._fire_alert("warning", "BLIND SPOT RIGHT ▶",
                             "Vehicle on your right", frame, h, w, overlay_only=True)

        # ── risk ──
        risk = _risk_score(closest_dist)
        self._max_risk = max(self._max_risk, risk)

        # ── speed estimate (~60 km/h constant + approach delta) ──
        speed_est = max(0.0, 60.0 + rel_spd * 3.6)

        return {
            "distance":     round(closest_dist, 1),
            "ttc":          round(ttc, 2),
            "risk":         risk,
            "speed":        round(speed_est, 1),
            "objects":      sum(class_counts.values()),
            "class_counts": class_counts,
            "alert_level":  alert_level,
        }

    def _fire_alert(self, level: str, overlay_text: str, speech: str,
                    frame, h, w, overlay_only=False):
        if not overlay_only:
            self.alert_triggered.emit(level, overlay_text)
            self._total_alerts += 1
            if self.config.enable_audio:
                self._audio.speak(speech)

        # overlay text — use drop-shadow modern style
        color = (0, 60, 255) if level == "critical" else (0, 200, 255)
        scale = 1.1 if level == "critical" else 0.85
        thick = 2
        font  = cv2.FONT_HERSHEY_DUPLEX
        (tw, th), _ = cv2.getTextSize(overlay_text, font, scale, thick)
        tx = (w - tw) // 2
        ty = h - 70 if level == "critical" else h - 40
        _draw_modern_text(frame, overlay_text, (tx, ty), scale, color, thick)

    # ── Modern HUD panel (left side) ─────────────────────────────────────────
    def _draw_modern_hud(self, frame: np.ndarray, metrics: dict):
        h, w = frame.shape[:2]
        dist  = metrics.get("distance", 0.0)
        ttc   = metrics.get("ttc",      0.0)
        risk  = metrics.get("risk",     0.0)

        # semi-transparent background panel
        overlay = frame.copy()
        cv2.rectangle(overlay, (20, 50), (300, h - 50), (15, 15, 15), -1)
        cv2.addWeighted(overlay, 0.50, frame, 0.50, 0, frame)

        _draw_modern_text(frame, "SYSTEM STATUS", (40, 85),  0.65, (255, 255, 255), 1)
        _draw_modern_text(frame, f"Distance : {dist:.1f} m", (40, 130), 0.58, (200, 200, 200), 1)
        _draw_modern_text(frame, f"TTC      : {ttc:.1f} s",  (40, 160), 0.58, (200, 200, 200), 1)
        _draw_modern_text(frame, f"Risk     : {risk:.2f}",   (40, 190), 0.58, (0, 229, 255), 1)

        # risk progress bar
        bar_max   = 200
        bar_fill  = int(min(max(risk, 0.0), 1.0) * bar_max)
        bar_color = (0, 60, 255) if risk > 0.7 else (0, 180, 255) if risk > 0.4 else (0, 200, 80)
        cv2.rectangle(frame, (40, 210), (40 + bar_max, 224), (60, 60, 60), -1)   # track
        if bar_fill > 0:
            cv2.rectangle(frame, (40, 210), (40 + bar_fill, 224), bar_color, -1)  # fill
        cv2.rectangle(frame, (40, 210), (40 + bar_max, 224), (120, 120, 120), 1) # border

    # ── Audio status panel (right side) ──────────────────────────────────────
    def _draw_audio_panel(self, frame: np.ndarray):
        h, w = frame.shape[:2]
        msg = self._audio.current_message

        overlay = frame.copy()
        cv2.rectangle(overlay, (w - 320, 50), (w - 10, 130), (15, 15, 15), -1)
        cv2.addWeighted(overlay, 0.60, frame, 0.40, 0, frame)

        _draw_modern_text(frame, "AUDIO STATUS", (w - 305, 78),  0.55, (0, 229, 255), 1)
        # truncate message if too long
        short = msg if len(msg) <= 28 else msg[:25] + "..."
        _draw_modern_text(frame, short.upper(),  (w - 305, 112), 0.50, (255, 255, 255), 1)

    # ── FPS badge ────────────────────────────────────────────────────────────
    def _draw_fps_badge(self, frame, fps: float):
        text = f"FPS  {fps:.0f}"
        cv2.rectangle(frame, (10, 8), (110, 36), (20, 20, 20), -1)
        cv2.putText(frame, text, (16, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 229, 255), 2, cv2.LINE_AA)
