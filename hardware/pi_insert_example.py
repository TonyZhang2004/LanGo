import json
import sys
from datetime import datetime
from urllib import error, request
from pathlib import Path
from urllib import error, parse, request

# Default is same-machine localhost. For another device on the same network,
# pass something like http://192.168.1.25:8000/api/history as argv[1].
SERVER_URL = "http://35.2.56.252:8001/api/history"
SERVER_BASE = "http://35.2.56.252:8001"

def current_time_label():
    return datetime.now().strftime("%I:%M %p").lstrip("0")


def build_entry():
    return {
        "languageKey": "japanese",
        "english": "ball",
        "translated": "ボール",
        "speech": "ボール",
        "image": None,
        "time": current_time_label(),
    }


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

def upload_image(entry_id, image_path, server_base=SERVER_BASE):
    file_path = "./hardware/" + image_path
    file_path = Path(file_path)
    endpoint = (
        f"{server_base}/api/upload-image?"
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
    
def main():
    entry = {
        "languageKey": "spanish",
        "english": "watermelon",
        "translated": "sandía",
        "speech": "sandía",
        "image": None,
        "time": current_time_label(),
    }

    server_url = SERVER_URL
    try:
        status, body = insert_entry(entry, server_url)
    except error.HTTPError as exc:
        print(f"Insert failed with HTTP {exc.code}")
        print(exc.read().decode("utf-8"))
        raise SystemExit(1) from exc
    except error.URLError as exc:
        print("Could not reach the LanGo server.")
        print(f"Checked URL: {server_url}")
        print("If this script is running on another computer, do not use 127.0.0.1 unless the server is running on that same computer.")
        print(str(exc.reason))
        raise SystemExit(1) from exc

    print(f"Inserted translation entry with HTTP {status}")
    print(body)

    data = json.loads(body)
    print(data["entry"]["id"])

    image_path = "watermelon.jpg"
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
    

if __name__ == "__main__":
    main()
