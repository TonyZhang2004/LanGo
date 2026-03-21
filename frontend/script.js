const { useEffect, useRef, useState } = React;
const h = React.createElement;

const seedTranslations = {
  arabic: [
    { id: "ball-ar", english: "ball", translated: "كُرَة", time: "2:42 PM", image: "./assets/ball.svg", speech: "كُرَة", lang: "ar-SA" },
    { id: "shoe-ar", english: "shoe", translated: "حِذَاء", time: "2:45 PM", image: "./assets/shoe.svg", speech: "حِذَاء", lang: "ar-SA" },
  ],
  bengali: [
    { id: "ball-bn", english: "ball", translated: "বল", time: "2:42 PM", image: "./assets/ball.svg", speech: "বল", lang: "bn-BD" },
    { id: "shoe-bn", english: "shoe", translated: "জুতা", time: "2:45 PM", image: "./assets/shoe.svg", speech: "জুতা", lang: "bn-BD" },
  ],
  chinese: [
    { id: "ball-zh", english: "ball", translated: "球", time: "2:42 PM", image: "./assets/ball.svg", speech: "球", lang: "zh-CN" },
    { id: "shoe-zh", english: "shoe", translated: "鞋子", time: "2:45 PM", image: "./assets/shoe.svg", speech: "鞋子", lang: "zh-CN" },
  ],
  french: [
    { id: "ball-fr", english: "ball", translated: "balle", time: "2:42 PM", image: "./assets/ball.svg", speech: "balle", lang: "fr-FR" },
    { id: "shoe-fr", english: "shoe", translated: "chaussure", time: "2:45 PM", image: "./assets/shoe.svg", speech: "chaussure", lang: "fr-FR" },
  ],
  hindi: [
    { id: "ball-hi", english: "ball", translated: "गेंद", time: "2:42 PM", image: "./assets/ball.svg", speech: "गेंद", lang: "hi-IN" },
    { id: "shoe-hi", english: "shoe", translated: "जूता", time: "2:45 PM", image: "./assets/shoe.svg", speech: "जूता", lang: "hi-IN" },
  ],
  indonesian: [
    { id: "ball-id", english: "ball", translated: "bola", time: "2:42 PM", image: "./assets/ball.svg", speech: "bola", lang: "id-ID" },
    { id: "shoe-id", english: "shoe", translated: "sepatu", time: "2:45 PM", image: "./assets/shoe.svg", speech: "sepatu", lang: "id-ID" },
  ],
  japanese: [
    { id: "ball-ja", english: "ball", translated: "ボール", time: "2:42 PM", image: "./assets/ball.svg", speech: "ボール", lang: "ja-JP" },
    { id: "shoe-ja", english: "shoe", translated: "くつ", time: "2:45 PM", image: "./assets/shoe.svg", speech: "くつ", lang: "ja-JP" },
  ],
  portuguese: [
    { id: "ball-pt", english: "ball", translated: "bola", time: "2:42 PM", image: "./assets/ball.svg", speech: "bola", lang: "pt-BR" },
    { id: "shoe-pt", english: "shoe", translated: "sapato", time: "2:45 PM", image: "./assets/shoe.svg", speech: "sapato", lang: "pt-BR" },
  ],
  russian: [
    { id: "ball-ru", english: "ball", translated: "мяч", time: "2:42 PM", image: "./assets/ball.svg", speech: "мяч", lang: "ru-RU" },
    { id: "shoe-ru", english: "shoe", translated: "ботинок", time: "2:45 PM", image: "./assets/shoe.svg", speech: "ботинок", lang: "ru-RU" },
  ],
  spanish: [
    { id: "ball-es", english: "ball", translated: "bola", time: "2:42 PM", image: "./assets/ball.svg", speech: "bola", lang: "es-ES" },
    { id: "shoe-es", english: "shoe", translated: "zapato", time: "2:45 PM", image: "./assets/shoe.svg", speech: "zapato", lang: "es-ES" },
  ],
};

const languageNames = {
  arabic: "Arabic",
  bengali: "Bengali",
  chinese: "Mandarin Chinese",
  french: "French",
  hindi: "Hindi",
  indonesian: "Indonesian",
  japanese: "Japanese",
  portuguese: "Portuguese",
  russian: "Russian",
  spanish: "Spanish",
};
const languageLocales = {
  arabic: "ar-SA",
  bengali: "bn-BD",
  chinese: "zh-CN",
  french: "fr-FR",
  hindi: "hi-IN",
  indonesian: "id-ID",
  japanese: "ja-JP",
  portuguese: "pt-BR",
  russian: "ru-RU",
  spanish: "es-ES",
};

const fallbackTranslations = seedTranslations;
const groqTtsLanguages = new Set(["arabic"]);

function findVoiceForLang(lang) {
  if (!("speechSynthesis" in window)) {
    return null;
  }

  const normalized = String(lang).toLowerCase();
  const base = normalized.split("-")[0];
  const voices = window.speechSynthesis.getVoices();

  return (
    voices.find((voice) => voice.lang.toLowerCase() === normalized) ||
    voices.find((voice) => voice.lang.toLowerCase().startsWith(`${base}-`)) ||
    null
  );
}

function speakWithBrowser(text, lang, setPlayingId, entryId, setAudioError) {
  if (!("speechSynthesis" in window)) {
    setAudioError("Speech playback is not supported in this browser.");
    return false;
  }

  const matchingVoice = findVoiceForLang(lang);
  if (!matchingVoice) {
    setAudioError(`No browser voice is installed for ${lang}. Install that language voice in your OS/browser settings.`);
    setPlayingId(null);
    return false;
  }

  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = lang;
  utterance.voice = matchingVoice;
  utterance.rate = 0.92;
  utterance.pitch = 1;
  utterance.onstart = () => setPlayingId(entryId);
  utterance.onend = () => setPlayingId(null);
  utterance.onerror = () => {
    setPlayingId(null);
    setAudioError("Could not play browser audio.");
  };
  window.speechSynthesis.speak(utterance);
  return true;
}

function TranslationCard({ entry, isPlaying, onPlay, onUpload }) {
  return h(
    "article",
    { className: "history-card" },
    h(
      "div",
      { className: "thumb-wrap" },
      h("img", {
        className: "thumb",
        src: entry.image,
        alt: `${entry.english} translation item`,
      }),
      h(
        "label",
        { className: "upload-chip" },
        h("input", {
          className: "upload-input",
          type: "file",
          accept: ".jpg,.jpeg,image/jpeg",
          onChange: (event) => {
            const file = event.target.files && event.target.files[0];
            if (file) {
              onUpload(file);
            }
            event.target.value = "";
          },
        }),
        "Upload JPG"
      )
    ),
    h("p", { className: "word english" }, entry.english),
    h(
      "div",
      { className: "translation-cell" },
      h("span", { className: "swap-mark", "aria-hidden": "true" }, "↔"),
      h("p", { className: "word translated" }, entry.translated)
    ),
    h(
      "button",
      {
        className: `audio-button ${isPlaying ? "is-playing" : ""}`,
        type: "button",
        "aria-label": `Play pronunciation for ${entry.translated}`,
        onClick: onPlay,
      },
      h("span", { className: "audio-icon", "aria-hidden": "true" })
    ),
    h("time", { className: "timestamp", dateTime: entry.time }, entry.time)
  );
}

function App() {
  const [selectedLanguage, setSelectedLanguage] = useState("spanish");
  const [translationsByLanguage, setTranslationsByLanguage] = useState(fallbackTranslations);
  const [playingId, setPlayingId] = useState(null);
  const [username, setUsername] = useState("Username");
  const [connectionState, setConnectionState] = useState("Raspberry Pi connected");
  const [audioError, setAudioError] = useState("");
  const [historyError, setHistoryError] = useState("");
  const [voiceNotice, setVoiceNotice] = useState("");
  const audioRef = useRef(null);

  useEffect(() => {
    const timeoutId = window.setTimeout(() => {
      setConnectionState("Web app synced with Raspberry Pi");
    }, 1200);
    return () => window.clearTimeout(timeoutId);
  }, []);

  useEffect(() => {
    return () => {
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current = null;
      }
    };
  }, []);

  useEffect(() => {
    if (!("speechSynthesis" in window)) {
      setVoiceNotice("Browser speech synthesis is unavailable in this browser.");
      return undefined;
    }

    const updateVoiceNotice = () => {
      if (groqTtsLanguages.has(selectedLanguage)) {
        setVoiceNotice("");
        return;
      }

      const currentEntries = translationsByLanguage[selectedLanguage] || fallbackTranslations[selectedLanguage] || [];
      const sampleEntry = currentEntries[0];
      if (!sampleEntry) {
        setVoiceNotice("");
        return;
      }

      const languageLocale = sampleEntry.lang || languageLocales[selectedLanguage];
      const voice = findVoiceForLang(languageLocale);
      if (voice) {
        setVoiceNotice("");
      } else {
        setVoiceNotice(
          `${languageNames[selectedLanguage]} audio needs a local browser/system voice. ` +
          `Groq TTS currently only supports English and Arabic, so ${languageNames[selectedLanguage]} falls back to your installed device voice.`
        );
      }
    };

    updateVoiceNotice();
    window.speechSynthesis.onvoiceschanged = updateVoiceNotice;
    return () => {
      window.speechSynthesis.onvoiceschanged = null;
    };
  }, [selectedLanguage, translationsByLanguage]);

  useEffect(() => {
    let cancelled = false;

    async function loadHistory() {
      setHistoryError("");
      try {
        const response = await fetch(`/api/history?language=${encodeURIComponent(selectedLanguage)}`);
        if (!response.ok) {
          throw new Error(`History request failed with status ${response.status}`);
        }
        const payload = await response.json();
        if (!cancelled) {
          setTranslationsByLanguage((current) => ({
            ...current,
            [selectedLanguage]: payload.entries,
          }));
        }
      } catch (_error) {
        if (!cancelled) {
          setHistoryError("Showing fallback history because the database request failed.");
          setTranslationsByLanguage((current) => ({
            ...current,
            [selectedLanguage]: fallbackTranslations[selectedLanguage],
          }));
        }
      }
    }

    loadHistory();
    return () => {
      cancelled = true;
    };
  }, [selectedLanguage]);

  const entries = translationsByLanguage[selectedLanguage] || [];

  const handleImageUpload = (entryId, file) => {
    const objectUrl = URL.createObjectURL(file);
    setTranslationsByLanguage((current) => ({
      ...current,
      [selectedLanguage]: (current[selectedLanguage] || []).map((entry) =>
        entry.id === entryId ? { ...entry, image: objectUrl } : entry
      ),
    }));
  };

  const handlePlayAudio = async (entry) => {
    setAudioError("");

    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
    }

    setPlayingId(entry.id);

    if (!groqTtsLanguages.has(selectedLanguage)) {
      speakWithBrowser(
        entry.speech,
        entry.lang || languageLocales[selectedLanguage],
        setPlayingId,
        entry.id,
        setAudioError
      );
      return;
    }

    try {
      const params = new URLSearchParams({
        text: entry.speech,
        language: selectedLanguage,
      });
      const response = await fetch(`/api/tts?${params.toString()}`);

      if (!response.ok) {
        let fallback = false;
        let message = `Audio request failed with status ${response.status}`;
        try {
          const payload = await response.json();
          if (payload.details) {
            message = payload.details;
          } else if (payload.error) {
            message = payload.error;
          }
          if (payload.fallback === "browser") {
            fallback = true;
          }
        } catch (_error) {
          // Keep fallback status if body is not JSON.
        }
        if (fallback) {
          setPlayingId(null);
          speakWithBrowser(
            entry.speech,
            entry.lang || languageLocales[selectedLanguage],
            setPlayingId,
            entry.id,
            setAudioError
          );
          return;
        }
        throw new Error(message);
      }

      const audioBlob = await response.blob();
      const audioUrl = URL.createObjectURL(audioBlob);
      const audio = new Audio(audioUrl);
      audioRef.current = audio;

      audio.onended = () => {
        URL.revokeObjectURL(audioUrl);
        if (audioRef.current === audio) {
          audioRef.current = null;
        }
        setPlayingId(null);
      };

      audio.onerror = () => {
        URL.revokeObjectURL(audioUrl);
        if (audioRef.current === audio) {
          audioRef.current = null;
        }
        setPlayingId(null);
        setAudioError("Could not play backend audio.");
      };

      await audio.play();
    } catch (error) {
      setPlayingId(null);
      setAudioError(error.message || "Could not load Groq audio from the backend.");
    }
  };

  return h(
    "div",
    { className: "page-shell" },
    h(
      "header",
      { className: "topbar" },
      h(
        "div",
        { className: "brand-block" },
        h("p", { className: "eyebrow" }, "Language Companion"),
        h("h1", null, "LanGo"),
        h("p", { className: "sync-pill" }, connectionState)
      ),
      h(
        "button",
        {
          className: "profile-chip",
          type: "button",
          "aria-label": "Edit profile name",
          onClick: () => {
            const nextName = window.prompt("Enter a profile name", username);
            if (nextName && nextName.trim()) {
              setUsername(nextName.trim());
            }
          },
        },
        h("span", { className: "profile-avatar", "aria-hidden": "true" }, username.slice(0, 1).toUpperCase()),
        h("span", { className: "profile-name" }, username)
      )
    ),
    h(
      "main",
      { className: "content" },
      h(
        "section",
        { className: "controls-panel" },
        h(
          "div",
          { className: "section-heading" },
          h("p", { className: "section-kicker" }, "Preferences"),
          h("h2", null, "Language")
        ),
        h(
          "label",
          { className: "language-picker", htmlFor: "language-select" },
          h("span", { className: "sr-only" }, "Select target language"),
          h(
            "select",
            {
              id: "language-select",
              name: "language",
              value: selectedLanguage,
              onChange: (event) => {
                setSelectedLanguage(event.target.value);
                setPlayingId(null);
                if (window.speechSynthesis) {
                  window.speechSynthesis.cancel();
                }
              },
            },
            ...Object.entries(languageNames).map(([value, label]) =>
              h("option", { key: value, value }, label)
            )
          ),
          h("span", { className: "picker-icon", "aria-hidden": "true" }, "⌄")
        )
      ),
      h(
        "section",
        { className: "history-panel", "aria-labelledby": "history-heading" },
        h(
          "div",
          { className: "section-heading history-header" },
          h("p", { className: "section-kicker" }, "Session Log"),
          h("h2", { id: "history-heading" }, "Translation History"),
          h("p", { className: "history-meta" }, `Showing ${entries.length} items in ${languageNames[selectedLanguage]}`),
          voiceNotice ? h("p", { className: "audio-error" }, voiceNotice) : null,
          historyError ? h("p", { className: "audio-error" }, historyError) : null,
          audioError ? h("p", { className: "audio-error" }, audioError) : null
        ),
        h(
          "div",
          { className: "history-columns", "aria-hidden": "true" },
          h("span", null, "Image"),
          h("span", null, "English"),
          h("span", null, "Translation"),
          h("span", null, "Audio"),
          h("span", null, "Time")
        ),
        h(
          "div",
          { className: "history-list" },
          ...entries.map((entry) =>
            h(TranslationCard, {
              key: entry.id,
              entry,
              isPlaying: playingId === entry.id,
              onPlay: () => handlePlayAudio(entry),
              onUpload: (file) => handleImageUpload(entry.id, file),
            })
          )
        )
      )
    )
  );
}

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(h(App));
