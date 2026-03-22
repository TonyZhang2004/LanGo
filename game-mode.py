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
model = YOLO("yolov8s-oiv7.pt")

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

while True:
    ret, frame = cap.read()
    if not ret:
        break

    h, w, _ = frame.shape

     # Convert to RGB for MediaPipe
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    hand_results = hands.process(rgb)

    yolo_results = model(frame, verbose=False)[0] #YOLO results

    detected_objs = []

    for box in yolo_results.boxes:
        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
        cls = int(box.cls[0])
        label = model.names[cls]
        if label not in detected_objs and label not in ignore_classes:
            detected_objs.append(box)
        
    random_obj = random.choice(detected_objs)
    


