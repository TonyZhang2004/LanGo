const { useEffect, useState } = React;
const h = React.createElement;

const seedTranslations = {
  arabic: [],
  chinese: [],
  french: [],
  japanese: [],
  russian: [],
  spanish: [],
};

const languageNames = {
  arabic: "Arabic",
  chinese: "Mandarin Chinese",
  french: "French",
  japanese: "Japanese",
  russian: "Russian",
  spanish: "Spanish",
};
const languageLocales = {
  arabic: "ar-SA",
  chinese: "zh-CN",
  french: "fr-FR",
  japanese: "ja-JP",
  russian: "ru-RU",
  spanish: "es-ES",
};

const fallbackTranslations = seedTranslations;
const defaultImage = "./assets/no-image.svg";
const fullDateTimeFormatter = new Intl.DateTimeFormat([], {
  month: "long",
  day: "numeric",
  hour: "numeric",
  minute: "2-digit",
});

function formatFullDateTime(timestamp, fallbackTime) {
  if (timestamp) {
    const normalized = String(timestamp).includes("T") ? String(timestamp) : String(timestamp).replace(" ", "T");
    const parsed = new Date(normalized);
    if (!Number.isNaN(parsed.getTime())) {
      return fullDateTimeFormatter.format(parsed);
    }
  }

  if (!fallbackTime) {
    return "Unknown time";
  }

  const today = new Date();
  const dateLabel = new Intl.DateTimeFormat([], {
    month: "long",
    day: "numeric",
  }).format(today);
  return `${dateLabel} ${fallbackTime}`;
}

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
  let started = false;
  utterance.lang = lang;
  utterance.voice = matchingVoice;
  utterance.rate = 0.92;
  utterance.pitch = 1;
  utterance.onstart = () => {
    started = true;
    setAudioError("");
    setPlayingId(entryId);
  };
  utterance.onend = () => setPlayingId(null);
  utterance.onerror = (event) => {
    setPlayingId(null);
    if (event && event.error === "interrupted") {
      return;
    }
    if (started) {
      return;
    }
    setAudioError("Could not play browser audio.");
  };
  window.speechSynthesis.speak(utterance);
  return true;
}

function TranslationCard({ entry, isPlaying, isDeleting, onPlay, onDelete }) {
  const displayTime = formatFullDateTime(entry.createdAt, entry.time);
  return h(
    "article",
    { className: "history-card" },
    h(
      "div",
      { className: "thumb-wrap" },
      h("img", {
        className: `thumb ${entry.image ? "" : "thumb is-placeholder"}`.trim(),
        src: entry.image || defaultImage,
        alt: entry.image ? `${entry.english} translation item` : `${entry.english} translation item without image`,
        onError: (event) => {
          if (event.currentTarget.src.endsWith("/assets/no-image.svg")) {
            return;
          }
          event.currentTarget.src = defaultImage;
          event.currentTarget.className = "thumb is-placeholder";
        },
      })
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
    h("time", { className: "timestamp", dateTime: entry.createdAt || entry.time }, displayTime),
    h(
      "button",
      {
        className: "delete-button",
        type: "button",
        onClick: onDelete,
        disabled: isDeleting,
        "aria-label": `Delete translation history entry for ${entry.english}`,
      },
      isDeleting ? "Deleting..." : "Delete"
    )
  );
}

function App() {
  const [selectedLanguage, setSelectedLanguage] = useState("spanish");
  const [translationsByLanguage, setTranslationsByLanguage] = useState(fallbackTranslations);
  const [playingId, setPlayingId] = useState(null);
  const [deletingId, setDeletingId] = useState(null);
  const [lastSyncTime, setLastSyncTime] = useState("Not synced yet");
  const [audioError, setAudioError] = useState("");
  const [historyError, setHistoryError] = useState("");
  const [voiceNotice, setVoiceNotice] = useState("");
  const [syncNonce, setSyncNonce] = useState(0);

  const stampSyncTime = () => {
    setLastSyncTime(fullDateTimeFormatter.format(new Date()));
  };

  useEffect(() => {
    if (!("speechSynthesis" in window)) {
      setVoiceNotice("Browser speech synthesis is unavailable in this browser.");
      return undefined;
    }

    const updateVoiceNotice = () => {
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
          `Install a ${languageNames[selectedLanguage]} voice in your OS settings to enable playback.`
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
          stampSyncTime();
        }
      } catch (_error) {
        if (!cancelled) {
          setHistoryError("Showing fallback history because the database request failed.");
          setTranslationsByLanguage((current) => ({
            ...current,
            [selectedLanguage]: fallbackTranslations[selectedLanguage],
          }));
          stampSyncTime();
        }
      }
    }

    loadHistory();
    return () => {
      cancelled = true;
    };
  }, [selectedLanguage, syncNonce]);

  const entries = translationsByLanguage[selectedLanguage] || [];

  const handlePlayAudio = async (entry) => {
    setAudioError("");
    window.speechSynthesis?.cancel();

    setPlayingId(entry.id);
    speakWithBrowser(
      entry.speech,
      entry.lang || languageLocales[selectedLanguage],
      setPlayingId,
      entry.id,
      setAudioError
    );
  };

  const handleDeleteEntry = async (entry) => {
    const confirmed = window.confirm(
      `Delete this translation history entry?\n\n${entry.english} ↔ ${entry.translated}`
    );
    if (!confirmed) {
      return;
    }

    setHistoryError("");
    setDeletingId(entry.id);
    try {
      const response = await fetch(`/api/history?entryId=${encodeURIComponent(entry.id)}`, {
        method: "DELETE",
      });
      if (!response.ok) {
        throw new Error(`Delete request failed with status ${response.status}`);
      }
      setTranslationsByLanguage((current) => ({
        ...current,
        [selectedLanguage]: (current[selectedLanguage] || []).filter((item) => item.id !== entry.id),
      }));
      if (playingId === entry.id) {
        window.speechSynthesis?.cancel();
        setPlayingId(null);
      }
      stampSyncTime();
    } catch (_error) {
      setHistoryError("Could not delete translation entry.");
    } finally {
      setDeletingId(null);
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
        h("h1", null, "LanGo")
      ),
      h(
        "div",
        { className: "sync-panel" },
        h("p", { className: "sync-label" }, `Last synced at ${lastSyncTime}`),
        h(
          "button",
          {
            className: "sync-button",
            type: "button",
            onClick: () => setSyncNonce((count) => count + 1),
          },
          "Sync now"
        )
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
          h("span", null, "Time"),
          h("span", null, "Delete")
        ),
        h(
          "div",
          { className: "history-list" },
          ...entries.map((entry) =>
            h(TranslationCard, {
              key: entry.id,
              entry,
              isPlaying: playingId === entry.id,
              isDeleting: deletingId === entry.id,
              onPlay: () => handlePlayAudio(entry),
              onDelete: () => handleDeleteEntry(entry),
            })
          )
        )
      )
    )
  );
}

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(h(App));
