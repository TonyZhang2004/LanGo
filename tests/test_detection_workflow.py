import tempfile
import unittest
from pathlib import Path

from backend.detection_workflow import DetectionWorkflow
from backend.translation_store import TranslationStore


class FakeTranslator:
    def translate_text(self, text, target_language, source_language="English"):
        return f"{target_language}:{text}", False


class DetectionWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.workflow = DetectionWorkflow(translator=FakeTranslator())
        self.temp_dir = tempfile.TemporaryDirectory()
        self.store = TranslationStore(Path(self.temp_dir.name) / "test.db")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_submit_detection_creates_pending_translation(self):
        pending, created = self.workflow.submit_detection(
            language_key="spanish",
            english="apple",
            image="./assets/captures/apple.jpg",
        )

        self.assertTrue(created)
        self.assertEqual(pending["languageKey"], "spanish")
        self.assertEqual(pending["english"], "apple")
        self.assertEqual(pending["translated"], "Spanish:apple")

    def test_submit_detection_dedups_pending_english_per_language(self):
        original, _ = self.workflow.submit_detection("spanish", "apple", "./assets/captures/apple-1.jpg")
        duplicate, created = self.workflow.submit_detection("spanish", "apple", "./assets/captures/apple-2.jpg")

        self.assertFalse(created)
        self.assertEqual(duplicate["pendingId"], original["pendingId"])

    def test_confirm_pending_moves_entry_into_history(self):
        pending, _ = self.workflow.submit_detection("japanese", "bottle", "./assets/captures/bottle.jpg")

        entry = self.workflow.confirm_pending(pending["pendingId"], self.store)

        self.assertEqual(entry["english"], "bottle")
        self.assertEqual(self.store.list_entries("japanese")[0]["id"], entry["id"])
        self.assertEqual(self.workflow.list_pending("japanese"), [])

    def test_reject_pending_removes_pending_entry(self):
        pending, _ = self.workflow.submit_detection("french", "book", None)

        rejected = self.workflow.reject_pending(pending["pendingId"])

        self.assertEqual(rejected["english"], "book")
        self.assertEqual(self.workflow.list_pending("french"), [])


if __name__ == "__main__":
    unittest.main()
