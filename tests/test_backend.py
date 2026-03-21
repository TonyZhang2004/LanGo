import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from backend.groq_audio_translation import GroqAudioTranslator
from backend.server import resolve_tts_provider
from backend.translation_store import TranslationStore


class TranslationStoreTests(unittest.TestCase):
    def test_seeded_japanese_entries_use_native_script(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = TranslationStore(Path(temp_dir) / "test.db")
            entries = store.list_entries("japanese")
            translated_values = {entry["translated"] for entry in entries}

        self.assertIn("ボール", translated_values)
        self.assertIn("くつ", translated_values)

    def test_seeded_entries_include_language_locale(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = TranslationStore(Path(temp_dir) / "test.db")
            entry = store.list_entries("japanese")[0]

        self.assertEqual(entry["lang"], "ja-JP")


class TranslatorSupportTests(unittest.TestCase):
    def test_supported_groq_tts_languages_are_explicit(self):
        translator = GroqAudioTranslator()
        self.assertTrue(translator.supports_groq_tts("Arabic"))
        self.assertFalse(translator.supports_groq_tts("Japanese"))


class ServerLogicTests(unittest.TestCase):
    def test_japanese_tts_requests_browser_fallback(self):
        payload = resolve_tts_provider("japanese")
        self.assertEqual(payload["provider"], "browser")
        self.assertIn("Japanese", payload["details"])

    def test_arabic_tts_uses_groq(self):
        payload = resolve_tts_provider("arabic")
        self.assertEqual(payload["provider"], "groq")
        self.assertEqual(payload["targetLanguage"], "Arabic")


if __name__ == "__main__":
    unittest.main()
