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

    def test_new_store_starts_without_demo_entries(self):
        for language_key in ("arabic", "chinese", "french", "japanese", "russian", "spanish"):
            self.assertEqual(self.store.list_entries(language_key), [])

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
        self.assertIsNotNone(created["createdAt"])
        self.assertEqual(created["languageKey"], "spanish")
        self.assertRegex(created["createdAt"], r"(Z|[+-]\d{2}:\d{2})$")

    def test_create_entry_dedups_existing_english_within_same_language(self):
        original = self.store.create_entry(
            "spanish",
            english="ball",
            translated="bola",
            speech="bola",
            image="./assets/ball.jpg",
            time_label="3:11 PM",
        )

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
        self.assertEqual(created["id"], original["id"])

    def test_find_entry_by_english_is_case_insensitive(self):
        self.store.create_entry(
            "japanese",
            english="ball",
            translated="ボール",
            speech="ボール",
            image="./assets/ball.jpg",
            time_label="3:14 PM",
        )
        found = self.store.find_entry_by_english("japanese", " BALL ")

        self.assertIsNotNone(found)
        self.assertEqual(found["translated"], "ボール")

    def test_create_entry_allows_none_image(self):
        created = self.store.create_entry(
            "russian",
            english="apple",
            translated="яблоко",
            speech="яблоко",
            image=None,
            time_label="3:18 PM",
        )

        entries = self.store.list_entries("russian")

        self.assertIsNone(created["image"])
        self.assertEqual(entries[0]["id"], created["id"])
        self.assertIsNone(entries[0]["image"])

    def test_missing_managed_image_is_serialized_as_none(self):
        created = self.store.create_entry(
            "spanish",
            english="keyboard",
            translated="teclado",
            speech="teclado",
            image="./assets/captures/missing-keyboard.png",
            time_label="3:19 PM",
        )

        entries = self.store.list_entries("spanish")

        self.assertIsNone(created["image"])
        self.assertIsNone(entries[0]["image"])

    def test_history_keeps_only_newest_ten_entries_per_language(self):
        for index in range(12):
            self.store.create_entry(
                "spanish",
                english=f"word-{index}",
                translated=f"translation-{index}",
                speech=f"translation-{index}",
                image=None,
                time_label=f"3:{index:02d} PM",
            )

        entries = self.store.list_entries("spanish")

        self.assertEqual(len(entries), 10)
        self.assertEqual(entries[0]["english"], "word-11")
        self.assertEqual(entries[-1]["english"], "word-2")

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
        self.assertRegex(created["createdAt"], r"(Z|[+-]\d{2}:\d{2})$")

    def test_existing_demo_entries_are_removed_on_store_init(self):
        db_path = Path(self.temp_dir.name) / "demo.db"
        connection = sqlite3.connect(db_path)
        connection.execute(
            """
            CREATE TABLE translation_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                language_key TEXT NOT NULL,
                english TEXT NOT NULL,
                translated TEXT NOT NULL,
                speech TEXT NOT NULL,
                image TEXT,
                time_label TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        connection.execute(
            """
            INSERT INTO translation_entries (
                language_key, english, translated, speech, image, time_label, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            ("japanese", "ball", "ボール", "ボール", "./assets/ball.svg", "2:42 PM", "2025-03-21 03:42:00"),
        )
        connection.execute(
            """
            INSERT INTO translation_entries (
                language_key, english, translated, speech, image, time_label, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            ("japanese", "custom", "カスタム", "カスタム", None, "4:00 PM", "2025-03-21 04:00:00"),
        )
        connection.commit()
        connection.close()

        cleaned_store = TranslationStore(db_path)
        entries = cleaned_store.list_entries("japanese")

        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["english"], "custom")
        self.assertEqual(entries[0]["createdAt"], "2025-03-21T04:00:00Z")

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

    def test_device_mode_defaults_to_learn(self):
        payload = self.store.get_device_mode()

        self.assertEqual(payload["selectedMode"], "learn")
        self.assertEqual(payload["modes"], ["learn", "game"])

    def test_set_device_mode_persists_mode(self):
        updated = self.store.set_device_mode("game")
        restored_store = TranslationStore(Path(self.temp_dir.name) / "test.db")
        restored = restored_store.get_device_mode()

        self.assertEqual(updated["selectedMode"], "game")
        self.assertEqual(restored["selectedMode"], "game")

    def test_set_device_mode_rejects_invalid_value(self):
        with self.assertRaises(ValueError):
            self.store.set_device_mode("arcade")


if __name__ == "__main__":
    unittest.main()
