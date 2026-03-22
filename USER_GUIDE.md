# LanGo User Guide

## Purpose

This guide explains how to run the LanGo repo locally, how to find the machine IP address, how to start the backend server, how to open the web UI, and how to run the Raspberry Pi screen app.

This guide is written for the current repo state.

## Repo Overview

Main parts of the project:

- [backend/server.py](/Users/tony/Desktop/LanGo/backend/server.py)
  Runs the HTTP server, frontend pages, detection endpoints, and translation history API.
- [pi_screen.py](/Users/tony/Desktop/LanGo/pi_screen.py)
  Native Tkinter UI for the Raspberry Pi screen.
- [object-detection.py](/Users/tony/Desktop/LanGo/object-detection.py)
  YOLO-based object detection client that submits pending detections to the backend.
- [frontend/index.html](/Users/tony/Desktop/LanGo/frontend/index.html)
  Main web app for translation history.
- [frontend/pi.html](/Users/tony/Desktop/LanGo/frontend/pi.html)
  Browser-based Pi control page.

## 1. Open The Repo

```bash
cd /Users/tony/Desktop/LanGo
```

## 2. Python Environment

If the virtual environment already exists:

```bash
source .venv/bin/activate
```

If it does not exist yet:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies if needed:

```bash
pip install groq opencv-python mediapipe ultralytics pygame gTTS
```

Note:

- Tkinter must also be available in the Python installation for `pi_screen.py`
- the repo does not currently use a locked `requirements.txt`

## 3. Find Your Machine IP Address

Use this when another laptop, Raspberry Pi, or phone needs to connect to your server over the local network.

### On macOS

Wi-Fi:

```bash
ipconfig getifaddr en0
```

If that returns nothing, try:

```bash
ipconfig getifaddr en1
```

### On Raspberry Pi / Linux

```bash
hostname -I
```

or:

```bash
ip addr
```

You are looking for a local/private IP like:

- `192.168.x.x`
- `10.x.x.x`
- `172.16.x.x` to `172.31.x.x`

## 4. Start The LanGo Server

### Localhost Only

Use this if you are running everything on one machine:

```bash
cd /Users/tony/Desktop/LanGo
HOST=127.0.0.1 PORT=8000 .venv/bin/python -m backend.server
```

### LAN / Shared Network Mode

Use this if another machine needs to connect:

```bash
cd /Users/tony/Desktop/LanGo
HOST=0.0.0.0 PORT=8000 .venv/bin/python -m backend.server
```

### Health Check

After starting the server:

```bash
curl http://127.0.0.1:8000/api/health
```

Expected result:

```json
{"status": "ok"}
```

## 5. Open The Web App

### On The Same Machine

Open the main history app:

- `http://127.0.0.1:8000`

Open the browser-based Pi control page:

- `http://127.0.0.1:8000/pi.html`

### On Another Machine On The Same Network

Replace `YOUR_LOCAL_IP` with the server machine's LAN IP:

- `http://YOUR_LOCAL_IP:8000`
- `http://YOUR_LOCAL_IP:8000/pi.html`

Example:

- `http://192.168.1.25:8000`

## 6. Run The Native Raspberry Pi Screen App

### Fullscreen Mode

This is the normal Raspberry Pi mode:

```bash
cd /Users/tony/Desktop/LanGo
.venv/bin/python pi_screen.py
```

### Fixed 3.5-Inch Simulation On Mac

This opens the Pi UI in a fixed `480x320` window:

```bash
cd /Users/tony/Desktop/LanGo
LANGO_PI_WINDOW_MODE=windowed .venv/bin/python pi_screen.py
```

This is the best way to simulate the Raspberry Pi 3.5-inch screen on a laptop.

## 7. Run Object Detection

The detector reads the selected device language from the backend and submits pending detections.

### Same Machine As Server

```bash
cd /Users/tony/Desktop/LanGo
LANGO_SERVER_BASE=http://127.0.0.1:8000 .venv/bin/python object-detection.py
```

### Detector On Another Machine

Replace the server base with the server machine IP:

```bash
cd /Users/tony/Desktop/LanGo
LANGO_SERVER_BASE=http://YOUR_LOCAL_IP:8000 .venv/bin/python object-detection.py
```

Example:

```bash
LANGO_SERVER_BASE=http://192.168.1.25:8000 .venv/bin/python object-detection.py
```

## 8. Typical Demo Flow

### Single-Machine Demo

1. Start the backend server:

```bash
HOST=127.0.0.1 PORT=8000 .venv/bin/python -m backend.server
```

2. In a second terminal, run the Pi screen:

```bash
.venv/bin/python pi_screen.py
```

3. In a third terminal, run detection:

```bash
LANGO_SERVER_BASE=http://127.0.0.1:8000 .venv/bin/python object-detection.py
```

4. Optional: open the web app in a browser:

- `http://127.0.0.1:8000`

### Mac Simulation Demo

1. Start the backend server:

```bash
HOST=127.0.0.1 PORT=8000 .venv/bin/python -m backend.server
```

2. Run the Pi screen in fixed `480x320` mode:

```bash
LANGO_PI_WINDOW_MODE=windowed .venv/bin/python pi_screen.py
```

3. Run detection:

```bash
LANGO_SERVER_BASE=http://127.0.0.1:8000 .venv/bin/python object-detection.py
```

## 9. If Another Person Needs To Connect

### Example: Friend Opens The Web UI From Another Laptop

On the server machine:

```bash
HOST=0.0.0.0 PORT=8000 .venv/bin/python -m backend.server
```

On the friend’s laptop, open:

- `http://YOUR_LOCAL_IP:8000`

### Example: Another Device Runs The Detector

On that device:

```bash
LANGO_SERVER_BASE=http://YOUR_LOCAL_IP:8000 .venv/bin/python object-detection.py
```

### Common Mistake

Do **not** use `127.0.0.1` from a different computer.

`127.0.0.1` always means “this computer,” not the server machine.

## 10. Ports

Default server port:

- `8000`

If `8000` is already in use:

```bash
HOST=127.0.0.1 PORT=8001 .venv/bin/python -m backend.server
```

Then use:

- `http://127.0.0.1:8001`

or:

- `http://YOUR_LOCAL_IP:8001`

## 11. Useful Commands

Show what is using port `8000`:

```bash
lsof -i :8000
```

Check the current selected device language:

```bash
curl http://127.0.0.1:8000/api/device/language
```

Check translation history for Spanish:

```bash
curl "http://127.0.0.1:8000/api/history?language=spanish"
```

Check pending detections for the currently selected language:

```bash
curl "http://127.0.0.1:8000/api/detections/pending?language=spanish"
```

## 12. Current Supported Languages

- Arabic
- Mandarin Chinese
- French
- Japanese
- Russian
- Spanish

Note:

- the Pi screen may display `Mandarin` instead of `Mandarin Chinese` to save space
- the backend still uses the canonical label `Mandarin Chinese`

## 13. Known Notes

- `pi_screen.py` is the intended native Raspberry Pi UI
- `frontend/pi.html` is still available as a browser-based control page
- the SQLite DB is local and is created/managed through the backend
- frontend uploaded images are stored under `frontend/assets/uploads/`
- pending detection captures are stored under `frontend/assets/captures/`

## 14. Quick Start Summary

Start server:

```bash
cd /Users/tony/Desktop/LanGo
HOST=127.0.0.1 PORT=8000 .venv/bin/python -m backend.server
```

Run Pi screen:

```bash
LANGO_PI_WINDOW_MODE=windowed .venv/bin/python pi_screen.py
```

Run detector:

```bash
LANGO_SERVER_BASE=http://127.0.0.1:8000 .venv/bin/python object-detection.py
```

Open browser:

- `http://127.0.0.1:8000`
