import { useEffect, useState } from "react";
import Onboarding from "./components/Onboarding.jsx";
import WrappedApp from "./components/WrappedApp.jsx";

const themeStorageKey = "finwrapped_theme";
const onboardedStorageKey = "finwrapped_onboarded";

function readStoredTheme() {
  if (typeof window === "undefined") {
    return "dark";
  }

  const stored = window.localStorage.getItem(themeStorageKey);
  return stored === "light" ? "light" : "dark";
}

function readStoredOnboarded() {
  if (typeof window === "undefined") {
    return false;
  }

  return window.localStorage.getItem(onboardedStorageKey) === "true";
}

function applyTheme(theme) {
  const nextTheme = theme === "light" ? "light" : "dark";

  document.body.classList.remove("dark", "light");
  document.body.classList.add(nextTheme);
  document.documentElement.style.colorScheme = nextTheme;
  document.body.dataset.theme = nextTheme;
}

export default function App() {
  const [theme, setTheme] = useState(readStoredTheme);
  const [isOnboarded, setIsOnboarded] = useState(readStoredOnboarded);

  useEffect(() => {
    applyTheme(theme);
    try {
      window.localStorage.setItem(themeStorageKey, theme);
    } catch {
      // Ignore storage failures so the UI still renders.
    }
  }, [theme]);

  function handleThemeChange(nextTheme) {
    setTheme(nextTheme);
  }

  function handleOnboardingComplete() {
    try {
      window.localStorage.setItem(onboardedStorageKey, "true");
    } catch {
      // Ignore storage failures so the UI still renders.
    }
    setIsOnboarded(true);
  }

  return (
    <div className={`finwrapped-shell theme-${theme}`}>
      {isOnboarded ? (
        <WrappedApp theme={theme} onThemeChange={handleThemeChange} />
      ) : (
        <Onboarding
          theme={theme}
          onThemeChange={handleThemeChange}
          onComplete={handleOnboardingComplete}
        />
      )}
    </div>
  );
}
