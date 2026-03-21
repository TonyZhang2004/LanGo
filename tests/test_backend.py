import json
import subprocess
import unittest

from backend.groq_audio_translation import GroqAudioTranslator
from backend.server import resolve_tts_provider


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
