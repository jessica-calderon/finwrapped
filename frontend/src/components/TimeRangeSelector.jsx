export const TIME_RANGES = [
  { key: "7d", label: "Last 7 days" },
  { key: "30d", label: "Last 30 days" },
  { key: "90d", label: "Last 3 months" },
  { key: "ytd", label: "This year" },
  { key: "1y", label: "Last year" },
  { key: "all", label: "All time" },
];

export default function TimeRangeSelector({
  ranges = TIME_RANGES,
  selectedRange,
  onSelect,
  disabled = false,
  label = "Time range",
}) {
  const options = Array.isArray(ranges) ? ranges : [];

  return (
    <div className="wrapped-time-range-selector" role="group" aria-label="Choose a time range">
      <span className="wrapped-time-range-selector__label">{label}</span>
      <div className="wrapped-time-range-selector__pills">
        {options.map((range) => {
          const isActive = selectedRange === range.key;

          return (
            <button
              key={range.key}
              type="button"
              className={`wrapped-user-pill${isActive ? " is-active" : ""}`}
              onClick={() => onSelect(range.key)}
              aria-pressed={isActive}
              disabled={disabled}
            >
              {range.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}
