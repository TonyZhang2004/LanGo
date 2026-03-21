import subprocess
import unittest
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent


class FrontendSmokeTests(unittest.TestCase):
    def test_frontend_script_has_valid_javascript_syntax(self):
        result = subprocess.run(
            ["node", "--check", "frontend/script.js"],
            cwd=ROOT_DIR,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)

    def test_index_html_uses_local_frontend_script_without_babel(self):
        html = (ROOT_DIR / "frontend" / "index.html").read_text(encoding="utf-8")
        self.assertIn('<div id="root"></div>', html)
        self.assertIn('<script src="./script.js"></script>', html)
        self.assertNotIn("text/babel", html)
        self.assertNotIn("@babel/standalone", html)

    def test_frontend_uses_browser_speech_instead_of_backend_tts_fetch(self):
        script = (ROOT_DIR / "frontend" / "script.js").read_text(encoding="utf-8")
        self.assertIn("SpeechSynthesisUtterance", script)
        self.assertNotIn("/api/tts", script)
        self.assertNotIn("Groq TTS", script)

    def test_frontend_ignores_interrupted_browser_tts_errors(self):
        script = (ROOT_DIR / "frontend" / "script.js").read_text(encoding="utf-8")
        self.assertIn('event && event.error === "interrupted"', script)
        self.assertIn("let started = false;", script)

    def test_frontend_uses_sync_button_instead_of_profile_component(self):
        script = (ROOT_DIR / "frontend" / "script.js").read_text(encoding="utf-8")
        styles = (ROOT_DIR / "frontend" / "styles.css").read_text(encoding="utf-8")
        self.assertIn("Last synced at", script)
        self.assertIn("Sync now", script)
        self.assertNotIn("profile-chip", script)
        self.assertIn(".sync-button", styles)


if __name__ == "__main__":
    unittest.main()
