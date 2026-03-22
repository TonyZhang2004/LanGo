import math
import os
import time
from pathlib import Path

import cv2
import mediapipe as mp
from ultralytics import YOLO

from hardware.detection_client import get_selected_language, submit_detection


mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils

hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=1,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5,
)

model = YOLO("yolov8s-oiv7.pt")

ignore_classes = ["Building", "Office building", "Clothing"]
label_map = {
    "Human hand": "Hand",
    "Human face": "Face",
    "Footwear": "Shoe",
    "Desk": "Table",
    "Tablet computer": "Tablet",
}

SERVER_BASE = os.environ.get("LANGO_SERVER_BASE", "http://127.0.0.1:8000")
DEFAULT_LANGUAGE_KEY = os.environ.get("LANGO_LANGUAGE_KEY", "spanish")
DETECTION_COOLDOWN_SECONDS = float(os.environ.get("LANGO_DETECTION_COOLDOWN_SECONDS", "5"))
LANGUAGE_REFRESH_SECONDS = float(os.environ.get("LANGO_LANGUAGE_REFRESH_SECONDS", "2"))
CAPTURE_DIR = Path("frontend/assets/captures")
SCREENSHOT_DIR = Path("images")
CAPTURE_DIR.mkdir(parents=True, exist_ok=True)
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

cap = cv2.VideoCapture(0)

touched = 0
touch_start = [0, 0]
touch_end = [0, 0]
pinch_threshold = 40

current_language_key = DEFAULT_LANGUAGE_KEY
last_language_refresh_at = 0.0
last_submitted_at = {}


def refresh_selected_language(now):
    global current_language_key, last_language_refresh_at
    if now - last_language_refresh_at < LANGUAGE_REFRESH_SECONDS:
        return current_language_key

    last_language_refresh_at = now
    try:
        status, payload = get_selected_language(server_base=SERVER_BASE)
        selected = payload.get("selectedLanguage", {}).get("key")
        if selected:
            if selected != current_language_key:
                print(f"Switched detector language from {current_language_key} to {selected} (HTTP {status}).")
            current_language_key = selected
    except Exception as exc:
        print(f"Could not refresh selected language; keeping {current_language_key}: {exc}")
    return current_language_key


def save_detection_crop(frame, x1, y1, x2, y2, clean_label, now):
    crop = frame[y1:y2, x1:x2]
    if crop.size == 0:
        return None

    filename = f"{clean_label.replace(' ', '_').lower()}-{int(now * 1000)}.png"
    file_path = CAPTURE_DIR / filename
    relative_path = f"./assets/captures/{filename}"
    cv2.imwrite(str(file_path), crop)
    return relative_path


while True:
    ret, frame = cap.read()
    if not ret:
        break

    h, w, _ = frame.shape
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    hand_results = hands.process(rgb)

    if hand_results.multi_hand_landmarks:
        yolo_results = model(frame, verbose=False)[0]
        hand_landmarks = hand_results.multi_hand_landmarks[0]

        tip = hand_landmarks.landmark[8]
        tip_x = int(tip.x * w)
        tip_y = int(tip.y * h)

        thumb = hand_landmarks.landmark[4]
        thumb_x = int(thumb.x * w)
        thumb_y = int(thumb.y * h)

        pinch_distance = math.sqrt((thumb_x - tip_x) ** 2 + (thumb_y - tip_y) ** 2)

        if touched == 0:
            if pinch_distance < pinch_threshold:
                touched = 1
                touch_start = [tip_x, tip_y]
                continue

            active_language_key = refresh_selected_language(time.time())
            detected_objs = []

            for box in yolo_results.boxes:
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                cls = int(box.cls[0])
                label = model.names[cls]
                if (x1 <= tip_x <= x2 and y1 <= tip_y <= y2) and label not in detected_objs and label not in ignore_classes:
                    detected_objs.append(box)

            sorted_objs = sorted(
                detected_objs,
                key=lambda box: (
                    (box.xyxy[0].cpu().numpy()[2] - box.xyxy[0].cpu().numpy()[0]) *
                    (box.xyxy[0].cpu().numpy()[3] - box.xyxy[0].cpu().numpy()[1])
                ),
            )

            for obj in sorted_objs:
                x1, y1, x2, y2 = map(int, obj.xyxy[0].cpu().numpy())
                cls = int(obj.cls[0])
                label = model.names[cls]
                clean_label = label_map.get(label, label)

                now = time.time()
                cooldown_key = f"{active_language_key}:{clean_label.strip().lower()}"
                last_seen = last_submitted_at.get(cooldown_key, 0)
                if now - last_seen < DETECTION_COOLDOWN_SECONDS:
                    continue

                relative_image_path = save_detection_crop(frame, x1, y1, x2, y2, clean_label, now)
                if not relative_image_path:
                    continue

                try:
                    status, payload = submit_detection(
                        language_key=active_language_key,
                        english=clean_label,
                        image=relative_image_path,
                        server_base=SERVER_BASE,
                    )
                    last_submitted_at[cooldown_key] = now
                    print(
                        f"Submitted detection {clean_label} for {active_language_key} "
                        f"with HTTP {status}: {payload}"
                    )
                except Exception as exc:
                    print(f"Failed to submit detection for {clean_label}: {exc}")

        elif touched == 1:
            touch_end = [tip_x, tip_y]
            cv2.circle(frame, (tip_x, tip_y), 10, (0, 0, 255), -1)
            cv2.rectangle(
                frame,
                (int(touch_start[0]), int(touch_start[1])),
                (int(touch_end[0]), int(touch_end[1])),
                (0, 255, 0),
                2,
            )

            if pinch_distance > pinch_threshold:
                touched = 2

        elif touched == 2:
            if (abs(touch_start[0] - touch_end[0]) < 20) or (abs(touch_start[1] - touch_end[1]) < 20):
                touched = 0
                continue

            crop = frame[touch_start[1]:touch_end[1], touch_start[0]:touch_end[0]]
            if crop.size > 0:
                file_path = SCREENSHOT_DIR / "screenshot.png"
                cv2.imwrite(str(file_path), crop)

            touched = 0

    cv2.imshow("LanGo", frame)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()
