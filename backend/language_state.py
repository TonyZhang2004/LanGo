import json
from pathlib import Path
from threading import Lock


ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
STATE_PATH = DATA_DIR / "device_language.json"
DEFAULT_LANGUAGE_KEY = "spanish"
SUPPORTED_LANGUAGES = {
    "arabic": {"label": "Arabic", "locale": "ar-SA"},
    "chinese": {"label": "Mandarin Chinese", "locale": "zh-CN"},
    "french": {"label": "French", "locale": "fr-FR"},
    "japanese": {"label": "Japanese", "locale": "ja-JP"},
    "portuguese": {"label": "Portuguese", "locale": "pt-BR"},
    "russian": {"label": "Russian", "locale": "ru-RU"},
    "spanish": {"label": "Spanish", "locale": "es-ES"},
}


def normalize_language_key(language_key):
    normalized = str(language_key or DEFAULT_LANGUAGE_KEY).strip().lower()
    if normalized not in SUPPORTED_LANGUAGES:
        raise ValueError(
            "Unsupported languageKey. Expected one of: "
            + ", ".join(sorted(SUPPORTED_LANGUAGES))
        )
    return normalized


def language_options():
    return [
        {
            "key": key,
            "label": value["label"],
            "locale": value["locale"],
        }
        for key, value in SUPPORTED_LANGUAGES.items()
    ]


class DeviceLanguageState:
    def __init__(self, state_path=STATE_PATH):
        self.state_path = Path(state_path)
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()
        self._ensure_state_file()

    def get_selected_language(self):
        with self._lock:
            payload = self._read_state()
        return self._serialize(payload["languageKey"])

    def set_selected_language(self, language_key):
        normalized = normalize_language_key(language_key)
        with self._lock:
            self._write_state({"languageKey": normalized})
        return self._serialize(normalized)

    def _ensure_state_file(self):
        if self.state_path.exists():
            try:
                payload = self._read_state()
                normalize_language_key(payload.get("languageKey"))
                return
            except (json.JSONDecodeError, OSError, ValueError, TypeError):
                pass
        self._write_state({"languageKey": DEFAULT_LANGUAGE_KEY})

    def _read_state(self):
        with open(self.state_path, "r", encoding="utf-8") as state_file:
            return json.load(state_file)

    def _write_state(self, payload):
        with open(self.state_path, "w", encoding="utf-8") as state_file:
            json.dump(payload, state_file)

    def _serialize(self, language_key):
        language = SUPPORTED_LANGUAGES[language_key]
        return {
            "selectedLanguage": {
                "key": language_key,
                "label": language["label"],
                "locale": language["locale"],
            },
            "languages": language_options(),
        }
