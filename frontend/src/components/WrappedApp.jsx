import { useEffect, useState } from "react";
import RecapSlides from "./RecapSlides.jsx";
import ThemeToggle from "./ThemeToggle.jsx";
import UserSelector from "./UserSelector.jsx";
import TimeRangeSelector, { TIME_RANGES } from "./TimeRangeSelector.jsx";
import { buildApiHeaders, requestJson } from "../apiClient.js";

const slideDurationMs = 3500;

function getRangeLabel(rangeKey) {
  return TIME_RANGES.find((range) => range.key === rangeKey)?.label || "Last 30 days";
}

function createEmptyRecap(recapRange) {
  return {
    range: recapRange,
    user: null,
    total_hours: 0,
    top_movies: [],
    top_shows: [],
    most_active_day: "",
    most_active_hour: 0,
    binge_sessions: 0,
  };
}

function fetchJson(path, config, options = {}) {
  return requestJson(path, {
    ...options,
    headers: buildApiHeaders(config, options.headers || {}),
  });
}

function formatHour(hour) {
  if (typeof hour !== "number" || Number.isNaN(hour)) {
    return null;
  }

  const normalized = ((hour % 24) + 24) % 24;
  const suffix = normalized >= 12 ? "PM" : "AM";
  const displayHour = normalized % 12 || 12;

  return `${displayHour}${suffix}`;
}

function isEmptyRecap(data) {
  if (!data) {
    return true;
  }

  return !(
    Number(data.total_hours) > 0 ||
    (Array.isArray(data.top_movies) && data.top_movies.length > 0) ||
    (Array.isArray(data.top_shows) && data.top_shows.length > 0) ||
    Number(data.binge_sessions) > 0 ||
    Boolean(data.most_active_day)
  );
}

function getPersonality(hour) {
  if (typeof hour !== "number" || Number.isNaN(hour)) {
    return "Still forming";
  }

  return hour > 22 ? "Night Owl" : "Day Watcher";
}

function getUserLabel(users, selectedUser) {
  if (selectedUser === "all") {
    return "All Users";
  }

  return users.find((user) => user.id === selectedUser)?.name || "Selected user";
}

function formatStatTitle(item, fallback) {
  const title = item?.title || item?.name;
  return typeof title === "string" && title.trim() ? title : fallback;
}

function formatPlayCount(count) {
  const numericCount = Number(count);

  if (!Number.isFinite(numericCount) || numericCount <= 0) {
    return null;
  }

  return `${numericCount} ${numericCount === 1 ? "time" : "times"}`;
}

function createTheme(background, accent, accentSoft, glow, accentStrong) {
  return {
    background,
    accent,
    accentSoft,
    glow,
    accentStrong: accentStrong || accent,
  };
}

function buildSlides(data, recapRangeLabel, selectedUserLabel) {
  const totalHours = Math.round(Number(data?.total_hours) || 0);
  const topMovie = data?.top_movies?.[0];
  const topShow = data?.top_shows?.[0];
  const activeHour = formatHour(data?.most_active_hour);
  const personality = getPersonality(data?.most_active_hour);

  const movieHasData = Boolean(topMovie?.title || topMovie?.name);
  const showHasData = Boolean(topShow?.title || topShow?.name);

  return [
    {
      id: "intro",
      label: "FinWrapped",
      title: `Your ${recapRangeLabel} Wrapped`,
      subtitle:
        selectedUserLabel === "All Users"
          ? `A cinematic recap for the whole server over ${recapRangeLabel.toLowerCase()}.`
          : `A cinematic recap for ${selectedUserLabel} over ${recapRangeLabel.toLowerCase()}.`,
      theme: createTheme(
        "linear-gradient(135deg, #0f172a 0%, #111827 50%, #020617 100%)",
        "#7CFFB2",
        "rgba(124, 255, 178, 0.18)",
        "rgba(29, 185, 84, 0.35)",
        "#7CFFB2"
      ),
    },
    {
      id: "watch-time",
      label: "Big number",
      title: `${totalHours} hours`,
      subtitle: `watched during ${recapRangeLabel.toLowerCase()}`,
      theme: createTheme(
        "linear-gradient(135deg, #312e81 0%, #1f1147 58%, #09090b 100%)",
        "#f5d0fe",
        "rgba(245, 208, 254, 0.16)",
        "rgba(139, 92, 246, 0.35)",
        "#f5d0fe"
      ),
    },
    {
      id: "movie",
      label: "Most replayed movie",
      title: movieHasData
        ? formatStatTitle(topMovie, "Your next favorite is waiting")
        : "Your next favorite is waiting",
      subtitle: movieHasData
        ? `Played ${formatPlayCount(topMovie?.play_count) || "a few times"}`
        : "Watch more to unlock this scene.",
      theme: createTheme(
        "linear-gradient(135deg, #0e7490 0%, #082f49 56%, #020617 100%)",
        "#a5f3fc",
        "rgba(165, 243, 252, 0.16)",
        "rgba(6, 182, 212, 0.32)",
        "#a5f3fc"
      ),
    },
    {
      id: "show",
      label: "Most replayed series",
      title: showHasData
        ? formatStatTitle(topShow, "A new favorite is waiting")
        : "A new favorite is waiting",
      subtitle: showHasData
        ? `Played ${formatPlayCount(topShow?.play_count) || "a few times"}`
        : "Keep watching to uncover your top series.",
      theme: createTheme(
        "linear-gradient(135deg, #c2410c 0%, #4c1d95 58%, #020617 100%)",
        "#fed7aa",
        "rgba(254, 215, 170, 0.16)",
        "rgba(249, 115, 22, 0.35)",
        "#fed7aa"
      ),
    },
    {
      id: "day",
      label: "Your rhythm",
      title: data?.most_active_day || "Your rhythm is still forming",
      subtitle: data?.most_active_day
        ? "Your most active day of the week"
        : "Watch a little more to reveal your busiest day.",
      theme: createTheme(
        "linear-gradient(135deg, #9d174d 0%, #111827 58%, #020617 100%)",
        "#fbcfe8",
        "rgba(251, 207, 232, 0.16)",
        "rgba(236, 72, 153, 0.32)",
        "#fbcfe8"
      ),
    },
    {
      id: "personality",
      label: "Wrapped personality",
      title: personality,
      subtitle: activeHour
        ? `You’re most active around ${activeHour}.`
        : "A personality will appear once your viewing pattern settles in.",
      theme: createTheme(
        "linear-gradient(135deg, #0f766e 0%, #042f2e 58%, #020617 100%)",
        "#99f6e4",
        "rgba(153, 246, 228, 0.16)",
        "rgba(15, 118, 110, 0.34)",
        "#99f6e4"
      ),
    },
    {
      id: "outro",
      label: "See you next time",
      title: "That’s your time window",
      subtitle: "Replay the highlights any time.",
      theme: createTheme(
        "linear-gradient(135deg, #111827 0%, #14532d 58%, #020617 100%)",
        "#d9f99d",
        "rgba(217, 249, 157, 0.16)",
        "rgba(29, 185, 84, 0.3)",
        "#d9f99d"
      ),
    },
  ];
}

function buildEmptySlides(selectedUserLabel, recapRangeLabel) {
  const targetLabel =
    selectedUserLabel === "All Users" ? "this story" : `${selectedUserLabel}'s story`;

  return [
    {
      id: "empty-intro",
      label: "FinWrapped",
      title: `Your ${recapRangeLabel} Wrapped is just getting started`,
      subtitle: "Watch more to unlock your recap.",
      theme: createTheme(
        "linear-gradient(135deg, #0f172a 0%, #111827 55%, #020617 100%)",
        "#d9f99d",
        "rgba(217, 249, 157, 0.16)",
        "rgba(29, 185, 84, 0.3)",
        "#d9f99d"
      ),
    },
    {
      id: "empty-detail",
      label: "Nothing to show yet",
      title: `${targetLabel} needs a little more watch time`,
      subtitle: "As soon as there’s enough activity, FinWrapped turns it into scenes.",
      theme: createTheme(
        "linear-gradient(135deg, #1e1b4b 0%, #111827 58%, #020617 100%)",
        "#c4b5fd",
        "rgba(196, 181, 253, 0.16)",
        "rgba(124, 58, 237, 0.3)",
        "#c4b5fd"
      ),
    },
  ];
}

export default function WrappedApp({
  theme,
  onThemeChange,
  config,
  onEditSettings,
  isSettingsOpen = false,
}) {
  const [users, setUsers] = useState([]);
  const [selectedUser, setSelectedUser] = useState("all");
  const [selectedRange, setSelectedRange] = useState("30d");
  const [recapData, setRecapData] = useState(null);
  const [usersLoading, setUsersLoading] = useState(true);
  const [recapLoading, setRecapLoading] = useState(true);
  const [slideIndex, setSlideIndex] = useState(0);

  useEffect(() => {
    let active = true;

    async function loadUsers() {
      try {
        const data = await fetchJson("/api/users", config);
        if (active) {
          setUsers(Array.isArray(data) ? data : []);
        }
      } catch {
        if (active) {
          setUsers([]);
        }
      } finally {
        if (active) {
          setUsersLoading(false);
        }
      }
    }

    loadUsers();

    return () => {
      active = false;
    };
  }, [config]);

  useEffect(() => {
    let active = true;

    setSlideIndex(0);
    setRecapLoading(true);
    setRecapData(null);

    async function loadRecap() {
      const path =
        selectedUser === "all"
          ? `/api/recap?range=${encodeURIComponent(selectedRange)}`
          : `/api/recap/user/${selectedUser}?range=${encodeURIComponent(selectedRange)}`;

      try {
        const data = await fetchJson(path, config);
        if (active) {
          setRecapData(data);
        }
      } catch {
        if (active) {
          setRecapData(createEmptyRecap(selectedRange));
        }
      } finally {
        if (active) {
          setRecapLoading(false);
        }
      }
    }

    loadRecap();

    return () => {
      active = false;
    };
  }, [config, selectedRange, selectedUser]);

  const selectedUserLabel = getUserLabel(users, selectedUser);
  const selectedRangeLabel = getRangeLabel(selectedRange);
  const slides = isEmptyRecap(recapData)
    ? buildEmptySlides(selectedUserLabel, selectedRangeLabel)
    : buildSlides(recapData, selectedRangeLabel, selectedUserLabel);
  const activeSlide = slides[slideIndex] || slides[0];
  const slideCount = slides.length;
  const isLoading = usersLoading || recapLoading;

  useEffect(() => {
    if (isSettingsOpen) {
      return undefined;
    }

    function handleKeyDown(event) {
      if (
        event.target &&
        ["INPUT", "SELECT", "TEXTAREA"].includes(event.target.tagName)
      ) {
        return;
      }

      if (event.key === "ArrowLeft") {
        event.preventDefault();
        setSlideIndex((current) => (current - 1 + slideCount) % slideCount);
      } else if (event.key === "ArrowRight") {
        event.preventDefault();
        setSlideIndex((current) => (current + 1) % slideCount);
      }
    }

    document.addEventListener("keydown", handleKeyDown);

    return () => {
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [isSettingsOpen, slideCount]);

  useEffect(() => {
    if (slideIndex >= slides.length) {
      setSlideIndex(0);
    }
  }, [slideIndex, slides.length]);

  useEffect(() => {
    if (isLoading || slides.length <= 1 || isSettingsOpen) {
      return undefined;
    }

    const timeout = window.setTimeout(() => {
      setSlideIndex((current) => (current + 1) % slides.length);
    }, slideDurationMs);

    return () => window.clearTimeout(timeout);
  }, [isLoading, isSettingsOpen, slideIndex, slides.length]);

  if (isLoading) {
    return (
      <div className="wrapped-loading">
        <div className="wrapped-loading__toolbar">
          <ThemeToggle theme={theme} onChange={onThemeChange} />
        </div>
        <div className="wrapped-loading__orb" />
        <div className="wrapped-loading__content">
          <div className="wrapped-loading__spinner" aria-hidden="true" />
          <p className="wrapped-loading__label">Loading your Wrapped</p>
          <p className="wrapped-loading__text">Assembling your scenes...</p>
        </div>
      </div>
    );
  }

  return (
    <main
      className={`wrapped-app${isSettingsOpen ? " is-settings-open" : ""}`}
      style={{ "--slide-duration": `${slideDurationMs}ms` }}
      aria-hidden={isSettingsOpen}
    >
      <header className="wrapped-topbar">
        <div className="wrapped-brand">
          <p className="wrapped-kicker">FinWrapped</p>
          <p className="wrapped-brand-copy">
            {selectedUserLabel === "All Users"
              ? `A cinematic recap for the whole server in ${selectedRangeLabel}.`
              : `A cinematic recap for ${selectedUserLabel} in ${selectedRangeLabel}.`}
          </p>
        </div>
        <div className="wrapped-topbar__actions">
          <ThemeToggle theme={theme} onChange={onThemeChange} />
          <button type="button" className="wrapped-settings-button" onClick={onEditSettings}>
            Edit settings
          </button>
          <TimeRangeSelector
            ranges={TIME_RANGES}
            selectedRange={selectedRange}
            onSelect={setSelectedRange}
          />
          <UserSelector
            users={users}
            selectedUser={selectedUser}
            onSelect={setSelectedUser}
            disabled={usersLoading}
          />
        </div>
      </header>

      <RecapSlides
        slides={slides}
        activeIndex={slideIndex}
        activeSlide={activeSlide}
        onAdvance={() => setSlideIndex((current) => (current + 1) % slides.length)}
        onPrevious={() =>
          setSlideIndex((current) => (current - 1 + slides.length) % slides.length)
        }
      />
    </main>
  );
}
