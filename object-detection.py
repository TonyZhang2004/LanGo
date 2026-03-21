import cv2
import mediapipe as mp
import time
from ultralytics import YOLO
import math



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


# Hand skeleton connections
HAND_CONNECTIONS = [
    (0,1),(1,2),(2,3),(3,4),
    (0,5),(5,6),(6,7),(7,8),
    (5,9),(9,10),(10,11),(11,12),
    (9,13),(13,14),(14,15),(15,16),
    (13,17),(17,18),(18,19),(19,20),
    (0,17)
]

# -----------------------
# YOLO Model
# -----------------------
model = YOLO("yolov8s-oiv7.pt")

ignore_classes = ["Building", "Office building"]
priority_classes = ["Man", "Woman"]


# -----------------------
# Webcam
# -----------------------
cap = cv2.VideoCapture(0)

# cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
# cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

frame_timestamp = 0

while True:
    ret, frame = cap.read()
    if not ret:
        break

    h, w, _ = frame.shape

    yolo_results = model(frame)[0] #YOLO results
    #frame = yolo_results[0].plot()



     # Convert to RGB for MediaPipe
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    hand_results = hands.process(rgb)

    tip_x, tip_y = 0,0

    if hand_results.multi_hand_landmarks:
        hand_landmarks = hand_results.multi_hand_landmarks[0]

        # Index fingertip = landmark 8
        tip = hand_landmarks.landmark[8]
        tip_x = int(tip.x * w)
        tip_y = int(tip.y * h)

        # Draw red dot
        cv2.circle(frame, (tip_x, tip_y), 10, (0, 0, 255), -1)

    detected_objs = []
    for box in yolo_results.boxes:
        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
        cls = int(box.cls[0])
        label = model.names[cls]
        if x1 <= tip_x <= x2 and y1 <= tip_y <= y2: #inside bounding box
            #add to list of detected 
            detected_objs.append(box)

            # cv2.rectangle(frame,
            #           (int(x1), int(y1)),
            #           (int(x2), int(y2)),
            #           (0, 255, 0), 2)

            # cv2.putText(frame, label,
            #             (int(x1), int(y1) - 5),
            #             cv2.FONT_HERSHEY_SIMPLEX,
            #             0.5, (0,255,0), 2)

    #choose object detected that finger is closest to center
    closest_obj = None
    smallest_area = 1000000
    for obj in detected_objs:
        x1, y1, x2, y2 = obj.xyxy[0].cpu().numpy()
        cls = int(obj.cls[0])
        label = model.names[cls]
        cx = (x1 + x2) / 2
        cy = (y1 + y2) / 2
        distance = math.hypot(tip_x - cx, tip_y - cy)
        area = (x2 - x1) * (y2 - y1)

        # take closest to center
        #if (closest_dist > distance) and label not in ignore_classes :
        if closest_obj not in priority_classes and obj in priority_classes:
            if smallest_area > area and label not in ignore_classes:
                # make sure to choose smallest area
                closest_obj = obj
                smallest_area = area

    #print out box
    if closest_obj:
        x1, y1, x2, y2 = closest_obj.xyxy[0].cpu().numpy()
        cls = int(closest_obj.cls[0])
        label = model.names[cls]

        cv2.rectangle(frame,
                    (int(x1), int(y1)),
                    (int(x2), int(y2)),
                    (0, 255, 0), 2)
        cv2.putText(frame, label,
                    (int(x1), int(y1) - 5),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5, (0,255,0), 2)


    cv2.imshow("LanGo", frame)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()