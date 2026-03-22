import json
from urllib import request


SERVER_BASE = "http://127.0.0.1:8000"


def submit_detection(english, image=None, language_key=None, server_base=SERVER_BASE):
    payload = {
        "english": english,
        "image": image,
    }
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
