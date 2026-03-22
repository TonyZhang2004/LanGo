import cv2
import mediapipe as mp
import time
from ultralytics import YOLO
import math
import os

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

