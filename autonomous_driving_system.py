import cv2
import torch
import numpy as np
import time
import pyttsx3
import queue
import threading
from ultralytics import YOLO
from transformers import SegformerImageProcessor, SegformerForSemanticSegmentation

# =========================================================
# DEVICE SETUP
# =========================================================
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print("Using device:", device)

# =========================================================
# YOLO OBJECT DETECTION
# =========================================================
detector = YOLO("yolov8s.pt")
detector.to(device)

PERSON_ID = 0
VEHICLE_IDS = [1, 2, 3, 5, 7]

# =========================================================
# SEGMENTATION MODEL
# =========================================================
processor = SegformerImageProcessor.from_pretrained(
    "nvidia/segformer-b0-finetuned-ade-512-512")
seg_model = SegformerForSemanticSegmentation.from_pretrained(
    "nvidia/segformer-b0-finetuned-ade-512-512").to(device)
seg_model.eval()

ROAD_CLASSES = [6, 7]
previous_seg = None

# =========================================================
# AUDIO SYSTEM
# =========================================================
engine = pyttsx3.init()
engine.setProperty("rate", 170)

speech_queue = queue.Queue()
alert_cooldowns = {}
ALERT_DELAY = 4
brake_announced = False
current_audio_message = "System Ready"

def speech_worker():
    global current_audio_message
    while True:
        text = speech_queue.get()
        if text is None:
            break
        current_audio_message = text
        engine.say(text)
        engine.runAndWait()
        speech_queue.task_done()

threading.Thread(target=speech_worker, daemon=True).start()

def speak(msg):
    now = time.time()
    if msg not in alert_cooldowns or now - alert_cooldowns[msg] > ALERT_DELAY:
        alert_cooldowns[msg] = now
        speech_queue.put(msg)

speech_queue.put("Advanced driver assistance system activated")

# =========================================================
# GLOBALS FOR TTC
# =========================================================
previous_distance = 0
previous_frame_distance = 0
previous_time = time.time()

# =========================================================
# CINEMATIC TEXT FUNCTION
# =========================================================
def draw_modern_text(frame, text, pos, size=0.6, color=(255,255,255)):
    x, y = pos
    cv2.putText(frame, text, (x+2, y+2),
                cv2.FONT_HERSHEY_SIMPLEX,
                size, (0,0,0), 3, cv2.LINE_AA)
    cv2.putText(frame, text, (x, y),
                cv2.FONT_HERSHEY_SIMPLEX,
                size, color, 1, cv2.LINE_AA)

# =========================================================
# ROAD SEGMENTATION (WITH BOUNDING BOX RESTORED)
# =========================================================
def segment_road(frame):
    global previous_seg
    h, w = frame.shape[:2]

    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    inputs = processor(images=rgb, return_tensors="pt").to(device)

    with torch.no_grad():
        outputs = seg_model(**inputs)

    logits = outputs.logits
    upsampled = torch.nn.functional.interpolate(
        logits, size=(h, w), mode="bilinear", align_corners=False
    )
    seg = upsampled.argmax(dim=1)[0].cpu().numpy()

    if previous_seg is not None:
        seg = (0.7 * previous_seg + 0.3 * seg).astype(np.uint8)
    previous_seg = seg

    road_mask = np.isin(seg, ROAD_CLASSES).astype(np.uint8) * 255
    contours, _ = cv2.findContours(road_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if len(contours) > 0:
        all_points = np.vstack(contours).squeeze()
        x_min, y_min = all_points.min(axis=0)
        x_max, y_max = all_points.max(axis=0)

        # Road bounding box restored
        cv2.rectangle(frame, (x_min, y_min), (x_max, y_max), (0,255,0), 2)

        overlay = frame.copy()
        for cnt in contours:
            if cv2.contourArea(cnt) > 500:
                cv2.drawContours(overlay, [cnt], -1, (0,255,0), -1)

        cv2.addWeighted(overlay, 0.08, frame, 0.92, 0, frame)

        draw_modern_text(frame, "DRIVABLE ROAD",
                         (x_min, y_min-10),
                         0.6, (0,255,0))

    return frame

# =========================================================
# UTILITIES
# =========================================================
def estimate_distance(box_height):
    return 5000 / max(box_height, 1)

def risk_score(distance, max_distance=30):
    if distance <= 0 or distance >= max_distance:
        return 0
    return round((max_distance - distance) / max_distance, 2)

def get_risk_color(distance):
    if distance < 8:
        return (0, 0, 255)
    elif distance < 15:
        return (0, 200, 255)
    else:
        return (0, 255, 0)

# =========================================================
# RIGHT SIDE AUDIO PANEL
# =========================================================
def draw_audio_panel(frame):
    h, w = frame.shape[:2]

    overlay = frame.copy()
    cv2.rectangle(overlay, (w-320, 100), (w-20, 200), (15,15,15), -1)
    cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)

    draw_modern_text(frame, "AUDIO STATUS",
                     (w-300, 130), 0.6, (0,255,255))

    draw_modern_text(frame, current_audio_message,
                     (w-300, 165), 0.55, (255,255,255))

    return frame

# =========================================================
# MODERN HUD PANEL
# =========================================================
def draw_modern_hud(frame, distance, ttc, risk):
    h, w = frame.shape[:2]

    overlay = frame.copy()
    cv2.rectangle(overlay, (20, 90), (300, h-90), (15,15,15), -1)
    cv2.addWeighted(overlay, 0.5, frame, 0.5, 0, frame)

    draw_modern_text(frame, "SYSTEM STATUS", (40, 120), 0.7)
    draw_modern_text(frame, f"Distance: {distance:.1f} m", (40, 170))
    draw_modern_text(frame, f"TTC: {ttc:.1f} s", (40, 200))
    draw_modern_text(frame, f"Risk Level: {risk:.2f}", (40, 230), 0.6, (0,255,255))

    bar_length = int(min(risk, 1) * 200)
    cv2.rectangle(frame, (40, 260),
                  (40 + bar_length, 275),
                  (0,0,255), -1)
    cv2.rectangle(frame, (40, 260),
                  (240, 275),
                  (255,255,255), 1)

    return frame

# =========================================================
# DETECTION
# =========================================================
def detect_objects(frame):
    global previous_distance, previous_frame_distance
    global previous_time, brake_announced

    results = detector(frame, conf=0.4, verbose=False)
    boxes = results[0].boxes

    closest_distance = 0

    if boxes is not None:
        for box in boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            cls = int(box.cls[0])

            box_h = y2 - y1
            dist = estimate_distance(box_h)

            if cls in VEHICLE_IDS:
                if closest_distance == 0 or dist < closest_distance:
                    closest_distance = dist

            color = get_risk_color(dist)
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

            draw_modern_text(frame,
                             f"{results[0].names[cls]}  {dist:.1f}m",
                             (x1, y1-10),
                             0.5, color)

    if closest_distance != 0:
        if previous_distance == 0:
            previous_distance = closest_distance
        else:
            previous_distance = 0.8 * previous_distance + 0.2 * closest_distance
    else:
        previous_distance = 0

    closest_distance = previous_distance

    current_time = time.time()
    delta_t = current_time - previous_time

    relative_speed = 0
    if previous_frame_distance != 0 and closest_distance != 0 and delta_t > 0:
        relative_speed = (previous_frame_distance - closest_distance) / delta_t

    ttc = 0
    if relative_speed > 0:
        ttc = closest_distance / relative_speed

    previous_frame_distance = closest_distance
    previous_time = current_time

    if ttc > 0 and ttc < 1.5:
        draw_modern_text(frame,
                         "EMERGENCY BRAKE",
                         (350, frame.shape[0]-60),
                         1.1, (0,0,255))
        if not brake_announced:
            speak("Emergency braking required")
            brake_announced = True
    else:
        brake_announced = False

    if ttc > 0 and ttc < 3:
        speak("Collision warning")

    if closest_distance > 0 and closest_distance < 20:
        speak("Vehicle ahead")

    risk = risk_score(closest_distance)
    frame = draw_modern_hud(frame, closest_distance, ttc, risk)
    frame = draw_audio_panel(frame)

    return frame

# =========================================================
# VIDEO INPUT
# =========================================================
video_path = input("Enter video path (Enter for webcam): ").strip()
cap = cv2.VideoCapture(0 if video_path=="" else video_path)

if not cap.isOpened():
    print("Error opening video.")
    exit()

# =========================================================
# MAIN LOOP
# =========================================================
while True:
    ret, frame = cap.read()
    if not ret:
        break

    frame = cv2.resize(frame, (960, 540))

    frame = segment_road(frame)
    frame = detect_objects(frame)

    frame[0:40,:,:] = 0
    frame[-40:,:,:] = 0

    cv2.imshow("Advanced ADAS System", frame)

    if cv2.waitKey(1) & 0xFF == 27:
        break

cap.release()
cv2.destroyAllWindows()
speech_queue.put(None)