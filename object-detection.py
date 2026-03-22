import cv2
import mediapipe as mp
import time
from ultralytics import YOLO
import math
import os
import json
import sys
from datetime import datetime
from urllib import error, request
from pathlib import Path
from urllib import error, parse, request

# as hand is detected, will first check for pinching gesture. 
# if pinching gesture is detected: save first x, y then save x,y when pinch gesture is let go
# if not, then run YOLO model and do pointing detection

# Default is same-machine localhost. For another device on the same network,
SERVER_BASE = "http://35.3.62.156:8000"
SERVER_URL = SERVER_BASE + "/api/history"

def current_time_label():
    return datetime.now().strftime("%I:%M %p").lstrip("0")

def insert_entry(entry, server_url=SERVER_URL):
    req = request.Request(
        server_url,
        data=json.dumps(entry).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with request.urlopen(req, timeout=10) as response:
        body = response.read().decode("utf-8")
        return response.status, body

def upload_image(entry_id, image_path):
    file_path = Path(image_path)
    endpoint = (
        f"{SERVER_BASE}/api/upload-image?"
        f"entryId={parse.quote(str(entry_id))}&filename={parse.quote(file_path.name)}"
    )
    req = request.Request(
        endpoint,
        data=file_path.read_bytes(),
        headers={"Content-Type": "image/jpeg"},
        method="POST",
    )
    with request.urlopen(req, timeout=15) as response:
        return response.status, response.read().decode("utf-8")

def log_new_item(entry, image_path):
    try:
        status, body = insert_entry(entry)
    except error.HTTPError as exc:
        print(f"Insert failed with HTTP {exc.code}")
        print(exc.read().decode("utf-8"))
        raise SystemExit(1) from exc
    except error.URLError as exc:
        print("Could not reach the LanGo server.")
        print(f"Checked URL: {SERVER_URL}")
        print("If this script is running on another computer, do not use 127.0.0.1 unless the server is running on that same computer.")
        print(str(exc.reason))
        raise SystemExit(1) from exc

    print(f"Inserted translation entry with HTTP {status}")
    print(body)

    data = json.loads(body)
    print(data["entry"]["id"])
    entry_id = data["entry"]["id"]

    try:
        status, body = upload_image(entry_id, image_path)
    except FileNotFoundError as exc:
        print(f"Image file not found: {image_path}")
        raise SystemExit(1) from exc
    except error.HTTPError as exc:
        print(f"Upload failed with HTTP {exc.code}")
        print(exc.read().decode("utf-8"))
        raise SystemExit(1) from exc
    except error.URLError as exc:
        print("Could not reach the LanGo server.")
        print(f"Checked URL: {SERVER_BASE}")
        print(str(exc.reason))
        raise SystemExit(1) from exc

    print(f"Uploaded image with HTTP {status}")
    print(body)

def main():
    # -----------------------
    # MediaPipe setup
    # -----------------------
    print("hi")
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

    # cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    # cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    vocab_words = [] # words from detected objects

    # state machine variable:
    # 0: no pinch
    # 1: pinch activated
    # 2: pinch released
    touched = 0
    touch_start = [0, 0]
    touch_end = [0, 0]

    pinch_threshold = 40

    while True:
        start_time = time.perf_counter()

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
            thumb = hand_landmarks.landmark[4]
            thumb_x = int(thumb.x * w)
            thumb_y = int(thumb.y * h)

            #distance eq for pinch gesture
            pinch_distance = math.sqrt((thumb_x - tip_x)** 2 + (thumb_y - tip_y) ** 2)


            # Draw red dot
            #cv2.circle(frame, (tip_x, tip_y), 10, (0, 0, 255), -1)
            if touched == 0: #no pinch, default to point detection

                if pinch_distance < pinch_threshold:
                    touched = 1
                    touch_start = [tip_x, tip_y]
                    continue


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
                    if clean_label not in vocab_words: # create image + word if not in vocab list already
                        vocab_words.append(clean_label)
                        filename = f"{clean_label.replace(' ', '_').lower()}.jpg"
                        filepath = os.path.join("images", filename)
                        crop = frame[y1:y2, x1:x2]
                        cv2.imwrite(filepath, crop)

                        entry = {
                            "languageKey": "spanish",
                            "english": clean_label,
                            "translated": "n",
                            "speech": "n",
                            "image": None,
                            "time": current_time_label(),
                        }
                        log_new_item(entry, filepath)

                # cv2.rectangle(frame,
                #           (int(x1), int(y1)),
                #           (int(x2), int(y2)),
                #           (0, 255, 0), 2)
                # cv2.putText(frame, clean_label,
                #             (int(x1), int(y1) - 5),
                #             cv2.FONT_HERSHEY_SIMPLEX,
                #             0.5, (0,255,0), 2)

            elif touched == 1: # still pinching
                touch_end = [tip_x, tip_y]
                cv2.circle(frame, (tip_x, tip_y), 10, (0, 0, 255), -1)
                cv2.rectangle(frame,
                        (int(touch_start[0]), int(touch_start[1])),
                        (int(touch_end[0]), int(touch_end[1])),
                        (0, 255, 0), 2)

                if pinch_distance > pinch_threshold:
                    touched = 2
            
            elif touched == 2: # pinch let go, store picture
                if (abs(touch_start[0] - touch_end[0]) < 20) or (abs(touch_start[1] - touch_end[1]) < 20):
                    touched = 0
                    continue 

                crop = frame[touch_start[1]:touch_end[1], touch_start[0]:touch_end[0]]
                if crop.size > 0:
                    filename = f"screenshot.jpg"
                    filepath = os.path.join("images", filename)
                    cv2.imwrite(filepath, crop)

                touched = 0



        print(vocab_words)
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
    main()
