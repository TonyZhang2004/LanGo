import math
import os
import re
import time
from pathlib import Path
from gtts import gTTS
from io import BytesIO
import pygame
from cache import fr_translated, zh_cn_translated, es_translated

import cv2
import mediapipe as mp
from ultralytics import YOLO

from hardware.detection_client import (
    SERVER_BASE as DEFAULT_SERVER_BASE,
    get_selected_language,
    submit_detection,
)


ROOT_DIR = Path(__file__).resolve().parent
LEGACY_IMAGES_DIR = ROOT_DIR / "images"
SERVER_BASE = os.environ.get("LANGO_SERVER_BASE", DEFAULT_SERVER_BASE)
FRAME_INTERVAL_SECONDS = float(os.environ.get("LANGO_FRAME_INTERVAL_SECONDS", "0.2"))
LANGUAGE_CACHE_SECONDS = float(os.environ.get("LANGO_LANGUAGE_CACHE_SECONDS", "1.0"))
DETECTION_COOLDOWN_SECONDS = float(os.environ.get("LANGO_DETECTION_COOLDOWN_SECONDS", "3.0"))


def slugify_label(label):
    slug = re.sub(r"[^a-z0-9]+", "-", str(label).strip().lower()).strip("-")
    return slug or "capture"


def clear_temp_directory(directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    for child in directory.iterdir():
        if child.is_file():
            child.unlink(missing_ok=True)


def clear_runtime_storage():
    if LEGACY_IMAGES_DIR.exists():
        clear_temp_directory(LEGACY_IMAGES_DIR)


def encode_capture_image(crop):
    if crop.size == 0:
        return None
    success, encoded = cv2.imencode(".png", crop)
    if not success:
        return None
    return encoded.tobytes()


def current_language_key(language_cache, server_base=SERVER_BASE):
    now = time.monotonic()
    cached_key = language_cache.get("key")
    cached_at = language_cache.get("checked_at", 0.0)
    if cached_key and now - cached_at < LANGUAGE_CACHE_SECONDS:
        return cached_key

    try:
        _, payload = get_selected_language(server_base=server_base)
        language_cache["key"] = payload["selectedLanguage"]["key"]
        language_cache["checked_at"] = now
    except Exception:
        language_cache["key"] = cached_key or "spanish"
        language_cache["checked_at"] = now
    return language_cache["key"]


def should_submit_detection(language_key, label, recent_submissions, now=None):
    moment = now if now is not None else time.monotonic()
    stale_keys = [
        key
        for key, submitted_at in recent_submissions.items()
        if moment - submitted_at >= DETECTION_COOLDOWN_SECONDS
    ]
    for stale_key in stale_keys:
        del recent_submissions[stale_key]

    cooldown_key = (language_key, str(label).strip().lower())
    last_seen = recent_submissions.get(cooldown_key)
    if last_seen is not None and moment - last_seen < DETECTION_COOLDOWN_SECONDS:
        return False

    recent_submissions[cooldown_key] = moment
    return True


def submit_pending_detection(label, crop, recent_submissions, language_cache, server_base=SERVER_BASE):
    language_key = current_language_key(language_cache, server_base=server_base)
    if not should_submit_detection(language_key, label, recent_submissions):
        return

    image_bytes = encode_capture_image(crop)
    image_filename = f"{slugify_label(label)}.png"
    try:
        status, payload = submit_detection(
            label,
            image_bytes=image_bytes,
            image_filename=image_filename,
            server_base=server_base,
        )
    except Exception as exc:
        print(f"Could not submit pending detection for {label}: {exc}")
        return

    if payload.get("created"):
        print(f"Queued {label} for {language_key}.")
    else:
        print(f"Skipped duplicate pending detection for {label} in {language_key}.")

    discarded_ids = payload.get("discardedPendingIds") or []
    if discarded_ids:
        print(f"Discarded {len(discarded_ids)} older pending item(s) to keep the queue capped at five.")

    if status >= 400:
        print(f"Detection submit returned HTTP {status} for {label}.")


def save_manual_screenshot(crop):
    if LEGACY_IMAGES_DIR.exists() or crop.size > 0:
        LEGACY_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
        filepath = LEGACY_IMAGES_DIR / "screenshot.png"
        if cv2.imwrite(str(filepath), crop):
            print(f"Saved manual crop to {filepath}.")

def translate(text, language):
    mp3_fo = BytesIO()
    tts = gTTS(text, lang='en')
    tts.write_to_fp(mp3_fo)
    mp3_fo.seek(0)

    pygame.mixer.init()
    sound = pygame.mixer.Sound(mp3_fo)
    sound.play()

    while pygame.mixer.get_busy():
        time.sleep(0.1)

    # say it translated
    mp3_fo = BytesIO()
    translated = text
    if language == 'fr':
        translated = fr_translated.get(text, text)
    elif language == 'zh-CN':
        translated = zh_cn_translated.get(text, text)
    elif language == 'es':
        translated = es_translated.get(text, text)
    else:
        return
    tts = gTTS(translated, lang=language)
    tts.write_to_fp(mp3_fo)
    mp3_fo.seek(0)

    pygame.mixer.init()
    sound = pygame.mixer.Sound(mp3_fo)
    sound.play()

    while pygame.mixer.get_busy():
        time.sleep(0.1)


def learn():
    clear_runtime_storage()

    mp_hands = mp.solutions.hands
    hands = mp_hands.Hands(
        static_image_mode=False,
        max_num_hands=1,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5,
    )

    model = YOLO("yolov8n.pt")
    ignore_classes = ["Building", "Office building", "Clothing"]
    label_map = {
        "Human hand": "Hand",
        "Human face": "Face",
        "Footwear": "Shoe",
        "Desk": "Table",
        "Tablet computer": "Tablet",
    }

    cap = cv2.VideoCapture(0)
    touched = 0
    touch_start = [0, 0]
    touch_end = [0, 0]
    pinch_threshold = 40
    recent_submissions = {}
    language_cache = {"key": None, "checked_at": 0.0}
    #language = 'fr'

    seen_labels = []

    while True:
        frame_started = time.perf_counter()
        ret, frame = cap.read()
        if not ret:
            break

        height, width, _ = frame.shape
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        hand_results = hands.process(rgb)

        if hand_results.multi_hand_landmarks:
            yolo_results = model(frame, verbose=False)[0]
            hand_landmarks = hand_results.multi_hand_landmarks[0]

            tip = hand_landmarks.landmark[8]
            tip_x = int(tip.x * width)
            tip_y = int(tip.y * height)

            thumb = hand_landmarks.landmark[4]
            thumb_x = int(thumb.x * width)
            thumb_y = int(thumb.y * height)

            pinch_distance = math.sqrt((thumb_x - tip_x) ** 2 + (thumb_y - tip_y) ** 2)

            if touched == 0:
                if pinch_distance < pinch_threshold:
                    touched = 1
                    touch_start = [tip_x, tip_y]
                    continue

                detected_boxes = []
                for box in yolo_results.boxes:
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    cls = int(box.cls[0])
                    label = model.names[cls]
                    if label in ignore_classes:
                        continue
                    if x1 <= tip_x <= x2 and y1 <= tip_y <= y2:
                        detected_boxes.append(box)

                if detected_boxes:
                    best_box = min(
                        detected_boxes,
                        key=lambda box: (
                            (box.xyxy[0].cpu().numpy()[2] - box.xyxy[0].cpu().numpy()[0])
                            * (box.xyxy[0].cpu().numpy()[3] - box.xyxy[0].cpu().numpy()[1])
                        ),
                    )
                    x1, y1, x2, y2 = map(int, best_box.xyxy[0].cpu().numpy())
                    cls = int(best_box.cls[0])
                    label = model.names[cls]
                    clean_label = label_map.get(label, label)
                    if clean_label not in seen_labels:
                        seen_labels.append(clean_label)
                        #translate(clean_label, language)
                        crop = frame[y1:y2, x1:x2]
                        submit_pending_detection(
                            clean_label,
                            crop,
                            recent_submissions,
                            language_cache,
                            server_base=SERVER_BASE,
                        )

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
                if abs(touch_start[0] - touch_end[0]) < 20 or abs(touch_start[1] - touch_end[1]) < 20:
                    touched = 0
                    continue

                crop = frame[touch_start[1]:touch_end[1], touch_start[0]:touch_end[0]]
                if crop.size > 0:
                    save_manual_screenshot(crop)

                touched = 0

        # cv2.imshow("LanGo", frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

        while time.perf_counter() - frame_started < FRAME_INTERVAL_SECONDS:
            time.sleep(0.01)

    cap.release()
    cv2.destroyAllWindows()

# randomly selects object detected in frame and does TTS in the desired language
# user points to the object they think it is
# tts confirms/denies


def speak(text, language):
    mp3_fo = BytesIO()
    tts = gTTS(text, lang=language)
    tts.write_to_fp(mp3_fo)
    mp3_fo.seek(0)

    pygame.mixer.init()
    sound = pygame.mixer.Sound(mp3_fo)
    sound.play()

    while pygame.mixer.get_busy():
        time.sleep(0.1)


def game():
    # -----------------------
    # MediaPipe setup
    # -----------------------
    mp_hands = mp.solutions.hands
    mp_draw = mp.solutions.drawing_utils

    hands = mp_hands.Hands(
        static_image_mode=False,
        max_num_hands=1,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5
    )

    # -----------------------
    # YOLO Model
    # -----------------------
    model = YOLO("yolov8n.pt")

    ignore_classes = ["Building", "Office building", "Clothing"]

    label_map = {
        "Human hand": "Hand",
        "Human face": "Face",
        "Footwear": "Shoe",
        "Desk": "Table",
        "Tablet computer": "Tablet",
    }

    # -----------------------
    # Webcam
    # -----------------------
    cap = cv2.VideoCapture(0)

    lang = 'en'
    #state machine var
    # 0: no obj selected
    # 1: obj selected, waiting for user to get correct
    # 2: user correct, reset
    state = 0
    random_obj = ""
    timeout = 10
    timeout_start = 0.0
    recent_objs = []
    while True:
        start_time = time.perf_counter()

        ret, frame = cap.read()
        if not ret:
            break

        h, w, _ = frame.shape

        # Convert to RGB for MediaPipe
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        hand_results = hands.process(rgb)

        
        if state == 0:
            yolo_results = model(frame, verbose=False)[0] #YOLO results

            detected_objs = []

            for box in yolo_results.boxes:
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                cls = int(box.cls[0])
                label = model.names[cls]
                if label not in detected_objs and label not in ignore_classes:

                    detected_objs.append(label)
            
            # CHANGE THIS CODE TO GET TRANSLATED WORD FROM LABEL!
            if len(detected_objs) > 0:
                random_obj = random.choice(detected_objs)
                if random_obj in recent_objs:
                    continue
                else:
                    recent_objs.append(random_obj)
                    if len(recent_objs) > 5:
                        recent_objs.pop(0)

                    word_to_trans = label_map.get(random_obj, random_obj)
                    speak(word_to_trans, lang)
                    timeout_start = time.perf_counter()
                    state = 1

        elif state == 1:
            if hand_results.multi_hand_landmarks:
                hand_landmarks = hand_results.multi_hand_landmarks[0]

                tip = hand_landmarks.landmark[8]
                tip_x = int(tip.x * w)
                tip_y = int(tip.y * h)

                yolo_results = model(frame, verbose=False)[0] #YOLO results

                for box in yolo_results.boxes:
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    cls = int(box.cls[0])
                    label = model.names[cls]
                    if (x1 <= tip_x <= x2 and y1 <= tip_y <= y2) and label == random_obj:
                        speak("Correct!", 'en')
                        state = 2
                        break

            if state != 2:
                current_time = time.perf_counter()
                if (current_time - timeout_start) > timeout:
                    speak("Next item", 'en')
                    if random_obj in recent_objs:
                        recent_objs.remove(random_obj)
                    state = 2

        elif state == 2:
            random_obj = ""
            state = 0


        #cv2.imshow("LanGo", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

        current_time = time.perf_counter()
        while (current_time - start_time) < 0.2:
            time.sleep(0.01)
            current_time = time.perf_counter()
        
    cap.release()
    cv2.destroyAllWindows()




