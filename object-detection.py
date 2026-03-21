import cv2
import mediapipe as mp
import time
from ultralytics import YOLO
import math
import os

# as hand is detected, will first check for pinching gesture. 
# if pinching gesture is detected: save first x, y then save x,y when pinch gesture is let go
# if not, then run YOLO model and do pointing detection

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

}

# -----------------------
# Webcam
# -----------------------
cap = cv2.VideoCapture(0)

# cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
# cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

frame_timestamp = 0
vocab_words = [] # words from detected objects

while True:
    ret, frame = cap.read()
    if not ret:
        break

    h, w, _ = frame.shape

     # Convert to RGB for MediaPipe
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    hand_results = hands.process(rgb)


    if hand_results.multi_hand_landmarks:
        yolo_results = model(frame, verbose=False)[0] #YOLO results

        hand_landmarks = hand_results.multi_hand_landmarks[0]

        # Index fingertip = landmark 8
        tip = hand_landmarks.landmark[8]
        tip_x = int(tip.x * w)
        tip_y = int(tip.y * h)

        # Thumb index

        # Draw red dot
        #cv2.circle(frame, (tip_x, tip_y), 10, (0, 0, 255), -1)

        detected_objs = []
        
        for box in yolo_results.boxes:
            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
            cls = int(box.cls[0])
            label = model.names[cls]
            if (x1 <= tip_x <= x2 and y1 <= tip_y <= y2) and label not in detected_objs and label not in ignore_classes: #inside bounding box
                #add to list of detected 
                detected_objs.append(box)

        sorted_objs = sorted(
        detected_objs,
        key=lambda box: (
            (box.xyxy[0].cpu().numpy()[2] - box.xyxy[0].cpu().numpy()[0]) *
            (box.xyxy[0].cpu().numpy()[3] - box.xyxy[0].cpu().numpy()[1])
        )
        )

        for obj in sorted_objs:
            x1, y1, x2, y2 = map(int, obj.xyxy[0].cpu().numpy())
            cls = int(obj.cls[0])
            label = model.names[cls]
            clean_label = label_map.get(label, label)
            if clean_label not in vocab_words: #create image + word if not in vocab list already
                vocab_words.append(clean_label)
                filename = f"{clean_label.lower()}.jpg"
                filepath = os.path.join("images", filename)
                crop = frame[y1:y2, x1:x2]
                cv2.imwrite(filepath, crop)

            # cv2.rectangle(frame,
            #           (int(x1), int(y1)),
            #           (int(x2), int(y2)),
            #           (0, 255, 0), 2)
            # cv2.putText(frame, clean_label,
            #             (int(x1), int(y1) - 5),
            #             cv2.FONT_HERSHEY_SIMPLEX,
            #             0.5, (0,255,0), 2)



    print(vocab_words)
    cv2.imshow("LanGo", frame)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()