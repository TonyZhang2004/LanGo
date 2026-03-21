from backend.groq_audio_translation import GroqAudioTranslator

if __name__ == "__main__":
    translator = GroqAudioTranslator()
    wav_path = translator.record_wav()
    result = translator.translate_audio(wav_path, target_language="Spanish")

    print("Transcript:", result.transcript)
    print("Translation:", result.translated_text)
    print("Audio file:", result.audio_path)
    print("Cache hit:", result.from_cache)

    translator.play_wav(result.audio_path)
