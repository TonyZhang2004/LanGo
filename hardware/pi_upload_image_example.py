import sys
from pathlib import Path
from urllib import error, parse, request


SERVER_BASE = "http://127.0.0.1:8000"


def upload_image(entry_id, image_path, server_base=SERVER_BASE):
    file_path = Path(image_path)
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
    if len(sys.argv) < 3:
        print("Usage: .venv/bin/python hardware/pi_upload_image_example.py <entry_id> <image_path> [server_base]")
        raise SystemExit(1)

    entry_id = sys.argv[1]
    image_path = sys.argv[2]
    server_base = sys.argv[3] if len(sys.argv) > 3 else SERVER_BASE

    try:
        status, body = upload_image(entry_id, image_path, server_base)
    except FileNotFoundError as exc:
        print(f"Image file not found: {image_path}")
        raise SystemExit(1) from exc
    except error.HTTPError as exc:
        print(f"Upload failed with HTTP {exc.code}")
        print(exc.read().decode("utf-8"))
        raise SystemExit(1) from exc
    except error.URLError as exc:
        print("Could not reach the LanGo server.")
        print(f"Checked URL: {server_base}")
        print(str(exc.reason))
        raise SystemExit(1) from exc

    print(f"Uploaded image with HTTP {status}")
    print(body)


if __name__ == "__main__":
    main()
