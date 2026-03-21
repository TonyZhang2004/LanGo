import json
import mimetypes
import os
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from backend.groq_audio_translation import GroqAudioTranslator
from backend.translation_store import TranslationStore


ROOT_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = ROOT_DIR / "frontend"
HOST = "127.0.0.1"
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

        required_fields = ["languageKey", "english", "translated", "speech", "image", "time"]
        missing = [field for field in required_fields if not payload.get(field)]
        if missing:
            self._write_json(
                {"error": f"Missing required fields: {', '.join(missing)}"},
                status=HTTPStatus.BAD_REQUEST,
            )
            return

        entry = translation_store.create_entry(
            language_key=payload["languageKey"].strip().lower(),
            english=payload["english"].strip(),
            translated=payload["translated"].strip(),
            speech=payload["speech"].strip(),
            image=payload["image"].strip(),
            time_label=payload["time"].strip(),
        )
        self._write_json({"entry": entry}, status=HTTPStatus.CREATED)

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
