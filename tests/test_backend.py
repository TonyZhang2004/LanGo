import json
import tempfile
import subprocess
import unittest
from pathlib import Path

from backend.groq_audio_translation import GroqAudioTranslator
from backend.server import build_uploaded_image_path, resolve_tts_provider, save_uploaded_image


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

    def test_uploaded_image_path_is_server_relative_and_sanitized(self):
        image_path, file_path = build_uploaded_image_path("15", "pumpkin photo.JPG")

        self.assertTrue(image_path.startswith("./assets/uploads/15-pumpkin-photo-"))
        self.assertEqual(file_path.suffix, ".jpg")

    def test_save_uploaded_image_writes_bytes_to_disk(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_uploads = Path(temp_dir)
            from unittest.mock import patch

            with patch("backend.server.UPLOADS_DIR", temp_uploads):
                image_path, file_path = save_uploaded_image("22", "pumpkin.jpg", b"jpg-bytes")
                self.assertTrue(image_path.startswith("./assets/uploads/"))
                self.assertTrue(file_path.exists())
                self.assertEqual(file_path.read_bytes(), b"jpg-bytes")


if __name__ == "__main__":
    unittest.main()
