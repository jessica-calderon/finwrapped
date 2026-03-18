import { useEffect, useMemo, useState } from "react";
import ThemeToggle from "./ThemeToggle.jsx";
import { buildApiHeaders, requestJson } from "../apiClient.js";
import { createDraftConfig } from "../configDraft.js";
import { isValidUrl, setConfig } from "../ConfigService.js";

const dataModeOptions = [
  {
    value: "auto",
    label: "Auto (recommended)",
    description: "Automatically uses the best available data source",
  },
  {
    value: "jellystat",
    label: "Jellystat only",
    description: "Always use Jellystat when it is available",
  },
  {
    value: "jellyfin",
    label: "Jellyfin only",
    description: "Use Jellyfin playback DB, then the API if needed",
  },
  {
    value: "sync",
    label: "Sync",
    description: "Combines Jellystat and Jellyfin data for maximum accuracy",
  },
];

async function postJson(path, body, config) {
  return requestJson(path, {
    method: "POST",
    headers: buildApiHeaders(config, {
      "Content-Type": "application/json",
    }),
    body: JSON.stringify(body),
  });
}

function createStatusState() {
  return {
    status: "idle",
    error: "",
    testing: false,
  };
}

export default function SettingsPanel({ theme, onThemeChange, config, onClose, onSave }) {
  const [draftConfig, setDraftConfig] = useState(() => createDraftConfig(config));
  const [jellyfinState, setJellyfinState] = useState(createStatusState);
  const [jellystatState, setJellystatState] = useState(createStatusState);

  useEffect(() => {
    function handleKeyDown(event) {
      if (event.key === "Escape") {
        event.preventDefault();
        onClose?.();
      }
    }

    document.addEventListener("keydown", handleKeyDown);

    return () => {
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [onClose]);

  useEffect(() => {
    setDraftConfig(createDraftConfig(config));
    setJellyfinState(createStatusState());
    setJellystatState(createStatusState());
  }, [config]);

  const jellyfinIsValid = useMemo(
    () =>
      isValidUrl(draftConfig.jellyfin.url) && draftConfig.jellyfin.apiKey.trim().length > 0,
    [draftConfig.jellyfin.apiKey, draftConfig.jellyfin.url]
  );

  const jellystatIsValid = useMemo(
    () => !draftConfig.jellystat.enabled || isValidUrl(draftConfig.jellystat.url || ""),
    [draftConfig.jellystat.enabled, draftConfig.jellystat.url]
  );

  const activeDataMode = useMemo(
    () =>
      dataModeOptions.find((option) => option.value === draftConfig.dataMode)?.label ||
      "Auto (recommended)",
    [draftConfig.dataMode]
  );

  const jellystatWarning = useMemo(
    () =>
      draftConfig.jellystat.enabled && jellystatState.status === "error"
        ? jellystatState.error || "Jellystat is enabled but the last test failed."
        : "",
    [draftConfig.jellystat.enabled, jellystatState.error, jellystatState.status]
  );

  function updateJellyfin(nextValue) {
    setDraftConfig((current) => ({
      ...current,
      jellyfin: {
        ...current.jellyfin,
        ...nextValue,
      },
    }));
    setJellyfinState(createStatusState());
  }

  function updateJellystatUrl(nextUrl) {
    setDraftConfig((current) => ({
      ...current,
      jellystat: {
        ...current.jellystat,
        url: nextUrl,
      },
    }));
    setJellystatState(createStatusState());
  }

  function toggleJellystat(enabled) {
    setDraftConfig((current) => ({
      ...current,
      jellystat: {
        enabled,
        url: enabled ? current.jellystat.url : null,
      },
    }));
    setJellystatState(createStatusState());
  }

  function updateDataMode(nextMode) {
    setDraftConfig((current) => ({
      ...current,
      dataMode: nextMode,
    }));
  }

  async function handleJellyfinTest() {
    if (!jellyfinIsValid) {
      setJellyfinState({
        status: "error",
        error: "Enter a valid Jellyfin URL and API key first.",
        testing: false,
      });
      return;
    }

    setJellyfinState((current) => ({ ...current, testing: true, error: "" }));

    try {
      await postJson(
        "/api/test/jellyfin",
        {
          url: draftConfig.jellyfin.url,
          apiKey: draftConfig.jellyfin.apiKey,
        },
        draftConfig
      );
      setJellyfinState({
        status: "success",
        error: "",
        testing: false,
      });
    } catch (error) {
      setJellyfinState({
        status: "error",
        error: error instanceof Error ? error.message : "Unable to connect to Jellyfin.",
        testing: false,
      });
    }
  }

  async function handleJellystatTest() {
    if (!draftConfig.jellystat.enabled || !jellystatIsValid) {
      setJellystatState({
        status: "error",
        error: "Enter a valid Jellystat URL first.",
        testing: false,
      });
      return;
    }

    setJellystatState((current) => ({ ...current, testing: true, error: "" }));

    try {
      await postJson(
        "/api/test/jellystat",
        {
          url: draftConfig.jellystat.url,
        },
        draftConfig
      );
      setJellystatState({
        status: "success",
        error: "",
        testing: false,
      });
    } catch (error) {
      setJellystatState({
        status: "error",
        error: error instanceof Error ? error.message : "Unable to connect to Jellystat.",
        testing: false,
      });
    }
  }

  function handleSave() {
    if (!jellyfinIsValid || !jellystatIsValid) {
      return;
    }

    const savedConfig = setConfig(draftConfig);
    onSave?.(savedConfig);
  }

  return (
    <div className="settings-panel" role="presentation" onClick={onClose}>
      <div className="settings-panel__backdrop" aria-hidden="true" />

      <section
        className="settings-panel__sheet"
        role="dialog"
        aria-modal="true"
        aria-labelledby="settings-panel-title"
        aria-describedby="settings-panel-description"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="settings-panel__toolbar">
          <ThemeToggle theme={theme} onChange={onThemeChange} />
          <button type="button" className="settings-panel__close" onClick={onClose}>
            Back to recap
          </button>
        </div>

        <header className="settings-panel__header">
          <p className="settings-panel__eyebrow">Settings</p>
          <h1 className="settings-panel__title" id="settings-panel-title">
            Update your connections
          </h1>
          <p className="settings-panel__description" id="settings-panel-description">
            Adjust your server details without reopening the getting started flow.
          </p>
        </header>

        <div className="settings-panel__content">
          <section className="settings-card settings-card--wide">
            <div className="settings-card__header">
              <div>
                <p className="settings-card__eyebrow">Data Source</p>
                <h2 className="settings-card__title">Choose how playback data is resolved</h2>
              </div>
              <p className="settings-card__description">
                Pick one source, let FinWrapped decide automatically, or merge both for the most
                complete recap.
              </p>
            </div>

            <div className="data-mode-group" role="radiogroup" aria-label="Data source mode">
              {dataModeOptions.map((option) => {
                const isActive = draftConfig.dataMode === option.value;

                return (
                  <label
                    key={option.value}
                    className={`data-mode-option${isActive ? " is-active" : ""}`}
                  >
                    <input
                      type="radio"
                      name="dataMode"
                      value={option.value}
                      checked={isActive}
                      onChange={() => updateDataMode(option.value)}
                    />
                    <span className="data-mode-option__content">
                      <span className="data-mode-option__label">{option.label}</span>
                      <span className="data-mode-option__description">{option.description}</span>
                    </span>
                  </label>
                );
              })}
            </div>

            <div className="settings-card__status">
              <p className="settings-card__note">Current mode: {activeDataMode}</p>
              <p className="settings-card__note">
                Auto uses the best available source at request time.
              </p>
              {jellystatWarning ? (
                <p className="settings-card__warning">{jellystatWarning}</p>
              ) : null}
            </div>
          </section>

          <section className="settings-card">
            <div className="settings-card__header">
              <div>
                <p className="settings-card__eyebrow">Required</p>
                <h2 className="settings-card__title">Jellyfin</h2>
              </div>
              <p className="settings-card__description">Used to fetch recap data and playback history.</p>
            </div>

            <div className="onboarding-form">
              <label className="onboarding-field">
                <span className="onboarding-field__label">Jellyfin URL</span>
                <input
                  className="onboarding-field__input"
                  type="url"
                  inputMode="url"
                  placeholder="https://jellyfin.example.com"
                  value={draftConfig.jellyfin.url}
                  onChange={(event) =>
                    updateJellyfin({ url: event.target.value, apiKey: draftConfig.jellyfin.apiKey })
                  }
                  autoComplete="url"
                />
                {!jellyfinIsValid && draftConfig.jellyfin.url ? (
                  <span className="onboarding-field__error">Enter a valid http or https URL.</span>
                ) : null}
              </label>

              <label className="onboarding-field">
                <span className="onboarding-field__label">API Key</span>
                <input
                  className="onboarding-field__input"
                  type="password"
                  placeholder="Your Jellyfin API key"
                  value={draftConfig.jellyfin.apiKey}
                  onChange={(event) =>
                    updateJellyfin({ url: draftConfig.jellyfin.url, apiKey: event.target.value })
                  }
                  autoComplete="off"
                />
                {draftConfig.jellyfin.apiKey && !draftConfig.jellyfin.apiKey.trim() ? (
                  <span className="onboarding-field__error">API key cannot be empty.</span>
                ) : null}
              </label>
            </div>

            <div className="onboarding-step__status">
              {jellyfinState.status === "success" ? (
                <p className="onboarding-step__success">Connected</p>
              ) : null}
              {jellyfinState.error ? <p className="onboarding-step__error">{jellyfinState.error}</p> : null}
            </div>

            <div className="onboarding-step__actions settings-card__actions">
              <button
                type="button"
                className="onboarding-button onboarding-button--secondary"
                onClick={handleJellyfinTest}
                disabled={!jellyfinIsValid || jellyfinState.testing}
              >
                {jellyfinState.testing ? "Testing..." : "Test connection"}
              </button>
            </div>
          </section>

          <section className="settings-card">
            <div className="settings-card__header">
              <div>
                <p className="settings-card__eyebrow">Optional</p>
                <h2 className="settings-card__title">Jellystat</h2>
              </div>
              <p className="settings-card__description">Connect Jellystat later if you want richer server stats.</p>
            </div>

            <label className="onboarding-toggle">
              <input
                type="checkbox"
                checked={draftConfig.jellystat.enabled}
                onChange={(event) => toggleJellystat(event.target.checked)}
              />
              <span className="onboarding-toggle__ui" aria-hidden="true" />
              <span className="onboarding-toggle__label">Use Jellystat</span>
            </label>

            {draftConfig.jellystat.enabled ? (
              <div className="onboarding-form">
                <label className="onboarding-field">
                  <span className="onboarding-field__label">Jellystat URL</span>
                  <input
                    className="onboarding-field__input"
                    type="url"
                    inputMode="url"
                    placeholder="https://jellystat.example.com"
                    value={draftConfig.jellystat.url || ""}
                    onChange={(event) => updateJellystatUrl(event.target.value)}
                    autoComplete="url"
                  />
                  {!jellystatIsValid && draftConfig.jellystat.url ? (
                    <span className="onboarding-field__error">Enter a valid http or https URL.</span>
                  ) : null}
                </label>
              </div>
            ) : (
              <p className="settings-card__note">Leave this off if you only want Jellyfin data.</p>
            )}

            <div className="onboarding-step__status">
              {jellystatState.status === "success" ? (
                <p className="onboarding-step__success">Connected</p>
              ) : null}
              {jellystatState.error ? <p className="onboarding-step__error">{jellystatState.error}</p> : null}
            </div>

            <div className="onboarding-step__actions settings-card__actions">
              {draftConfig.jellystat.enabled ? (
                <button
                  type="button"
                  className="onboarding-button onboarding-button--secondary"
                  onClick={handleJellystatTest}
                  disabled={!jellystatIsValid || jellystatState.testing}
                >
                  {jellystatState.testing ? "Testing..." : "Test Jellystat"}
                </button>
              ) : null}
            </div>
          </section>
        </div>

        <footer className="settings-panel__footer">
          <p className="settings-panel__note">Changes are stored locally on this device.</p>
          <div className="settings-panel__footer-actions">
            <button
              type="button"
              className="onboarding-button onboarding-button--secondary"
              onClick={onClose}
            >
              Cancel
            </button>
            <button
              type="button"
              className="onboarding-button onboarding-button--primary"
              onClick={handleSave}
              disabled={!jellyfinIsValid || !jellystatIsValid}
            >
              Save changes
            </button>
          </div>
        </footer>
      </section>
    </div>
  );
}
