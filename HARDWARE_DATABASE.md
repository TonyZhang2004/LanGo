# LanGo Hardware Database Guide

## Purpose

This document explains how the Raspberry Pi side of LanGo should store translation history in the local database.

Current project assumption:

- one Raspberry Pi device
- one local web app
- one local SQLite database
- Python on the hardware side

For this setup, the Raspberry Pi should usually write entries through the local HTTP API instead of writing raw SQL directly.

## Recommended Architecture

Use this flow on the Raspberry Pi:

1. Capture object, text, or speech input.
2. Run detection and translation logic.
3. Build a translation entry payload.
4. POST that payload to the local LanGo server.
5. Let the web app read the stored history from the same database.

For a single-device demo, the Raspberry Pi can call:

- `http://127.0.0.1:8000/api/history`

If you run the server on another port, replace `8000` with that port.

If the Pi script is running on a different computer from the LanGo server, do not use `127.0.0.1`.
Use the server machine's local network IP instead, for example:

- `http://192.168.1.25:8000/api/history`

In that case, start the server so it listens on the network, not just localhost:

```bash
cd /Users/tony/Desktop/LanGo
HOST=0.0.0.0 PORT=8000 .venv/bin/python -m backend.server
```

## Database Location

The local SQLite database is stored at:

- `data/lango.db`

The backend store code lives at:

- `backend/translation_store.py`

## Translation Entry Shape

Each entry stored in the database has these fields:

- `languageKey`
- `english`
- `translated`
- `speech`
- `image`
- `time`

`image` can be `null` if no image is available yet.

Example:

```json
{
  "languageKey": "spanish",
  "english": "ball",
  "translated": "bola",
  "speech": "bola",
  "image": null,
  "time": "2:42 PM"
}
```

## Supported Language Keys

Use one of these values for `languageKey`:

- `arabic`
- `chinese`
- `french`
- `japanese`
- `portuguese`
- `russian`
- `spanish`

## Recommended Insert Path: Local API

This is the safest approach because the backend already validates the payload and writes into SQLite for you.

### HTTP Endpoint

- `POST /api/history`

### Required JSON Fields

- `languageKey`
- `english`
- `translated`
- `speech`
- `time`

`image` is optional and may be `null`.

### Example With `curl`

```bash
curl -X POST http://127.0.0.1:8000/api/history \
  -H "Content-Type: application/json" \
  -d '{
    "languageKey": "japanese",
    "english": "ball",
    "translated": "ボール",
    "speech": "ボール",
    "image": "./assets/ball.jpg",
    "time": "3:12 PM"
  }'
```

### Example With Python On The Raspberry Pi

```python
import json
from urllib import request


payload = {
    "languageKey": "spanish",
    "english": "shoe",
    "translated": "zapato",
    "speech": "zapato",
    "image": None,
    "time": "3:15 PM",
}

req = request.Request(
    "http://127.0.0.1:8000/api/history",
    data=json.dumps(payload).encode("utf-8"),
    headers={"Content-Type": "application/json"},
    method="POST",
)

with request.urlopen(req) as response:
    print(response.status)
    print(response.read().decode("utf-8"))
```

## Reading History Back

The web app and Raspberry Pi can query history with:

- `GET /api/history?language=spanish`

Example:

```bash
curl "http://127.0.0.1:8000/api/history?language=spanish"
```

## Uploading A Real Image To The Server

The frontend no longer exposes manual image upload for users, but the backend supports server-side image upload for hardware or script-based flows.

Use this when the Pi captures a JPG and you want every machine to see the same file.

### HTTP Endpoint

- `POST /api/upload-image?entryId=<entry_id>&filename=<file_name>`

Send the raw JPG bytes in the request body.

### Example With Python On The Raspberry Pi

```python
from pathlib import Path
from urllib import parse, request


entry_id = "15"
image_path = Path("pumpkin.jpg")
endpoint = (
    "http://127.0.0.1:8000/api/upload-image?"
    f"entryId={parse.quote(entry_id)}&filename={parse.quote(image_path.name)}"
)

req = request.Request(
    endpoint,
    data=image_path.read_bytes(),
    headers={"Content-Type": "image/jpeg"},
    method="POST",
)

with request.urlopen(req) as response:
    print(response.status)
    print(response.read().decode("utf-8"))
```

The backend saves the file under `frontend/assets/uploads/` and updates the DB entry to point at the shared server path.

## Direct Python Store Access

If the Pi-side process runs in the same repo and you do not want to go through HTTP, you can call the store directly from Python.

This is acceptable for a single-device demo, but the API path is still cleaner because it matches how the frontend works.

Example:

```python
from backend.translation_store import TranslationStore


store = TranslationStore()

entry = store.create_entry(
    language_key="french",
    english="book",
    translated="livre",
    speech="livre",
    image="./assets/book.jpg",
    time_label="3:20 PM",
)

print(entry)
```

## When To Use `speech`

Set `speech` to the exact text that should be spoken by system voice playback.

Examples:

- Spanish `bola`
- Japanese `ボール`
- Chinese `球`
- Arabic `كُرَة`

Do not romanize languages that should stay in native script unless the TTS path specifically requires it.

## Image Field Guidance

For now, `image` should store a path or URL string that the frontend can display.

For the current single-device hackathon setup, acceptable values are:

- local frontend asset path such as `./assets/ball.svg`
- future local JPG path such as `./assets/captures/ball-001.jpg`
- `null` when no image is available yet

If the Raspberry Pi starts saving captured JPGs later, store the relative path that the frontend server can expose.

## Time Field Guidance

For now, `time` is a display label like:

- `2:42 PM`
- `3:15 PM`

If you want consistent formatting from the Pi side, generate it in Python before insert.

Example:

```python
from datetime import datetime

time_label = datetime.now().strftime("%-I:%M %p")
```

If `%-I` is not supported on a given platform, use:

```python
from datetime import datetime

time_label = datetime.now().strftime("%I:%M %p").lstrip("0")
```

## Minimal Pi Insert Workflow

A practical hardware-side flow is:

1. Camera or microphone captures input.
2. CV or STT pipeline returns an English label or phrase.
3. Translation step returns the target-language text.
4. The Pi creates an entry with:
   - source English text
   - translated text
   - speech text
   - image path
   - current time
5. The Pi POSTs the entry to `/api/history`.
6. The web app refreshes and displays the new item.

## Validation Rules

An insert will fail if these required fields are missing or empty:

Make sure the Pi always sends:

- non-empty `languageKey`
- non-empty `english`
- non-empty `translated`
- non-empty `speech`
- non-empty `time`

`image` may be omitted or set to `null`.

## Recommended Choice For LanGo

For the current hackathon scope, use the local API instead of direct SQLite writes.

Why:

- less coupling between hardware code and database code
- easier to debug with `curl`
- same path the frontend already depends on
- easy to replace later if you move from local SQLite to another database
