import { useEffect, useState } from "react";
import Onboarding from "./components/Onboarding.jsx";
import SettingsPanel from "./components/SettingsPanel.jsx";
import WrappedApp from "./components/WrappedApp.jsx";
import { getConfig, getOnboarded, setOnboarded } from "./ConfigService.js";

const themeStorageKey = "finwrapped_theme";

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

  return getOnboarded();
}

function readStoredConfig() {
  if (typeof window === "undefined") {
    return null;
  }

  return getConfig();
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
  const [config, setConfig] = useState(readStoredConfig);
  const [isOnboarded, setIsOnboarded] = useState(() => {
    const storedConfig = readStoredConfig();
    return Boolean(storedConfig && readStoredOnboarded());
  });
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);

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
    setOnboarded(true);
    setIsOnboarded(true);
    setIsSettingsOpen(false);
  }

  function handleSettingsEdit() {
    setIsSettingsOpen(true);
  }

  function handleSettingsClose() {
    setIsSettingsOpen(false);
  }

  function handleSettingsSave(savedConfig) {
    setConfig(savedConfig);
    setIsSettingsOpen(false);
  }

  return (
    <div className={`finwrapped-shell theme-${theme}`}>
      {isOnboarded ? (
        <WrappedApp
          theme={theme}
          onThemeChange={handleThemeChange}
          config={config}
          onEditSettings={handleSettingsEdit}
          isSettingsOpen={isSettingsOpen}
        />
      ) : (
        <Onboarding
          theme={theme}
          onThemeChange={handleThemeChange}
          initialConfig={config}
          onComplete={(savedConfig) => {
            setConfig(savedConfig);
            handleOnboardingComplete();
          }}
        />
      )}
      {isOnboarded && isSettingsOpen ? (
        <SettingsPanel
          theme={theme}
          onThemeChange={handleThemeChange}
          config={config}
          onClose={handleSettingsClose}
          onSave={handleSettingsSave}
        />
      ) : null}
    </div>
  );
}
