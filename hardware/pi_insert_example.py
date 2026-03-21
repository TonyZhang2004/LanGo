import json
import sys
from datetime import datetime
from urllib import error, request


# Default is same-machine localhost. For another device on the same network,
# pass something like http://192.168.1.25:8000/api/history as argv[1].
SERVER_URL = "http://127.0.0.1:8000/api/history"


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


def insert_entry(server_url=SERVER_URL):
    payload = build_entry()
    req = request.Request(
        server_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with request.urlopen(req, timeout=10) as response:
        body = response.read().decode("utf-8")
        return response.status, body


def main():
    server_url = sys.argv[1] if len(sys.argv) > 1 else SERVER_URL
    try:
        status, body = insert_entry(server_url)
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


if __name__ == "__main__":
    main()
