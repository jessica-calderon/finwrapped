import { useMemo, useState } from "react";
import ThemeToggle from "./ThemeToggle.jsx";
import JellyfinStep from "./JellyfinStep.jsx";
import JellystatStep from "./JellystatStep.jsx";
import { buildApiHeaders, requestJson } from "../apiClient.js";
import { createDraftConfig } from "../configDraft.js";
import {
  isValidUrl,
  setConfig,
  setOnboarded,
} from "../ConfigService.js";

async function postJson(path, body, config) {
  return requestJson(path, {
    method: "POST",
    headers: buildApiHeaders(config, {
      "Content-Type": "application/json",
    }),
    body: JSON.stringify(body),
  });
}

export default function Onboarding({ theme, onThemeChange, onComplete, initialConfig }) {
  const [step, setStep] = useState(0);
  const [config, setDraftConfig] = useState(() => createDraftConfig(initialConfig));
  const [jellyfinStatus, setJellyfinStatus] = useState("idle");
  const [jellyfinError, setJellyfinError] = useState("");
  const [jellyfinTesting, setJellyfinTesting] = useState(false);
  const [jellystatStatus, setJellystatStatus] = useState("idle");
  const [jellystatError, setJellystatError] = useState("");
  const [jellystatTesting, setJellystatTesting] = useState(false);

  const jellyfinIsValid = useMemo(
    () => isValidUrl(config.jellyfin.url) && config.jellyfin.apiKey.trim().length > 0,
    [config.jellyfin.apiKey, config.jellyfin.url]
  );

  const jellystatIsValid = useMemo(
    () => !config.jellystat.enabled || isValidUrl(config.jellystat.url || ""),
    [config.jellystat.enabled, config.jellystat.url]
  );

  function updateJellyfin(nextValue) {
    setDraftConfig((current) => ({
      ...current,
      jellyfin: {
        ...current.jellyfin,
        ...nextValue,
      },
    }));
    setJellyfinStatus("idle");
    setJellyfinError("");
  }

  function updateJellystatUrl(nextUrl) {
    setDraftConfig((current) => ({
      ...current,
      jellystat: {
        ...current.jellystat,
        url: nextUrl,
      },
    }));
    setJellystatStatus("idle");
    setJellystatError("");
  }

  function toggleJellystat(enabled) {
    setDraftConfig((current) => ({
      ...current,
      jellystat: {
        enabled,
        url: enabled ? current.jellystat.url : null,
      },
    }));
    setJellystatStatus("idle");
    setJellystatError("");
  }

  async function handleJellyfinTest() {
    if (!jellyfinIsValid) {
      setJellyfinStatus("error");
      setJellyfinError("Enter a valid Jellyfin URL and API key first.");
      return;
    }

    setJellyfinTesting(true);
    setJellyfinError("");

    try {
      await postJson("/api/test/jellyfin", {
        url: config.jellyfin.url,
        apiKey: config.jellyfin.apiKey,
      }, config);
      setJellyfinStatus("success");
    } catch (error) {
      setJellyfinStatus("error");
      setJellyfinError(error instanceof Error ? error.message : "Unable to connect to Jellyfin.");
    } finally {
      setJellyfinTesting(false);
    }
  }

  async function handleJellystatTest() {
    if (!config.jellystat.enabled || !jellystatIsValid) {
      setJellystatStatus("error");
      setJellystatError("Enter a valid Jellystat URL first.");
      return;
    }

    setJellystatTesting(true);
    setJellystatError("");

    try {
      await postJson("/api/test/jellystat", {
        url: config.jellystat.url,
      }, config);
      setJellystatStatus("success");
    } catch (error) {
      setJellystatStatus("error");
      setJellystatError(error instanceof Error ? error.message : "Unable to connect to Jellystat.");
    } finally {
      setJellystatTesting(false);
    }
  }

  function handleFinish() {
    const savedConfig = setConfig(config);
    setOnboarded(true);
    onComplete?.(savedConfig);
  }

  function handlePrimaryAction() {
    if (step < 3) {
      setStep((current) => current + 1);
      return;
    }

    handleFinish();
  }

  const stepContent = {
    0: {
      eyebrow: "Step 1 of 4",
      title: "Welcome to FinWrapped",
      body: "Set up Jellyfin once, optionally connect Jellystat, and FinWrapped will keep the configuration locally on this device.",
      cta: "Get Started",
    },
    3: {
      eyebrow: "Step 4 of 4",
      title: "You’re ready to go",
      body: "Everything is saved locally. Start your recap whenever you’re ready.",
      cta: "Start Recap",
    },
  }[step];

  return (
    <main className="onboarding">
      <div className="onboarding__backdrop" aria-hidden="true" />

      <div className="onboarding__toolbar">
        <ThemeToggle theme={theme} onChange={onThemeChange} />
      </div>

      <section className="onboarding__panel">
        {step === 0 ? (
          <>
            <p className="onboarding__eyebrow">{stepContent.eyebrow}</p>
            <h1 className="onboarding__title">{stepContent.title}</h1>
            <p className="onboarding__subtitle">Generate your Jellyfin recap</p>
            <p className="onboarding__body">{stepContent.body}</p>
            <div className="onboarding__progress" aria-hidden="true">
              {[0, 1, 2, 3].map((index) => (
                <span
                  key={index}
                  className={`onboarding__progress-dot ${index <= step ? "is-active" : ""}`}
                />
              ))}
            </div>
            <button type="button" className="onboarding__cta" onClick={handlePrimaryAction}>
              {stepContent.cta}
            </button>
          </>
        ) : null}

        {step === 1 ? (
          <JellyfinStep
            value={config.jellyfin}
            onChange={updateJellyfin}
            onBack={() => setStep(0)}
            onNext={() => setStep(2)}
            onTest={handleJellyfinTest}
            status={jellyfinStatus}
            error={jellyfinError}
            isTesting={jellyfinTesting}
          />
        ) : null}

        {step === 2 ? (
          <JellystatStep
            value={config.jellystat}
            onChange={updateJellystatUrl}
            onToggleEnabled={toggleJellystat}
            onBack={() => setStep(1)}
            onNext={() => setStep(3)}
            onTest={handleJellystatTest}
            onSkip={() => {
              toggleJellystat(false);
              setStep(3);
            }}
            status={jellystatStatus}
            error={jellystatError}
            isTesting={jellystatTesting}
          />
        ) : null}

        {step === 3 ? (
          <div className="onboarding-step">
            <div className="onboarding-step__header">
              <p className="onboarding-step__eyebrow">{stepContent.eyebrow}</p>
              <h2 className="onboarding-step__title">{stepContent.title}</h2>
              <p className="onboarding-step__subtitle">{stepContent.body}</p>
            </div>

            <div className="onboarding-summary">
              <div className="onboarding-summary__card">
                <p className="onboarding-summary__label">Jellyfin</p>
                <p className="onboarding-summary__value">{config.jellyfin.url || "Not set"}</p>
                <p className="onboarding-summary__meta">
                  {jellyfinStatus === "success" ? "Connected" : "Test before starting"}
                </p>
              </div>
              <div className="onboarding-summary__card">
                <p className="onboarding-summary__label">Jellystat</p>
                <p className="onboarding-summary__value">
                  {config.jellystat.enabled ? config.jellystat.url || "Enabled" : "Disabled"}
                </p>
                <p className="onboarding-summary__meta">
                  {config.jellystat.enabled ? "Optional connection enabled" : "Skipped"}
                </p>
              </div>
            </div>

            <div className="onboarding__progress" aria-hidden="true">
              {[0, 1, 2, 3].map((index) => (
                <span
                  key={index}
                  className={`onboarding__progress-dot ${index <= step ? "is-active" : ""}`}
                />
              ))}
            </div>

            <div className="onboarding-step__actions">
              <button
                type="button"
                className="onboarding-button onboarding-button--secondary"
                onClick={() => setStep(2)}
              >
                Back
              </button>
              <button
                type="button"
                className="onboarding-button onboarding-button--primary"
                onClick={handlePrimaryAction}
                disabled={!jellyfinIsValid || !jellystatIsValid}
              >
                {stepContent.cta}
              </button>
            </div>
          </div>
        ) : null}
      </section>
    </main>
  );
}
