import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
DB_PATH = DATA_DIR / "lango.db"
FRONTEND_DIR = ROOT_DIR / "frontend"
MAX_HISTORY_ENTRIES = 10
LANGUAGE_LOCALES = {
    "arabic": "ar-SA",
    "chinese": "zh-CN",
    "french": "fr-FR",
    "japanese": "ja-JP",
    "russian": "ru-RU",
    "spanish": "es-ES",
}


DEMO_ENTRIES = {
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
                    image TEXT,
                    time_label TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_at_local TEXT
                )
                """
            )
            self._migrate_nullable_image_column(connection)
            self._migrate_created_at_local_column(connection)
            self._remove_demo_entries(connection)
            self._enforce_all_language_limits(connection)
            connection.commit()

    def _migrate_nullable_image_column(self, connection):
        columns = connection.execute("PRAGMA table_info(translation_entries)").fetchall()
        image_column = next((column for column in columns if column["name"] == "image"), None)
        if not image_column or image_column["notnull"] == 0:
            return

        connection.execute("ALTER TABLE translation_entries RENAME TO translation_entries_old")
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
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_at_local TEXT
            )
            """
        )
        connection.execute(
            """
            INSERT INTO translation_entries (
                id, language_key, english, translated, speech, image, time_label, created_at, created_at_local
            )
            SELECT
                id, language_key, english, translated, speech, image, time_label, created_at, NULL
            FROM translation_entries_old
            """
        )
        connection.execute("DROP TABLE translation_entries_old")

    def _migrate_created_at_local_column(self, connection):
        columns = connection.execute("PRAGMA table_info(translation_entries)").fetchall()
        column_names = {column["name"] for column in columns}
        if "created_at_local" not in column_names:
            connection.execute("ALTER TABLE translation_entries ADD COLUMN created_at_local TEXT")

        connection.execute(
            """
            UPDATE translation_entries
            SET created_at_local = replace(created_at, ' ', 'T') || 'Z'
            WHERE created_at_local IS NULL
              AND created_at IS NOT NULL
            """
        )

    def _remove_demo_entries(self, connection):
        for language_key, entries in DEMO_ENTRIES.items():
            for entry in entries:
                connection.execute(
                    """
                    DELETE FROM translation_entries
                    WHERE language_key = ?
                      AND english = ?
                      AND translated = ?
                      AND speech = ?
                      AND image = ?
                      AND time_label = ?
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

    def _enforce_all_language_limits(self, connection):
        rows = connection.execute(
            """
            SELECT DISTINCT language_key
            FROM translation_entries
            """
        ).fetchall()
        for row in rows:
            self._enforce_language_limit(connection, row["language_key"])

    def _enforce_language_limit(self, connection, language_key):
        connection.execute(
            """
            DELETE FROM translation_entries
            WHERE language_key = ?
              AND id IN (
                  SELECT id
                  FROM translation_entries
                  WHERE language_key = ?
                  ORDER BY id DESC
                  LIMIT -1 OFFSET ?
              )
            """,
            (language_key, language_key, MAX_HISTORY_ENTRIES),
        )

    def list_entries(self, language_key):
        with closing(self._connect()) as connection:
            rows = connection.execute(
                """
                SELECT id, language_key, english, translated, speech, image, time_label, created_at, created_at_local
                FROM translation_entries
                WHERE language_key = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (language_key, MAX_HISTORY_ENTRIES),
            ).fetchall()
        return [self._serialize_row(row) for row in rows]

    def find_entry_by_english(self, language_key, english):
        with closing(self._connect()) as connection:
            row = connection.execute(
                """
                SELECT id, language_key, english, translated, speech, image, time_label, created_at, created_at_local
                FROM translation_entries
                WHERE language_key = ?
                  AND lower(trim(english)) = lower(trim(?))
                ORDER BY id DESC
                LIMIT 1
                """,
                (language_key, english),
            ).fetchone()
        return self._serialize_row(row) if row else None

    def get_entry(self, entry_id):
        with closing(self._connect()) as connection:
            row = connection.execute(
                """
                SELECT id, language_key, english, translated, speech, image, time_label, created_at, created_at_local
                FROM translation_entries
                WHERE id = ?
                """,
                (entry_id,),
            ).fetchone()
        return self._serialize_row(row) if row else None

    def create_entry(self, language_key, english, translated, speech, image, time_label):
        existing = self.find_entry_by_english(language_key, english)
        if existing:
            return existing

        image_value = self._normalize_image(image)
        local_now = self._machine_local_now()
        effective_time_label = time_label or local_now.strftime("%I:%M %p").lstrip("0")

        with closing(self._connect()) as connection:
            cursor = connection.execute(
                """
                INSERT INTO translation_entries (
                    language_key, english, translated, speech, image, time_label, created_at_local
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (language_key, english, translated, speech, image_value, effective_time_label, local_now.isoformat(timespec="seconds")),
            )
            self._enforce_language_limit(connection, language_key)
            row = connection.execute(
                """
                SELECT id, language_key, english, translated, speech, image, time_label, created_at, created_at_local
                FROM translation_entries
                WHERE id = ?
                """,
                (cursor.lastrowid,),
            ).fetchone()
            connection.commit()
        return self._serialize_row(row)

    def update_entry_image(self, entry_id, image):
        image_value = self._normalize_image(image)
        with closing(self._connect()) as connection:
            connection.execute(
                "UPDATE translation_entries SET image = ? WHERE id = ?",
                (image_value, entry_id),
            )
            row = connection.execute(
                """
                SELECT id, language_key, english, translated, speech, image, time_label, created_at, created_at_local
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

    def _normalize_image(self, image):
        if image is None:
            return None
        image_text = str(image).strip()
        return image_text or None

    def _serialize_image(self, image):
        image_value = self._normalize_image(image)
        if not image_value:
            return None

        relative_path = image_value.removeprefix("./")
        if relative_path.startswith("assets/uploads/") or relative_path.startswith("assets/captures/"):
            file_path = FRONTEND_DIR / relative_path
            if not file_path.exists():
                return None
        return image_value

    def _machine_local_now(self):
        return datetime.now().astimezone()

    def _serialize_created_at(self, row):
        if row["created_at_local"]:
            return row["created_at_local"]
        if row["created_at"]:
            return str(row["created_at"]).replace(" ", "T") + "Z"
        return None

    def _serialize_row(self, row):
        return {
            "id": str(row["id"]),
            "languageKey": row["language_key"],
            "english": row["english"],
            "translated": row["translated"],
            "speech": row["speech"],
            "lang": LANGUAGE_LOCALES.get(row["language_key"]),
            "image": self._serialize_image(row["image"]),
            "time": row["time_label"],
            "createdAt": self._serialize_created_at(row),
        }
