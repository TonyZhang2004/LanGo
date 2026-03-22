# LanGo Raspberry Pi Integration Contract

## Purpose

This document is the handoff contract for Raspberry Pi side code.

If you give this file to another coding assistant, it should be enough for it to generate a working Python file that:

0. lets the user choose a target language on the Raspberry Pi screen
1. detects or receives an object label
2. submits that label to LanGo as a pending detection
3. optionally uploads a captured JPG
4. lets the Pi-side UI confirm or reject the detection
5. causes confirmed detections to appear in the web app translation history

## Use The HTTP API, Not Raw SQLite

The Raspberry Pi side should **not** write SQL directly.

Use the LanGo backend HTTP API so that:

- translation is handled consistently
- pending detections work correctly
- confirmed entries land in the shared SQLite database
- the web app updates from the same source of truth

The backend owns the database at:

- `data/lango.db`

## Canonical Pi-Side Helper Functions

These are the current helper functions the Pi code should call:

- [detection_client.py](/Users/tony/Desktop/LanGo/hardware/detection_client.py)
- [pi_upload_image_example.py](/Users/tony/Desktop/LanGo/hardware/pi_upload_image_example.py)
- [pi_screen.py](/Users/tony/Desktop/LanGo/pi_screen.py)

### 1. Read Or Change The Selected Language

Functions:

- `get_selected_language(server_base=SERVER_BASE)`
- `set_selected_language(language_key, server_base=SERVER_BASE)`

Defined at:

- [detection_client.py](/Users/tony/Desktop/LanGo/hardware/detection_client.py#L25)

Use these when the Raspberry Pi screen needs to display or update the active target language.

The backend stores one shared selected language value for the device. The camera detection script reads this value and uses it for new `submit_detection(...)` calls.

Return payload shape:

```json
{
  "selectedLanguage": {
    "key": "spanish",
    "label": "Spanish",
    "locale": "es-ES"
  },
  "languages": [
    {
      "key": "arabic",
      "label": "Arabic",
      "locale": "ar-SA"
    }
  ]
}
```

### 2. Submit A Pending Detection

Function:

- `submit_detection(english, image=None, language_key=None, server_base=SERVER_BASE)`

Defined at:

- [detection_client.py](/Users/tony/Desktop/LanGo/hardware/detection_client.py#L9)

Use this when YOLO has identified an object and you want LanGo to create a pending queue item for user confirmation.

Arguments:

- `language_key`: one of `arabic`, `chinese`, `french`, `japanese`, `russian`, `spanish`
- `english`: detected English label, for example `apple`, `shoe`, `bottle`
- `image`: optional frontend-served image path such as `./assets/captures/apple-123.jpg`
- `language_key`: optional explicit override. If omitted, the backend uses the currently selected device language.
- `server_base`: base URL like `http://127.0.0.1:8001`

Return shape:

```python
status_code, payload
```

Typical payload:

```json
{
  "entry": {
    "pendingId": "abc123def456",
    "languageKey": "spanish",
    "english": "apple",
    "translated": "manzana",
    "speech": "manzana",
    "image": "./assets/captures/apple-123.jpg",
    "createdAt": "2026-03-21T19:55:00-04:00"
  },
  "pending": {
    "pendingId": "abc123def456",
    "languageKey": "spanish",
    "english": "apple",
    "translated": "manzana",
    "speech": "manzana",
    "image": "./assets/captures/apple-123.jpg",
    "createdAt": "2026-03-21T19:55:00-04:00"
  },
  "created": true
}
```

### 3. List Pending Detections

Function:

- `list_pending(language_key=None, server_base=SERVER_BASE)`

Defined at:

- [detection_client.py](/Users/tony/Desktop/LanGo/hardware/detection_client.py#L25)

Use this if the Pi-side screen needs to refresh its queue view.

Arguments:

- `language_key`: optional filter, usually the current selected target language
- `server_base`: base URL like `http://127.0.0.1:8001`

Return payload:

```json
{
  "pending": [
    {
      "pendingId": "abc123def456",
      "languageKey": "spanish",
      "english": "apple",
      "translated": "manzana",
      "speech": "manzana",
      "image": "./assets/captures/apple-123.jpg",
      "createdAt": "2026-03-21T19:55:00-04:00"
    }
  ]
}
```

### 4. Read Confirmed History

Function:

- `get_history(language_key, server_base=SERVER_BASE)`

Defined at:

- [detection_client.py](/Users/tony/Desktop/LanGo/hardware/detection_client.py#L48)

Use this when the Pi screen needs to show the latest confirmed translation summary for the selected language.

Return payload:

```json
{
  "entries": [
    {
      "id": "42",
      "languageKey": "spanish",
      "english": "apple",
      "translated": "manzana",
      "speech": "manzana",
      "lang": "es-ES",
      "image": "./assets/captures/apple-123.png",
      "time": "7:55 PM",
      "createdAt": "2026-03-21T19:55:00-04:00"
    }
  ]
}
```

### 5. Confirm A Pending Detection

Function:

- `confirm_pending(pending_id, server_base=SERVER_BASE)`

Defined at:

- [detection_client.py](/Users/tony/Desktop/LanGo/hardware/detection_client.py#L31)

Use this when the user accepts the detected word on the Raspberry Pi screen.

Effect:

- removes the pending item from the queue
- inserts the confirmed translation into the shared DB
- makes it show up in the web app history

Arguments:

- `pending_id`: the `pendingId` returned from `submit_detection(...)`
- `server_base`: base URL like `http://127.0.0.1:8001`

Return payload:

```json
{
  "entry": {
    "id": "42",
    "languageKey": "spanish",
    "english": "apple",
    "translated": "manzana",
    "speech": "manzana",
    "lang": "es-ES",
    "image": "./assets/captures/apple-123.jpg",
    "time": "7:55 PM",
    "createdAt": "2026-03-21T19:55:00-04:00"
  }
}
```

### 6. Reject A Pending Detection

Function:

- `reject_pending(pending_id, server_base=SERVER_BASE)`

Defined at:

- [detection_client.py](/Users/tony/Desktop/LanGo/hardware/detection_client.py#L43)

Use this when the user says the detected word should **not** be added to history.

Effect:

- removes the pending item from the queue
- does **not** insert anything into the DB

Return payload:

```json
{
  "rejected": true,
  "pendingId": "abc123def456"
}
```

### 7. Upload A Real JPG File

Function:

- `upload_image(entry_id, image_path, server_base=SERVER_BASE)`

Defined at:

- [pi_upload_image_example.py](/Users/tony/Desktop/LanGo/hardware/pi_upload_image_example.py#L9)

Use this only if the Pi captured a real JPG file and you want the backend to host it for all clients.

Important:

- `confirm_pending(...)` already supports an image path if the capture was written into `frontend/assets/captures/`
- use `upload_image(...)` when the Pi has a local JPG file that is **not** already inside the LanGo frontend assets directory

Arguments:

- `entry_id`: the confirmed DB entry id returned from `confirm_pending(...)`
- `image_path`: local Pi file path to the JPG
- `server_base`: base URL like `http://127.0.0.1:8001`

Effect:

- uploads the file bytes to the backend
- backend saves it under `frontend/assets/uploads/`
- backend updates that DB entry’s `image` field

## Intended Raspberry Pi Flow

The Pi-side code should follow this order:

1. load the current selected language with `get_selected_language(...)`
2. let the user change it from the Raspberry Pi screen with `set_selected_language(...)` or the built-in Pi page
3. run YOLO detection
4. normalize the detected English object label
5. save a crop image under `frontend/assets/captures/`
6. call `submit_detection(...)`
7. show a scrollable pending queue on the Pi screen
8. let the user select an item from the queue
9. if user accepts, call `confirm_pending(...)`
10. if user rejects, call `reject_pending(...)`
11. refresh `get_history(...)` so the Pi can show the latest saved translation
12. if needed, upload a real JPG with `upload_image(...)` after confirmation

## Native Raspberry Pi Screen

LanGo now includes a native Tkinter Raspberry Pi app:

- run with `.venv/bin/python pi_screen.py`

Files:

- [pi_screen.py](/Users/tony/Desktop/LanGo/pi_screen.py)
- [screen-test.py](/Users/tony/Desktop/LanGo/screen-test.py)

Behavior:

- fullscreen native Python UI for Raspberry Pi
- uses the same warm paper / lime accent theme direction as the webapp
- lets the user switch between `Language` and `Mode`
- keeps `Learn` functional and `Game` as a placeholder
- shows a scrollable pending-detection queue for the selected language
- lets the user tap a pending item and choose `Add to History` or `Reject`
- shows the latest confirmed translation summary for the selected language

The browser page at `pi.html` remains available, but `pi_screen.py` is now the intended native on-device UI.

## Built-In Raspberry Pi Language Panel

LanGo now includes a dedicated Pi-friendly language picker page:

- `http://<server-host>:8000/pi.html`

Files:

- [pi.html](/Users/tony/Desktop/LanGo/frontend/pi.html)
- [pi-panel.js](/Users/tony/Desktop/LanGo/frontend/pi-panel.js)
- [pi.css](/Users/tony/Desktop/LanGo/frontend/pi.css)

Behavior:

- fetches the current selected language from `GET /api/device/language`
- shows tappable buttons for all supported languages
- updates the selected language with `POST /api/device/language`
- affects future object detections without restarting the Pi detector

The detector script in [object-detection.py](/Users/tony/Desktop/LanGo/object-detection.py) polls the selected language from the backend and uses it for new detection submissions.

## Current Backend Endpoints

These are the actual backend routes:

- `GET /api/device/language`
- `POST /api/device/language`
- `POST /api/detections`
- `GET /api/detections/pending?language=<language_key>`
- `POST /api/detections/confirm`
- `POST /api/detections/reject`
- `POST /api/upload-image?entryId=<entry_id>&filename=<file_name>`
- `GET /api/history?language=<language_key>`

Implemented in:

- [server.py](/Users/tony/Desktop/LanGo/backend/server.py#L94)

## Detection Workflow Behavior

The pending detection workflow is implemented in:

- [detection_workflow.py](/Users/tony/Desktop/LanGo/backend/detection_workflow.py#L16)

Important behavior:

- selected device language is persisted in `data/device_language.json`
- the detector reads that selected language and applies it to future submissions
- detector crop images are written into `frontend/assets/captures/` as PNG files
- translation happens when `submit_detection(...)` is called, even if the detector only sends the English label
- queue items are stored in memory on the backend
- pending detections are deduped by `english` within each language
- confirmed detections are inserted into SQLite
- history is capped at 10 entries per language

## What The Pi Code Should Generate

A fully functioning Pi-side Python file should:

- read the selected `language_key`
- let the user change `language_key` on the Pi screen
- run detection or receive a detected word
- call `submit_detection(english, image=image, language_key=language_key)`
- store the returned `pendingId`
- show a scrollable queue UI on the Pi screen
- allow the user to select which pending word to act on
- on accept, call `confirm_pending(pendingId)`
- on reject, call `reject_pending(pendingId)`
- read `get_history(language_key)` to show the latest confirmed translation
- optionally call `upload_image(entry_id, image_path, server_base)` if the image file needs to be hosted by the backend

## Minimal Reference Snippet

```python
from hardware.detection_client import submit_detection, confirm_pending, reject_pending

SERVER_BASE = "http://127.0.0.1:8001"
LANGUAGE_KEY = "spanish"

status, payload = submit_detection(
    "apple",
    image="./assets/captures/apple-123.jpg",
    server_base=SERVER_BASE,
)

pending = payload["pending"]
pending_id = pending["pendingId"]

user_accepts = True

if user_accepts:
    status, payload = confirm_pending(pending_id, server_base=SERVER_BASE)
    entry = payload["entry"]
    print("Saved to DB:", entry["id"], entry["english"], entry["translated"])
else:
    status, payload = reject_pending(pending_id, server_base=SERVER_BASE)
    print("Rejected:", payload["pendingId"])
```

## Notes For The Assistant Generating Pi Code

If another assistant is generating the Raspberry Pi Python file, it should follow these constraints:

- use Python
- use the helper functions from `hardware/detection_client.py`
- do not write raw SQL
- do not bypass the backend
- preserve `pendingId` from submit to confirm/reject
- if the server is on the same Pi, use `http://127.0.0.1:<port>`
- if the server is on another laptop, use that machine’s LAN IP and make sure the server was started with `HOST=0.0.0.0`
- keep the UI simple but queue-oriented: language picker, pending list, selected item detail, confirm button, reject button

## Related Files

- [object-detection.py](/Users/tony/Desktop/LanGo/object-detection.py)
- [detection_client.py](/Users/tony/Desktop/LanGo/hardware/detection_client.py)
- [pi_upload_image_example.py](/Users/tony/Desktop/LanGo/hardware/pi_upload_image_example.py)
- [server.py](/Users/tony/Desktop/LanGo/backend/server.py)
- [detection_workflow.py](/Users/tony/Desktop/LanGo/backend/detection_workflow.py)
- [translation_store.py](/Users/tony/Desktop/LanGo/backend/translation_store.py)
