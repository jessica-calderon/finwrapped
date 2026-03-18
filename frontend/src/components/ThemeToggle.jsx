const themeStorageKey = "finwrapped_theme";

function applyTheme(theme) {
  const nextTheme = theme === "light" ? "light" : "dark";

  document.body.classList.remove("dark", "light");
  document.body.classList.add(nextTheme);
  document.body.dataset.theme = nextTheme;
  document.documentElement.style.colorScheme = nextTheme;
}

export default function ThemeToggle({ theme, onChange }) {
  const isLight = theme === "light";
  const label = isLight ? "Light" : "Dark";

  function handleClick() {
    const nextTheme = isLight ? "dark" : "light";

    try {
      window.localStorage.setItem(themeStorageKey, nextTheme);
    } catch {
      // Storage can be unavailable in private or restricted contexts.
    }

    applyTheme(nextTheme);
    onChange?.(nextTheme);
  }

  return (
    <button
      type="button"
      className="theme-toggle"
      onClick={handleClick}
      aria-label={`Switch to ${isLight ? "dark" : "light"} theme`}
      aria-pressed={isLight}
    >
      <span className="theme-toggle__dot" aria-hidden="true" />
      <span className="theme-toggle__label">{label}</span>
    </button>
  );
}
