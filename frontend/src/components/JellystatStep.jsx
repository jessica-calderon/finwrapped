import { isValidUrl } from "../ConfigService.js";

export default function JellystatStep({
  value,
  onChange,
  onBack,
  onNext,
  onToggleEnabled,
  onTest,
  onSkip,
  status,
  error,
  isTesting,
}) {
  const isUrlValid = !value.enabled || isValidUrl(value.url || "");
  const canContinue = !value.enabled || isUrlValid;

  return (
    <div className="onboarding-step">
      <div className="onboarding-step__header">
        <p className="onboarding-step__eyebrow">Step 3 of 4</p>
        <h2 className="onboarding-step__title">Optional Jellystat</h2>
        <p className="onboarding-step__subtitle">
          Jellystat can be added later, so this step is optional.
        </p>
      </div>

      <label className="onboarding-toggle">
        <input
          type="checkbox"
          checked={value.enabled}
          onChange={(event) => onToggleEnabled(event.target.checked)}
        />
        <span className="onboarding-toggle__ui" aria-hidden="true" />
        <span className="onboarding-toggle__label">Use Jellystat (optional)</span>
      </label>

      {value.enabled ? (
        <div className="onboarding-form">
          <label className="onboarding-field">
            <span className="onboarding-field__label">Jellystat URL</span>
            <input
              className="onboarding-field__input"
              type="url"
              inputMode="url"
              placeholder="https://jellystat.example.com"
              value={value.url || ""}
              onChange={(event) => onChange(event.target.value)}
              autoComplete="url"
            />
            {!isUrlValid && value.url ? (
              <span className="onboarding-field__error">Enter a valid http or https URL.</span>
            ) : null}
          </label>
        </div>
      ) : null}

      <div className="onboarding-step__status">
        {status === "success" ? <p className="onboarding-step__success">Connected</p> : null}
        {error ? <p className="onboarding-step__error">{error}</p> : null}
      </div>

      <div className="onboarding-step__actions">
        <button type="button" className="onboarding-button onboarding-button--secondary" onClick={onBack}>
          Back
        </button>
        {value.enabled ? (
          <button
            type="button"
            className="onboarding-button onboarding-button--secondary"
            onClick={onTest}
            disabled={!isUrlValid || isTesting}
          >
            {isTesting ? "Testing..." : "Test Jellystat"}
          </button>
        ) : (
          <button
            type="button"
            className="onboarding-button onboarding-button--secondary"
            onClick={onSkip}
          >
            Skip
          </button>
        )}
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

