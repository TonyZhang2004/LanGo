const selectedLanguageElement = document.getElementById("selected-language");
const statusMessageElement = document.getElementById("status-message");
const languageGridElement = document.getElementById("language-grid");
const refreshButtonElement = document.getElementById("refresh-button");

let selectedLanguageKey = "";
let languages = [];
let refreshTimerId = null;

function setStatus(message, tone = "") {
  statusMessageElement.textContent = message;
  statusMessageElement.className = "status";
  if (tone) {
    statusMessageElement.classList.add(`is-${tone}`);
  }
}

function renderLanguages() {
  languageGridElement.innerHTML = "";
  for (const language of languages) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "language-button";
    if (language.key === selectedLanguageKey) {
      button.classList.add("is-selected");
    }

    const label = document.createElement("span");
    label.className = "language-label";
    label.textContent = language.label;

    const meta = document.createElement("span");
    meta.className = "language-meta";
    meta.textContent = `${language.key}  ${language.locale}`;

    button.append(label, meta);
    button.addEventListener("click", () => updateSelectedLanguage(language.key, language.label));
    languageGridElement.appendChild(button);
  }
}

function applyLanguagePayload(payload) {
  selectedLanguageKey = payload.selectedLanguage.key;
  languages = payload.languages || [];
  selectedLanguageElement.textContent = payload.selectedLanguage.label;
  renderLanguages();
}

async function loadSelectedLanguage() {
  try {
    const response = await fetch("/api/device/language");
    if (!response.ok) {
      throw new Error(`Language request failed with status ${response.status}`);
    }
    const payload = await response.json();
    applyLanguagePayload(payload);
    setStatus("Ready for the next detection.", "success");
  } catch (_error) {
    setStatus("Could not load the current Pi language selection.", "error");
  }
}

async function updateSelectedLanguage(languageKey, languageLabel) {
  setStatus(`Saving ${languageLabel}...`);
  try {
    const response = await fetch("/api/device/language", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ languageKey }),
    });
    if (!response.ok) {
      throw new Error(`Language update failed with status ${response.status}`);
    }
    const payload = await response.json();
    applyLanguagePayload(payload);
    setStatus(`${languageLabel} is now active for new detections.`, "success");
  } catch (_error) {
    setStatus(`Could not switch to ${languageLabel}.`, "error");
  }
}

refreshButtonElement.addEventListener("click", () => {
  loadSelectedLanguage();
});

loadSelectedLanguage();
refreshTimerId = window.setInterval(loadSelectedLanguage, 5000);
window.addEventListener("beforeunload", () => {
  if (refreshTimerId) {
    window.clearInterval(refreshTimerId);
  }
});
