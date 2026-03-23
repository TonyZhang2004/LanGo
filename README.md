# LanGo

LanGo is a hackathon prototype for an interactive language-learning headset in the Education track. The current prototype uses a Raspberry Pi terminal, a YOLO-based object-detection loop, a native Pi touchscreen UI, and a companion web app that shows confirmed translation history.

## What It Does

- detects objects from a camera feed
- translates detected words into the selected target language
- lets the user confirm or discard detections on the Raspberry Pi screen
- stores confirmed translations in SQLite
- displays translation history in the web app
- supports `learn` and `game` device modes

## Architecture

The main parts of the system are:

- [backend/server.py](/Users/tony/Desktop/LanGo/backend/server.py)
  Runs the HTTP API, serves the frontend, exposes device language/mode state, and owns the confirmation/history flow.
- [backend/translation_store.py](/Users/tony/Desktop/LanGo/backend/translation_store.py)
  Stores translation history and device mode in SQLite at `data/lango.db`.
- [object-detection.py](/Users/tony/Desktop/LanGo/object-detection.py)
  Runs camera-based detection and switches between `learn()` and `game()` based on the persisted device mode.
- [pi_screen.py](/Users/tony/Desktop/LanGo/pi_screen.py)
  Native Raspberry Pi touchscreen UI for language selection, mode switching, and pending detection confirmation.
- [frontend/index.html](/Users/tony/Desktop/LanGo/frontend/index.html)
  Web app for viewing translation history.

## Quick Start

### 1. Create and activate a virtual environment

```bash
cd /Users/tony/Desktop/LanGo
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install groq opencv-python mediapipe ultralytics pygame gTTS
```

Notes:

- `tkinter` must be available in your Python install for [pi_screen.py](/Users/tony/Desktop/LanGo/pi_screen.py)
- this repo does not currently include a locked `requirements.txt`

### 3. Start the backend

Local-only:

```bash
HOST=127.0.0.1 PORT=8000 .venv/bin/python -m backend.server
```

LAN mode for other devices:

```bash
HOST=0.0.0.0 PORT=8000 .venv/bin/python -m backend.server
```

### 4. Open the web app

On the same machine:

- `http://127.0.0.1:8000`

On another device on the same network:

- `http://YOUR_LOCAL_IP:8000`

### 5. Run the native Pi screen

Fullscreen:

```bash
.venv/bin/python pi_screen.py
```

Mac simulation for a `480x320` 3.5-inch Pi screen:

```bash
LANGO_PI_WINDOW_MODE=windowed .venv/bin/python pi_screen.py
```

The Pi UI now starts the detector process automatically and defaults runtime mode to `learn`.

## Common Commands

Get your local IP on macOS:

```bash
ipconfig getifaddr en0
```

Health check:

```bash
curl http://127.0.0.1:8000/api/health
```

Kill whatever is using port `8000`:

```bash
lsof -ti :8000 | xargs kill -9
```

## Repo Docs

- [USER_GUIDE.md](/Users/tony/Desktop/LanGo/USER_GUIDE.md)
  Full setup and run instructions.
- [SYSTEM_DESIGN.md](/Users/tony/Desktop/LanGo/SYSTEM_DESIGN.md)
  High-level system design and architecture.
- [HARDWARE_DATABASE.md](/Users/tony/Desktop/LanGo/HARDWARE_DATABASE.md)
  How the Pi/backend interaction writes into the shared DB.
- [HARDWARE_PI_INTEGRATION.md](/Users/tony/Desktop/LanGo/HARDWARE_PI_INTEGRATION.md)
  Pi-side API contract for teammate handoff.

## Current Demo Flow

1. Start the backend server.
2. Launch the Pi screen.
3. Let the detector queue an object as a pending translation.
4. Save or discard it on the Pi touchscreen.
5. View the confirmed entry in the web app history.

## Status

LanGo is a hackathon-stage prototype optimized for live demo flow, not production deployment.
