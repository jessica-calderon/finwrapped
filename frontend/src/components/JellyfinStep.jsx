import { isValidUrl } from "../ConfigService.js";

export default function JellyfinStep({
  value,
  onChange,
  onBack,
  onNext,
  onTest,
  status,
  error,
  isTesting,
}) {
  const isUrlValid = isValidUrl(value.url);
  const isApiKeyValid = value.apiKey.trim().length > 0;
  const canContinue = status === "success" && isUrlValid && isApiKeyValid;

  return (
    <div className="onboarding-step">
      <div className="onboarding-step__header">
        <p className="onboarding-step__eyebrow">Step 2 of 4</p>
        <h2 className="onboarding-step__title">Connect Jellyfin</h2>
        <p className="onboarding-step__subtitle">
          FinWrapped needs your Jellyfin server URL and API key to generate a recap.
        </p>
      </div>

      <div className="onboarding-form">
        <label className="onboarding-field">
          <span className="onboarding-field__label">Jellyfin URL</span>
          <input
            className="onboarding-field__input"
            type="url"
            inputMode="url"
            placeholder="https://jellyfin.example.com"
            value={value.url}
            onChange={(event) => onChange({ url: event.target.value, apiKey: value.apiKey })}
            autoComplete="url"
          />
          {!isUrlValid && value.url ? (
            <span className="onboarding-field__error">Enter a valid http or https URL.</span>
          ) : null}
        </label>

        <label className="onboarding-field">
          <span className="onboarding-field__label">API Key</span>
          <input
            className="onboarding-field__input"
            type="password"
            placeholder="Your Jellyfin API key"
            value={value.apiKey}
            onChange={(event) => onChange({ url: value.url, apiKey: event.target.value })}
            autoComplete="off"
          />
          {!isApiKeyValid && value.apiKey ? (
            <span className="onboarding-field__error">API key cannot be empty.</span>
          ) : null}
        </label>
      </div>

      <div className="onboarding-step__status">
        {status === "success" ? (
          <p className="onboarding-step__success">Connected</p>
        ) : null}
        {error ? <p className="onboarding-step__error">{error}</p> : null}
      </div>

      <div className="onboarding-step__actions">
        <button type="button" className="onboarding-button onboarding-button--secondary" onClick={onBack}>
          Back
        </button>
        <button
          type="button"
          className="onboarding-button onboarding-button--secondary"
          onClick={onTest}
          disabled={!isUrlValid || !isApiKeyValid || isTesting}
        >
          {isTesting ? "Testing..." : "Test Connection"}
        </button>
        <button
          type="button"
          className="onboarding-button onboarding-button--primary"
          onClick={onNext}
          disabled={!canContinue}
        >
          Continue
        </button>
      </div>
    </div>
  );
}

