import { useState } from "react";
import ThemeToggle from "./ThemeToggle.jsx";

export default function Onboarding({ theme, onThemeChange, onComplete }) {
  const [step, setStep] = useState(0);

  function handlePrimaryAction() {
    if (step < 2) {
      setStep((current) => current + 1);
      return;
    }

    onComplete?.();
  }

  const stepContent = [
    {
      eyebrow: "Step 1 of 3",
      title: "Welcome to FinWrapped",
      body: "FinWrapped turns your Jellyfin watch history into a cinematic recap built for sharing, replaying, and getting hooked on your own viewing patterns.",
      cta: "Get Started",
    },
    {
      eyebrow: "Step 2 of 3",
      title: "A quick setup is all it takes",
      body: "There are no forms yet. Just a short introduction so the experience feels intentional before your recap begins.",
      cta: "Continue",
    },
    {
      eyebrow: "Step 3 of 3",
      title: "Ready to see your recap?",
      body: "Your first wrapped is waiting. Tap once more and FinWrapped will take you straight into the cinematic slides.",
      cta: "Continue to Recap",
    },
  ][step];

  return (
    <main className="onboarding">
      <div className="onboarding__backdrop" aria-hidden="true" />

      <div className="onboarding__toolbar">
        <ThemeToggle theme={theme} onChange={onThemeChange} />
      </div>

      <section className="onboarding__panel">
        <p className="onboarding__eyebrow">{stepContent.eyebrow}</p>
        <h1 className="onboarding__title">{stepContent.title}</h1>
        <p className="onboarding__subtitle">Generate your Jellyfin recap</p>
        <p className="onboarding__body">{stepContent.body}</p>

        <div className="onboarding__progress" aria-hidden="true">
          {[0, 1, 2].map((index) => (
            <span
              key={index}
              className={`onboarding__progress-dot ${index <= step ? "is-active" : ""}`}
            />
          ))}
        </div>

        <button type="button" className="onboarding__cta" onClick={handlePrimaryAction}>
          {stepContent.cta}
        </button>
      </section>
    </main>
  );
}
