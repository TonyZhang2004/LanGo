const { useEffect, useState } = React;

const seedTranslations = {
  arabic: [
    { id: "ball-ar", english: "ball", translated: "kura", time: "2:42 PM", image: "./assets/ball.svg", speech: "kura", lang: "ar-SA" },
    { id: "shoe-ar", english: "shoe", translated: "hitha", time: "2:45 PM", image: "./assets/shoe.svg", speech: "hitha", lang: "ar-SA" },
  ],
  bengali: [
    { id: "ball-bn", english: "ball", translated: "bol", time: "2:42 PM", image: "./assets/ball.svg", speech: "bol", lang: "bn-BD" },
    { id: "shoe-bn", english: "shoe", translated: "juto", time: "2:45 PM", image: "./assets/shoe.svg", speech: "juto", lang: "bn-BD" },
  ],
  chinese: [
    { id: "ball-zh", english: "ball", translated: "qiu", time: "2:42 PM", image: "./assets/ball.svg", speech: "qiu", lang: "zh-CN" },
    { id: "shoe-zh", english: "shoe", translated: "xiezi", time: "2:45 PM", image: "./assets/shoe.svg", speech: "xiezi", lang: "zh-CN" },
  ],
  french: [
    { id: "ball-fr", english: "ball", translated: "balle", time: "2:42 PM", image: "./assets/ball.svg", speech: "balle", lang: "fr-FR" },
    { id: "shoe-fr", english: "shoe", translated: "chaussure", time: "2:45 PM", image: "./assets/shoe.svg", speech: "chaussure", lang: "fr-FR" },
  ],
  hindi: [
    { id: "ball-hi", english: "ball", translated: "gend", time: "2:42 PM", image: "./assets/ball.svg", speech: "gend", lang: "hi-IN" },
    { id: "shoe-hi", english: "shoe", translated: "juta", time: "2:45 PM", image: "./assets/shoe.svg", speech: "juta", lang: "hi-IN" },
  ],
  indonesian: [
    { id: "ball-id", english: "ball", translated: "bola", time: "2:42 PM", image: "./assets/ball.svg", speech: "bola", lang: "id-ID" },
    { id: "shoe-id", english: "shoe", translated: "sepatu", time: "2:45 PM", image: "./assets/shoe.svg", speech: "sepatu", lang: "id-ID" },
  ],
  japanese: [
    { id: "ball-ja", english: "ball", translated: "booru", time: "2:42 PM", image: "./assets/ball.svg", speech: "booru", lang: "ja-JP" },
    { id: "shoe-ja", english: "shoe", translated: "kutsu", time: "2:45 PM", image: "./assets/shoe.svg", speech: "kutsu", lang: "ja-JP" },
  ],
  portuguese: [
    { id: "ball-pt", english: "ball", translated: "bola", time: "2:42 PM", image: "./assets/ball.svg", speech: "bola", lang: "pt-BR" },
    { id: "shoe-pt", english: "shoe", translated: "sapato", time: "2:45 PM", image: "./assets/shoe.svg", speech: "sapato", lang: "pt-BR" },
  ],
  russian: [
    { id: "ball-ru", english: "ball", translated: "myach", time: "2:42 PM", image: "./assets/ball.svg", speech: "myach", lang: "ru-RU" },
    { id: "shoe-ru", english: "shoe", translated: "botinok", time: "2:45 PM", image: "./assets/shoe.svg", speech: "botinok", lang: "ru-RU" },
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

function speakWord(text, lang, setPlayingId, entryId) {
  if (!("speechSynthesis" in window)) {
    window.alert("Speech playback is not supported in this browser.");
    return;
  }

  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = lang;
  utterance.onstart = () => setPlayingId(entryId);
  utterance.onend = () => setPlayingId(null);
  utterance.onerror = () => setPlayingId(null);
  window.speechSynthesis.speak(utterance);
}

function TranslationCard({ entry, isPlaying, onPlay, onUpload }) {
  return (
    <article className="history-card">
      <div className="thumb-wrap">
        <img className="thumb" src={entry.image} alt={`${entry.english} translation item`} />
        <label className="upload-chip">
          <input
            className="upload-input"
            type="file"
            accept=".jpg,.jpeg,image/jpeg"
            onChange={(event) => {
              const file = event.target.files?.[0];
              if (file) {
                onUpload(file);
              }
              event.target.value = "";
            }}
          />
          Upload JPG
        </label>
      </div>

      <p className="word english">{entry.english}</p>

      <div className="translation-cell">
        <span className="swap-mark" aria-hidden="true">
          ↔
        </span>
        <p className="word translated">{entry.translated}</p>
      </div>

      <button
        className={`audio-button ${isPlaying ? "is-playing" : ""}`}
        type="button"
        aria-label={`Play pronunciation for ${entry.translated}`}
        onClick={onPlay}
      >
        <span className="audio-icon" aria-hidden="true"></span>
      </button>

      <time className="timestamp" dateTime={entry.time}>
        {entry.time}
      </time>
    </article>
  );
}

function App() {
  const [selectedLanguage, setSelectedLanguage] = useState("spanish");
  const [translationsByLanguage, setTranslationsByLanguage] = useState(seedTranslations);
  const [playingId, setPlayingId] = useState(null);
  const [username, setUsername] = useState("Username");
  const [connectionState, setConnectionState] = useState("Raspberry Pi connected");

  useEffect(() => {
    const timeoutId = window.setTimeout(() => {
      setConnectionState("Web app synced with Raspberry Pi");
    }, 1200);

    return () => window.clearTimeout(timeoutId);
  }, []);

  const entries = translationsByLanguage[selectedLanguage];

  const handleImageUpload = (entryId, file) => {
    const objectUrl = URL.createObjectURL(file);

    setTranslationsByLanguage((current) => ({
      ...current,
      [selectedLanguage]: current[selectedLanguage].map((entry) =>
        entry.id === entryId ? { ...entry, image: objectUrl } : entry
      ),
    }));
  };

  return (
    <div className="page-shell">
      <header className="topbar">
        <div className="brand-block">
          <p className="eyebrow">Language Companion</p>
          <h1>LanGo</h1>
          <p className="sync-pill">{connectionState}</p>
        </div>

        <button
          className="profile-chip"
          type="button"
          aria-label="Edit profile name"
          onClick={() => {
            const nextName = window.prompt("Enter a profile name", username);
            if (nextName && nextName.trim()) {
              setUsername(nextName.trim());
            }
          }}
        >
          <span className="profile-avatar" aria-hidden="true">
            {username.slice(0, 1).toUpperCase()}
          </span>
          <span className="profile-name">{username}</span>
        </button>
      </header>

      <main className="content">
        <section className="controls-panel">
          <div className="section-heading">
            <p className="section-kicker">Preferences</p>
            <h2>Language</h2>
          </div>

          <label className="language-picker" htmlFor="language-select">
            <span className="sr-only">Select target language</span>
            <select
              id="language-select"
              name="language"
              value={selectedLanguage}
              onChange={(event) => {
                setSelectedLanguage(event.target.value);
                setPlayingId(null);
                window.speechSynthesis?.cancel();
              }}
            >
              {Object.entries(languageNames).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
            <span className="picker-icon" aria-hidden="true">
              ⌄
            </span>
          </label>
        </section>

        <section className="history-panel" aria-labelledby="history-heading">
          <div className="section-heading history-header">
            <p className="section-kicker">Session Log</p>
            <h2 id="history-heading">Translation History</h2>
            <p className="history-meta">
              Showing {entries.length} items in {languageNames[selectedLanguage]}
            </p>
          </div>

          <div className="history-columns" aria-hidden="true">
            <span>Image</span>
            <span>English</span>
            <span>Translation</span>
            <span>Audio</span>
            <span>Time</span>
          </div>

          <div className="history-list">
            {entries.map((entry) => (
              <TranslationCard
                key={entry.id}
                entry={entry}
                isPlaying={playingId === entry.id}
                onPlay={() => speakWord(entry.speech, entry.lang, setPlayingId, entry.id)}
                onUpload={(file) => handleImageUpload(entry.id, file)}
              />
            ))}
          </div>
        </section>
      </main>
    </div>
  );
}

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(<App />);
