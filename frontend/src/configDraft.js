import { createEmptyConfig } from "./ConfigService.js";

export function createDraftConfig(initialConfig) {
  const baseConfig = createEmptyConfig();

  return {
    jellyfin: {
      url: initialConfig?.jellyfin?.url || baseConfig.jellyfin.url,
      apiKey: initialConfig?.jellyfin?.apiKey || baseConfig.jellyfin.apiKey,
    },
    jellystat: {
      url: initialConfig?.jellystat?.url || baseConfig.jellystat.url,
      enabled: Boolean(initialConfig?.jellystat?.enabled),
    },
    dataMode: initialConfig?.dataMode || baseConfig.dataMode,
  };
}
