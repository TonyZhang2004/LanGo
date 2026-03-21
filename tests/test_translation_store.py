import sqlite3
import tempfile
import unittest
from pathlib import Path

from backend.translation_store import TranslationStore


class TranslationStoreDatabaseTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.store = TranslationStore(Path(self.temp_dir.name) / "test.db")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_seeded_entry_has_expected_database_fields(self):
        entry = self.store.list_entries("japanese")[0]

        self.assertEqual(entry["languageKey"], "japanese")
        self.assertEqual(entry["lang"], "ja-JP")
        self.assertIn("english", entry)
        self.assertIn("translated", entry)
        self.assertIn("speech", entry)
        self.assertIn("image", entry)
        self.assertIn("time", entry)

    def test_seeded_japanese_entries_use_native_script(self):
        entries = self.store.list_entries("japanese")
        translated_values = {entry["translated"] for entry in entries}

        self.assertIn("ボール", translated_values)
        self.assertIn("くつ", translated_values)

    def test_create_entry_inserts_and_returns_translation_entry(self):
        created = self.store.create_entry(
            "spanish",
            english="book",
            translated="libro",
            speech="libro",
            image="./assets/book.jpg",
            time_label="3:10 PM",
        )

        entries = self.store.list_entries("spanish")

        self.assertEqual(created["english"], "book")
        self.assertEqual(created["translated"], "libro")
        self.assertEqual(created["lang"], "es-ES")
        self.assertEqual(entries[0]["id"], created["id"])
        self.assertEqual(entries[0]["image"], "./assets/book.jpg")

    def test_create_entry_dedups_existing_english_within_same_language(self):
        before_entries = self.store.list_entries("spanish")

        created = self.store.create_entry(
            "spanish",
            english="ball",
            translated="otra-bola",
            speech="otra-bola",
            image="./assets/other-ball.jpg",
            time_label="3:12 PM",
        )

        after_entries = self.store.list_entries("spanish")

        self.assertEqual(len(after_entries), len(before_entries))
        self.assertEqual(created["english"], "ball")
        self.assertEqual(created["translated"], "bola")
        self.assertEqual(created["id"], before_entries[-1]["id"])

    def test_find_entry_by_english_is_case_insensitive(self):
        found = self.store.find_entry_by_english("japanese", " BALL ")

        self.assertIsNotNone(found)
        self.assertEqual(found["translated"], "ボール")

    def test_create_entry_allows_none_image(self):
        created = self.store.create_entry(
            "portuguese",
            english="apple",
            translated="maca",
            speech="maca",
            image=None,
            time_label="3:18 PM",
        )

        entries = self.store.list_entries("portuguese")

        self.assertIsNone(created["image"])
        self.assertEqual(entries[0]["id"], created["id"])
        self.assertIsNone(entries[0]["image"])

    def test_existing_database_schema_is_migrated_to_nullable_image(self):
        db_path = Path(self.temp_dir.name) / "legacy.db"
        connection = sqlite3.connect(db_path)
        connection.execute(
            """
            CREATE TABLE translation_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                language_key TEXT NOT NULL,
                english TEXT NOT NULL,
                translated TEXT NOT NULL,
                speech TEXT NOT NULL,
                image TEXT NOT NULL,
                time_label TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        connection.execute(
            """
            INSERT INTO translation_entries (
                language_key, english, translated, speech, image, time_label
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            ("spanish", "ball", "bola", "bola", "./assets/ball.svg", "2:42 PM"),
        )
        connection.commit()
        connection.close()

        migrated_store = TranslationStore(db_path)
        created = migrated_store.create_entry(
            "spanish",
            english="apple",
            translated="manzana",
            speech="manzana",
            image=None,
            time_label="3:20 PM",
        )

        self.assertIsNone(created["image"])

    def test_delete_entry_removes_inserted_translation_entry(self):
        created = self.store.create_entry(
            "french",
            english="apple",
            translated="pomme",
            speech="pomme",
            image="./assets/apple.jpg",
            time_label="3:15 PM",
        )

        deleted = self.store.delete_entry(created["id"])
        entries = self.store.list_entries("french")

        self.assertTrue(deleted)
        self.assertNotIn(created["id"], {entry["id"] for entry in entries})

    def test_delete_entry_returns_false_for_missing_entry(self):
        deleted = self.store.delete_entry("999999")

        self.assertFalse(deleted)


if __name__ == "__main__":
    unittest.main()
