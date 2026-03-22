import base64
import json
from pathlib import Path
from urllib import request


SERVER_BASE = "http://35.3.62.156:8000"

def submit_detection(english, image=None, image_bytes=None, image_filename=None, language_key=None, server_base=SERVER_BASE):
    payload = {
        "english": english,
    }
    if image_bytes is not None:
        payload["imageFilename"] = image_filename or "capture.png"
        payload["imageBase64"] = base64.b64encode(image_bytes).decode("ascii")
    elif image:
        image_path = Path(image)
        if image_path.exists():
            payload["imageFilename"] = image_path.name
            payload["imageBase64"] = base64.b64encode(image_path.read_bytes()).decode("ascii")
        else:
            payload["image"] = image
    if language_key:
        payload["languageKey"] = language_key
    req = request.Request(
        f"{server_base}/api/detections",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with request.urlopen(req, timeout=10) as response:
        return response.status, json.loads(response.read().decode("utf-8"))


def get_selected_language(server_base=SERVER_BASE):
    with request.urlopen(f"{server_base}/api/device/language", timeout=10) as response:
        return response.status, json.loads(response.read().decode("utf-8"))


def set_selected_language(language_key, server_base=SERVER_BASE):
    payload = {"languageKey": language_key}
    req = request.Request(
        f"{server_base}/api/device/language",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with request.urlopen(req, timeout=10) as response:
        return response.status, json.loads(response.read().decode("utf-8"))


def list_pending(language_key=None, server_base=SERVER_BASE):
    suffix = f"?language={language_key}" if language_key else ""
    with request.urlopen(f"{server_base}/api/detections/pending{suffix}", timeout=10) as response:
        return response.status, json.loads(response.read().decode("utf-8"))


def get_history(language_key, server_base=SERVER_BASE):
    with request.urlopen(
        f"{server_base}/api/history?language={language_key}",
        timeout=10,
    ) as response:
        return response.status, json.loads(response.read().decode("utf-8"))


def confirm_pending(pending_id, server_base=SERVER_BASE):
    payload = {"pendingId": pending_id}
    req = request.Request(
        f"{server_base}/api/detections/confirm",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with request.urlopen(req, timeout=10) as response:
        return response.status, json.loads(response.read().decode("utf-8"))


def reject_pending(pending_id, server_base=SERVER_BASE):
    payload = {"pendingId": pending_id}
    req = request.Request(
        f"{server_base}/api/detections/reject",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with request.urlopen(req, timeout=10) as response:
        return response.status, json.loads(response.read().decode("utf-8"))
