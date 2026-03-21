import sqlite3
from contextlib import closing
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
DB_PATH = DATA_DIR / "lango.db"
LANGUAGE_LOCALES = {
    "arabic": "ar-SA",
    "chinese": "zh-CN",
    "french": "fr-FR",
    "japanese": "ja-JP",
    "portuguese": "pt-BR",
    "russian": "ru-RU",
    "spanish": "es-ES",
}


SEED_ENTRIES = {
    "arabic": [
        {"english": "ball", "translated": "كُرَة", "speech": "كُرَة", "image": "./assets/ball.svg", "time": "2:42 PM"},
        {"english": "shoe", "translated": "حِذَاء", "speech": "حِذَاء", "image": "./assets/shoe.svg", "time": "2:45 PM"},
    ],
    "chinese": [
        {"english": "ball", "translated": "球", "speech": "球", "image": "./assets/ball.svg", "time": "2:42 PM"},
        {"english": "shoe", "translated": "鞋子", "speech": "鞋子", "image": "./assets/shoe.svg", "time": "2:45 PM"},
    ],
    "french": [
        {"english": "ball", "translated": "balle", "speech": "balle", "image": "./assets/ball.svg", "time": "2:42 PM"},
        {"english": "shoe", "translated": "chaussure", "speech": "chaussure", "image": "./assets/shoe.svg", "time": "2:45 PM"},
    ],
    "japanese": [
        {"english": "ball", "translated": "ボール", "speech": "ボール", "image": "./assets/ball.svg", "time": "2:42 PM"},
        {"english": "shoe", "translated": "くつ", "speech": "くつ", "image": "./assets/shoe.svg", "time": "2:45 PM"},
    ],
    "portuguese": [
        {"english": "ball", "translated": "bola", "speech": "bola", "image": "./assets/ball.svg", "time": "2:42 PM"},
        {"english": "shoe", "translated": "sapato", "speech": "sapato", "image": "./assets/shoe.svg", "time": "2:45 PM"},
    ],
    "russian": [
        {"english": "ball", "translated": "мяч", "speech": "мяч", "image": "./assets/ball.svg", "time": "2:42 PM"},
        {"english": "shoe", "translated": "ботинок", "speech": "ботинок", "image": "./assets/shoe.svg", "time": "2:45 PM"},
    ],
    "spanish": [
        {"english": "ball", "translated": "bola", "speech": "bola", "image": "./assets/ball.svg", "time": "2:42 PM"},
        {"english": "shoe", "translated": "zapato", "speech": "zapato", "image": "./assets/shoe.svg", "time": "2:45 PM"},
    ],
}


class TranslationStore:
    def __init__(self, db_path=DB_PATH):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self):
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self):
        with closing(self._connect()) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS translation_entries (
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
            count = connection.execute("SELECT COUNT(*) AS total FROM translation_entries").fetchone()["total"]
            if count == 0:
                self._seed(connection)
            connection.commit()

    def _seed(self, connection):
        for language_key, entries in SEED_ENTRIES.items():
            for entry in entries:
                connection.execute(
                    """
                    INSERT INTO translation_entries (
                        language_key, english, translated, speech, image, time_label
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        language_key,
                        entry["english"],
                        entry["translated"],
                        entry["speech"],
                        entry["image"],
                        entry["time"],
                    ),
                )

    def list_entries(self, language_key):
        with closing(self._connect()) as connection:
            rows = connection.execute(
                """
                SELECT id, language_key, english, translated, speech, image, time_label
                FROM translation_entries
                WHERE language_key = ?
                ORDER BY id DESC
                """,
                (language_key,),
            ).fetchall()
        return [self._serialize_row(row) for row in rows]

    def create_entry(self, language_key, english, translated, speech, image, time_label):
        with closing(self._connect()) as connection:
            cursor = connection.execute(
                """
                INSERT INTO translation_entries (
                    language_key, english, translated, speech, image, time_label
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (language_key, english, translated, speech, image, time_label),
            )
            row = connection.execute(
                """
                SELECT id, language_key, english, translated, speech, image, time_label
                FROM translation_entries
                WHERE id = ?
                """,
                (cursor.lastrowid,),
            ).fetchone()
            connection.commit()
        return self._serialize_row(row)

    def update_entry_image(self, entry_id, image):
        with closing(self._connect()) as connection:
            connection.execute(
                "UPDATE translation_entries SET image = ? WHERE id = ?",
                (image, entry_id),
            )
            row = connection.execute(
                """
                SELECT id, language_key, english, translated, speech, image, time_label
                FROM translation_entries
                WHERE id = ?
                """,
                (entry_id,),
            ).fetchone()
            connection.commit()
        return self._serialize_row(row) if row else None

    def delete_entry(self, entry_id):
        with closing(self._connect()) as connection:
            cursor = connection.execute(
                "DELETE FROM translation_entries WHERE id = ?",
                (entry_id,),
            )
            connection.commit()
        return cursor.rowcount > 0

    def _serialize_row(self, row):
        return {
            "id": str(row["id"]),
            "languageKey": row["language_key"],
            "english": row["english"],
            "translated": row["translated"],
            "speech": row["speech"],
            "lang": LANGUAGE_LOCALES.get(row["language_key"]),
            "image": row["image"],
            "time": row["time_label"],
        }
