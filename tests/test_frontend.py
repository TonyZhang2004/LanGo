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


if __name__ == "__main__":
    unittest.main()
