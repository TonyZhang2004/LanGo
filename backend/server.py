import json
import mimetypes
import os
import re
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from uuid import uuid4

from backend.groq_audio_translation import GroqAudioTranslator
from backend.translation_store import TranslationStore


ROOT_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = ROOT_DIR / "frontend"
UPLOADS_DIR = FRONTEND_DIR / "assets" / "uploads"
HOST = os.environ.get("HOST", "127.0.0.1").strip() or "127.0.0.1"
PORT = int(os.environ.get("PORT", "8000"))
translator = GroqAudioTranslator()
translation_store = TranslationStore()


LANGUAGE_CODES = {
    "arabic": "Arabic",
    "bengali": "Bengali",
    "chinese": "Mandarin Chinese",
    "french": "French",
    "hindi": "Hindi",
    "indonesian": "Indonesian",
    "japanese": "Japanese",
    "portuguese": "Portuguese",
    "russian": "Russian",
    "spanish": "Spanish",
}


def resolve_target_language(language_key):
    normalized = (language_key or "spanish").strip().lower()
    return LANGUAGE_CODES.get(normalized, normalized or "Spanish")


def resolve_tts_provider(language_key):
    target_language = resolve_target_language(language_key)
    if translator.supports_groq_tts(target_language):
        return {"provider": "groq", "targetLanguage": target_language}
    return {
        "provider": "browser",
        "targetLanguage": target_language,
        "details": f"Groq TTS currently supports English and Arabic only, not {target_language}.",
    }


def build_uploaded_image_path(entry_id, filename):
    original_name = Path(filename or "capture.jpg").name
    stem = re.sub(r"[^a-zA-Z0-9_-]+", "-", Path(original_name).stem).strip("-") or "capture"
    suffix = Path(original_name).suffix.lower()
    if suffix not in {".jpg", ".jpeg", ".png"}:
        suffix = ".jpg"
    final_name = f"{entry_id}-{stem}-{uuid4().hex[:8]}{suffix}"
    return f"./assets/uploads/{final_name}", UPLOADS_DIR / final_name


def save_uploaded_image(entry_id, filename, payload_bytes):
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    image_path, file_path = build_uploaded_image_path(entry_id, filename)
    file_path.write_bytes(payload_bytes)
    return image_path, file_path


def resolve_uploaded_image_file(image_path):
    if not image_path or not str(image_path).startswith("./assets/uploads/"):
        return None
    relative_path = str(image_path).removeprefix("./")
    return FRONTEND_DIR / relative_path


class LanGoHandler(SimpleHTTPRequestHandler):
    def translate_path(self, path):
        parsed = urlparse(path)
        request_path = parsed.path
        if request_path in {"", "/"}:
            return str(FRONTEND_DIR / "index.html")
        if request_path.startswith("/frontend/"):
            request_path = request_path[len("/frontend") :]
        safe_path = request_path.lstrip("/")
        return str(FRONTEND_DIR / safe_path)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/health":
            self._write_json({"status": "ok"})
            return
        if parsed.path == "/api/history":
            self._handle_history_get(parsed)
            return
        if parsed.path == "/api/tts":
            self._handle_tts(parsed)
            return
        return super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/history":
            self._handle_history_post()
            return
        if parsed.path == "/api/upload-image":
            self._handle_upload_image(parsed)
            return
        self._write_json({"error": "Not found."}, status=HTTPStatus.NOT_FOUND)

    def do_DELETE(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/history":
            self._handle_history_delete(parsed)
            return
        self._write_json({"error": "Not found."}, status=HTTPStatus.NOT_FOUND)

    def _handle_history_get(self, parsed):
        params = parse_qs(parsed.query)
        language_key = params.get("language", ["spanish"])[0].strip().lower()
        entries = translation_store.list_entries(language_key)
        self._write_json({"entries": entries})

    def _handle_history_post(self):
        content_length = int(self.headers.get("Content-Length", "0"))
        if content_length <= 0:
            self._write_json({"error": "Missing request body."}, status=HTTPStatus.BAD_REQUEST)
            return

        try:
            payload = json.loads(self.rfile.read(content_length).decode("utf-8"))
        except json.JSONDecodeError:
            self._write_json({"error": "Request body must be valid JSON."}, status=HTTPStatus.BAD_REQUEST)
            return

        required_fields = ["languageKey", "english", "translated", "speech", "time"]
        missing = [field for field in required_fields if not payload.get(field)]
        if missing:
            self._write_json(
                {"error": f"Missing required fields: {', '.join(missing)}"},
                status=HTTPStatus.BAD_REQUEST,
            )
            return

        language_key = payload["languageKey"].strip().lower()
        english = payload["english"].strip()
        existing_entry = translation_store.find_entry_by_english(language_key, english)
        if existing_entry:
            self._write_json(
                {"entry": existing_entry, "created": False, "dedupedOn": "english"},
                status=HTTPStatus.OK,
            )
            return

        entry = translation_store.create_entry(
            language_key=language_key,
            english=english,
            translated=payload["translated"].strip(),
            speech=payload["speech"].strip(),
            image=payload.get("image"),
            time_label=payload["time"].strip(),
        )
        self._write_json({"entry": entry, "created": True}, status=HTTPStatus.CREATED)

    def _handle_upload_image(self, parsed):
        params = parse_qs(parsed.query)
        entry_id = params.get("entryId", [""])[0].strip()
        filename = params.get("filename", ["capture.jpg"])[0].strip()
        content_length = int(self.headers.get("Content-Length", "0"))

        if not entry_id:
            self._write_json({"error": "Missing entryId parameter."}, status=HTTPStatus.BAD_REQUEST)
            return
        if content_length <= 0:
            self._write_json({"error": "Missing image body."}, status=HTTPStatus.BAD_REQUEST)
            return

        payload_bytes = self.rfile.read(content_length)
        image_path, file_path = save_uploaded_image(entry_id, filename, payload_bytes)
        entry = translation_store.update_entry_image(entry_id, image_path)
        if not entry:
            file_path.unlink(missing_ok=True)
            self._write_json({"error": "Translation entry not found."}, status=HTTPStatus.NOT_FOUND)
            return

        self._write_json({"entry": entry, "image": image_path}, status=HTTPStatus.OK)

    def _handle_history_delete(self, parsed):
        params = parse_qs(parsed.query)
        entry_id = params.get("entryId", [""])[0].strip()
        if not entry_id:
            self._write_json({"error": "Missing entryId parameter."}, status=HTTPStatus.BAD_REQUEST)
            return

        entry = translation_store.get_entry(entry_id)
        if not entry:
            self._write_json({"error": "Translation entry not found."}, status=HTTPStatus.NOT_FOUND)
            return

        image_file = resolve_uploaded_image_file(entry.get("image"))
        deleted = translation_store.delete_entry(entry_id)
        if not deleted:
            self._write_json({"error": "Translation entry not found."}, status=HTTPStatus.NOT_FOUND)
            return

        if image_file:
            image_file.unlink(missing_ok=True)

        self._write_json({"deleted": True, "entryId": entry_id}, status=HTTPStatus.OK)

    def _handle_tts(self, parsed):
        params = parse_qs(parsed.query)
        text = params.get("text", [""])[0].strip()
        language_key = params.get("language", ["spanish"])[0].strip().lower()
        tts_resolution = resolve_tts_provider(language_key)
        target_language = tts_resolution["targetLanguage"]

        if not text:
            self._write_json({"error": "Missing text parameter."}, status=HTTPStatus.BAD_REQUEST)
            return

        if tts_resolution["provider"] != "groq":
            self._write_json(
                {
                    "error": "Unsupported Groq TTS language.",
                    "details": tts_resolution["details"],
                    "fallback": "browser",
                },
                status=HTTPStatus.BAD_REQUEST,
            )
            return

        try:
            audio_path, cache_hit = translator.speak_text(text=text, target_language=target_language)
        except Exception as exc:
            error_text = str(exc)
            if "model_terms_required" in error_text or "requires terms acceptance" in error_text:
                self._write_json(
                    {
                        "error": "Groq TTS terms not accepted for this model.",
                        "details": error_text,
                        "fallback": "browser",
                    },
                    status=HTTPStatus.BAD_REQUEST,
                )
                return
            self._write_json(
                {"error": "Failed to synthesize audio.", "details": error_text},
                status=HTTPStatus.BAD_GATEWAY,
            )
            return

        audio_file = Path(audio_path)
        if not audio_file.exists():
            self._write_json(
                {"error": "Audio file was not created."},
                status=HTTPStatus.INTERNAL_SERVER_ERROR,
            )
            return

        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "audio/wav")
        self.send_header("Content-Length", str(audio_file.stat().st_size))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Cache-Hit", "1" if cache_hit else "0")
        self.end_headers()

        with open(audio_file, "rb") as audio_stream:
            self.wfile.write(audio_stream.read())

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        super().end_headers()

    def log_message(self, format, *args):
        return

    def guess_type(self, path):
        guessed = mimetypes.guess_type(path)[0]
        if guessed:
            return guessed
        return "application/octet-stream"

    def _write_json(self, payload, status=HTTPStatus.OK):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def run():
    try:
        server = ThreadingHTTPServer((HOST, PORT), LanGoHandler)
    except OSError as exc:
        if exc.errno == 48:
            raise OSError(
                f"Port {PORT} is already in use. Run with a different port, for example: "
                f"`PORT=8001 .venv/bin/python -m backend.server`"
            ) from exc
        raise

    print(f"LanGo server running at http://{HOST}:{PORT}")
    print("Serving frontend and Groq-backed TTS audio from one process.")
    server.serve_forever()


if __name__ == "__main__":
    run()
