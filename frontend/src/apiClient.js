const configuredBaseUrl = import.meta.env.VITE_API_BASE_URL?.trim();

function getBrowserCandidates() {
  if (typeof window === "undefined") {
    return ["http://localhost:8091", "http://localhost:8090"];
  }

  const { protocol, hostname, origin } = window.location;

  return [
    origin,
    `http://${hostname}:8091`,
    `http://${hostname}:8090`,
    `${protocol}//${hostname}:8091`,
    `${protocol}//${hostname}:8090`,
  ];
}

function getBaseUrls() {
  const candidates = configuredBaseUrl
    ? [configuredBaseUrl, ...getBrowserCandidates()]
    : getBrowserCandidates();

  return [...new Set(candidates)];
}

export function buildApiHeaders(config, extraHeaders = {}) {
  const headers = {
    ...extraHeaders,
  };

  if (config?.jellyfin?.url) {
    headers["X-Jellyfin-Url"] = config.jellyfin.url;
  }

  if (config?.jellyfin?.apiKey) {
    headers["X-Jellyfin-Key"] = config.jellyfin.apiKey;
  }

  if (config?.jellystat?.enabled && config?.jellystat?.url) {
    headers["X-Jellystat-Url"] = config.jellystat.url;
  }

  headers["X-Data-Mode"] = typeof config?.dataMode === "string" && config.dataMode.trim()
    ? config.dataMode.trim().toLowerCase()
    : "auto";

  return headers;
}

async function fetchWithFallback(path, options) {
  let lastError = null;
  let lastResponse = null;

  for (const baseUrl of getBaseUrls()) {
    try {
      const response = await fetch(`${baseUrl}${path}`, options);
      if (response.ok) {
        return response;
      }

      lastResponse = response;
      if (response.status !== 404) {
        return response;
      }

      lastError = new Error(`Received 404 from ${baseUrl}${path}`);
    } catch (error) {
      lastError = error;
    }
  }

  if (lastResponse) {
    return lastResponse;
  }

  throw lastError || new Error("Unable to reach API.");
}

export async function requestJson(path, options = {}) {
  const response = await fetchWithFallback(path, options);

  let payload = null;
  try {
    payload = await response.json();
  } catch {
    payload = null;
  }

  if (!response.ok || (payload && payload.ok === false)) {
    throw new Error(payload?.detail || payload?.error || `Request failed with status ${response.status}`);
  }

  return payload;
}

