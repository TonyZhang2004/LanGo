import hashlib
import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

from groq import Groq


DEFAULT_API_KEY = "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"
DEFAULT_CACHE_DIR = Path(".cache/audio_translation")
DEFAULT_STT_MODEL = "whisper-large-v3"
DEFAULT_CHAT_MODEL = "openai/gpt-oss-20b"
DEFAULT_TTS_MODEL = "canopylabs/orpheus-v1-english"
DEFAULT_VOICE = "troy"
ARABIC_TTS_MODEL = "canopylabs/orpheus-arabic-saudi"
ARABIC_VOICE = "fahad"
SUPPORTED_GROQ_TTS_LANGUAGES = {"english", "arabic"}


@dataclass
class AudioTranslationResult:
    transcript: str
    translated_text: str
    audio_path: str
    from_cache: bool


class GroqAudioTranslator:
    def __init__(
        self,
        api_key=None,
        cache_dir=DEFAULT_CACHE_DIR,
        stt_model=DEFAULT_STT_MODEL,
        chat_model=DEFAULT_CHAT_MODEL,
        tts_model=DEFAULT_TTS_MODEL,
        voice=DEFAULT_VOICE,
    ):
        resolved_key = api_key or os.environ.get("GROQ_API_KEY") or DEFAULT_API_KEY
        self.client = Groq(api_key=resolved_key)
        self.cache_dir = Path(cache_dir)
        self.text_cache_dir = self.cache_dir / "text"
        self.audio_cache_dir = self.cache_dir / "audio"
        self.stt_model = stt_model
        self.chat_model = chat_model
        self.tts_model = tts_model
        self.voice = voice

        self.text_cache_dir.mkdir(parents=True, exist_ok=True)
        self.audio_cache_dir.mkdir(parents=True, exist_ok=True)

    def record_wav(self, seconds=4, sample_rate=16000):
        import sounddevice as sd
        from scipy.io.wavfile import write

        audio = sd.rec(int(seconds * sample_rate), samplerate=sample_rate, channels=1, dtype="int16")
        sd.wait()
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        write(tmp.name, sample_rate, audio)
        return tmp.name

    def transcribe(self, path):
        with open(path, "rb") as audio_file:
            result = self.client.audio.transcriptions.create(
                file=(os.path.basename(path), audio_file.read()),
                model=self.stt_model,
            )
        return result.text.strip()

    def translate_text(self, text, target_language, source_language="auto"):
        cache_key = self._cache_key(text=text, target_language=target_language, source_language=source_language)
        cached = self._read_text_cache(cache_key)
        if cached:
            return cached, True

        system_prompt = (
            "You are a translation engine for a language-learning app. "
            "Return only the translated phrase with no explanation."
        )
        user_prompt = (
            f"Translate the following text from {source_language} to {target_language}. "
            f"Text: {text}"
        )
        response = self.client.chat.completions.create(
            model=self.chat_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        translated = response.choices[0].message.content.strip()
        self._write_text_cache(cache_key, translated)
        return translated, False

    def synthesize_translation(self, translated_text, target_language):
        if not self.supports_groq_tts(target_language):
            raise ValueError(
                f"Groq TTS does not support {target_language}. "
                "Current Groq TTS support is limited to English and Arabic."
            )

        model, voice = self._tts_profile_for_language(target_language)
        cache_key = self._cache_key(
            text=translated_text,
            target_language=target_language,
            model=model,
            voice=voice,
        )
        audio_path = self.audio_cache_dir / f"{cache_key}.wav"
        if audio_path.exists():
            return str(audio_path), True

        audio = self.client.audio.speech.create(
            model=model,
            voice=voice,
            input=translated_text,
            response_format="wav",
        )
        audio.write_to_file(str(audio_path))
        return str(audio_path), False

    def speak_text(self, text, target_language):
        return self.synthesize_translation(text, target_language)

    def translate_audio(self, audio_path, target_language, source_language="auto"):
        transcript = self.transcribe(audio_path)
        translated_text, text_cache_hit = self.translate_text(
            transcript,
            target_language=target_language,
            source_language=source_language,
        )
        spoken_audio_path, audio_cache_hit = self.synthesize_translation(translated_text, target_language)
        return AudioTranslationResult(
            transcript=transcript,
            translated_text=translated_text,
            audio_path=spoken_audio_path,
            from_cache=text_cache_hit and audio_cache_hit,
        )

    def play_wav(self, path):
        import simpleaudio as sa

        wave_obj = sa.WaveObject.from_wave_file(path)
        play_obj = wave_obj.play()
        play_obj.wait_done()

    def _cache_key(self, **parts):
        serialized = json.dumps(parts, sort_keys=True, ensure_ascii=True)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def supports_groq_tts(self, target_language):
        normalized = str(target_language).strip().lower()
        return any(language in normalized for language in SUPPORTED_GROQ_TTS_LANGUAGES)

    def _tts_profile_for_language(self, target_language):
        normalized = str(target_language).strip().lower()
        if "arabic" in normalized:
            return ARABIC_TTS_MODEL, ARABIC_VOICE
        return self.tts_model, self.voice

    def _read_text_cache(self, cache_key):
        cache_path = self.text_cache_dir / f"{cache_key}.json"
        if not cache_path.exists():
            return None
        with open(cache_path, "r", encoding="utf-8") as cache_file:
            payload = json.load(cache_file)
        return payload["translated_text"]

    def _write_text_cache(self, cache_key, translated_text):
        cache_path = self.text_cache_dir / f"{cache_key}.json"
        payload = {"translated_text": translated_text}
        with open(cache_path, "w", encoding="utf-8") as cache_file:
            json.dump(payload, cache_file)
