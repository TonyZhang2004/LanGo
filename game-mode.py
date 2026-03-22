import cv2
import mediapipe as mp
import time
from ultralytics import YOLO
import math
import os
from gtts import gTTS
from io import BytesIO
import pygame
import random

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


        cv2.imshow("LanGo", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

        current_time = time.perf_counter()
        while (current_time - start_time) < 0.2:
            time.sleep(0.01)
            current_time = time.perf_counter()
        
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    game()
