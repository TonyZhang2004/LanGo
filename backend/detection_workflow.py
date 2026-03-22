import hashlib
from datetime import datetime


TARGET_LANGUAGE_NAMES = {
    "arabic": "Arabic",
    "chinese": "Mandarin Chinese",
    "french": "French",
    "japanese": "Japanese",
    "russian": "Russian",
    "spanish": "Spanish",
}


class DetectionWorkflow:
    def __init__(self, translator, max_pending_per_language=5):
        self.translator = translator
        self.max_pending_per_language = max_pending_per_language
        self._pending = {}

    def list_pending(self, language_key=None):
        if language_key:
            return list(self._pending.get(language_key, []))

        pending = []
        for entries in self._pending.values():
            pending.extend(entries)
        return pending

    def submit_detection(self, language_key, english, image=None):
        normalized_language = str(language_key or "spanish").strip().lower()
        normalized_english = str(english or "").strip()
        if not normalized_english:
            raise ValueError("english is required")

        existing = self._find_pending(normalized_language, normalized_english)
        if existing:
            if image and not existing.get("image"):
                existing["image"] = image
            return existing, False

        target_language = TARGET_LANGUAGE_NAMES.get(normalized_language, normalized_language.title())
        translated, _ = self.translator.translate_text(normalized_english, target_language=target_language, source_language="English")
        pending_entry = {
            "pendingId": self._pending_id(normalized_language, normalized_english),
            "languageKey": normalized_language,
            "english": normalized_english,
            "translated": translated,
            "speech": translated,
            "image": image,
            "createdAt": datetime.now().astimezone().isoformat(timespec="seconds"),
        }

        language_queue = self._pending.setdefault(normalized_language, [])
        language_queue.insert(0, pending_entry)
        del language_queue[self.max_pending_per_language :]
        return pending_entry, True

    def confirm_pending(self, pending_id, store):
        pending_entry = self._pop_pending(pending_id)
        if not pending_entry:
            return None

        created_entry = store.create_entry(
            language_key=pending_entry["languageKey"],
            english=pending_entry["english"],
            translated=pending_entry["translated"],
            speech=pending_entry["speech"],
            image=pending_entry.get("image"),
            time_label="",
        )
        return created_entry

    def reject_pending(self, pending_id):
        pending_entry = self._pop_pending(pending_id)
        return pending_entry

    def _find_pending(self, language_key, english):
        normalized_english = english.strip().lower()
        for entry in self._pending.get(language_key, []):
            if entry["english"].strip().lower() == normalized_english:
                return entry
        return None

    def _pop_pending(self, pending_id):
        for language_key, entries in self._pending.items():
            for index, entry in enumerate(entries):
                if entry["pendingId"] == pending_id:
                    return entries.pop(index)
        return None

    def _pending_id(self, language_key, english):
        digest = hashlib.sha1(f"{language_key}:{english}".encode("utf-8")).hexdigest()
        return digest[:12]
