function getDisplayTitleClass(title) {
  if (typeof title !== "string") {
    return "wrapped-slide__title";
  }

  return title.length > 20
    ? "wrapped-slide__title wrapped-slide__title--compact"
    : "wrapped-slide__title";
}

export default function Slide({
  label,
  title,
  subtitle,
  theme,
  onNext,
  onPrevious,
  children,
}) {
  function handleClick(event) {
    if (!onNext) {
      return;
    }

    const leftBoundary = window.innerWidth * 0.36;

    if (onPrevious && event.clientX <= leftBoundary) {
      onPrevious();
      return;
    }

    onNext();
  }

  function handleKeyDown(event) {
    if (event.key === "ArrowLeft" && onPrevious) {
      event.preventDefault();
      onPrevious();
      return;
    }

    if (event.key === "ArrowRight" || event.key === " " || event.key === "Enter") {
      event.preventDefault();
      onNext?.();
    }
  }

  return (
    <section
      className="wrapped-slide wrapped-enter"
      role="button"
      tabIndex={0}
      aria-label={title ? `${title}. Click to continue.` : "Wrapped slide"}
      onClick={handleClick}
      onKeyDown={handleKeyDown}
      style={{
        background: theme.background,
        color: theme.textColor || "#fff",
        "--accent": theme.accent,
        "--accent-soft": theme.accentSoft,
        "--glow": theme.glow,
        "--accent-strong": theme.accentStrong || theme.accent,
        transition: "all 0.5s ease",
      }}
    >
      <div className="wrapped-slide__glow wrapped-slide__glow--left" />
      <div className="wrapped-slide__glow wrapped-slide__glow--right" />
      <div className="wrapped-slide__grid" />
      <div className="wrapped-slide__content">
        {label ? <p className="wrapped-label">{label}</p> : null}
        {title ? <h1 className={getDisplayTitleClass(title)}>{title}</h1> : null}
        {subtitle ? <p className="wrapped-subtitle">{subtitle}</p> : null}
        {children}
      </div>
    </section>
  );
}
