const CONFIG_STORAGE_KEY = "finwrapped_config";
const ONBOARDED_STORAGE_KEY = "finwrapped_onboarded";

const defaultConfig = {
  jellyfin: {
    url: "",
    apiKey: "",
  },
  jellystat: {
    url: null,
    enabled: false,
  },
  dataMode: "auto",
};

function getStorageValue(key) {
  if (typeof window === "undefined") {
    return null;
  }

  try {
    return window.localStorage.getItem(key);
  } catch {
    return null;
  }
}

function setStorageValue(key, value) {
  if (typeof window === "undefined") {
    return;
  }

  try {
    window.localStorage.setItem(key, value);
  } catch {
    // Ignore storage failures so the UI can still continue.
  }
}

function removeStorageValue(key) {
  if (typeof window === "undefined") {
    return;
  }

  try {
    window.localStorage.removeItem(key);
  } catch {
    // Ignore storage failures so the UI can still continue.
  }
}

function cleanUrl(value) {
  if (typeof value !== "string") {
    return "";
  }

  return value.trim();
}

function cleanOptionalUrl(value) {
  const cleaned = cleanUrl(value);
  return cleaned ? cleaned : null;
}

function normalizeConfig(config) {
  return {
    jellyfin: {
      url: cleanUrl(config?.jellyfin?.url),
      apiKey: cleanUrl(config?.jellyfin?.apiKey),
    },
    jellystat: {
      url: cleanOptionalUrl(config?.jellystat?.url),
      enabled: Boolean(config?.jellystat?.enabled),
    },
    dataMode: normalizeDataMode(config?.dataMode),
  };
}

function normalizeDataMode(value) {
  const normalized = typeof value === "string" ? value.trim().toLowerCase() : "";
  return ["auto", "jellystat", "jellyfin", "sync"].includes(normalized) ? normalized : "auto";
}

export function getConfig() {
  const rawConfig = getStorageValue(CONFIG_STORAGE_KEY);
  if (!rawConfig) {
    return null;
  }

  try {
    return normalizeConfig(JSON.parse(rawConfig));
  } catch {
    return null;
  }
}

export function setConfig(config) {
  const normalizedConfig = normalizeConfig(config);
  setStorageValue(CONFIG_STORAGE_KEY, JSON.stringify(normalizedConfig));
  return normalizedConfig;
}

export function clearConfig() {
  removeStorageValue(CONFIG_STORAGE_KEY);
}

export function getOnboarded() {
  return getStorageValue(ONBOARDED_STORAGE_KEY) === "true";
}

export function setOnboarded(isOnboarded) {
  setStorageValue(ONBOARDED_STORAGE_KEY, isOnboarded ? "true" : "false");
}

export function clearOnboarded() {
  removeStorageValue(ONBOARDED_STORAGE_KEY);
}

export function createEmptyConfig() {
  return typeof structuredClone === "function"
    ? structuredClone(defaultConfig)
    : normalizeConfig(defaultConfig);
}

export function isValidUrl(value) {
  if (typeof value !== "string") {
    return false;
  }

  try {
    const parsed = new URL(value.trim());
    return parsed.protocol === "http:" || parsed.protocol === "https:";
  } catch {
    return false;
  }
}

