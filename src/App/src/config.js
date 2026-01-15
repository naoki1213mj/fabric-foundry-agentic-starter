function getRuntimeConfigValue(runtimeKey, envKey, defaultValue) {
   if (typeof window !== "undefined" && window._env_?.[runtimeKey]) {
    const val = window._env_[runtimeKey].trim();
    if (val && val !== `$${runtimeKey}`) {
      return val;
    }
  }
  if (process.env[envKey]) {
    return process.env[envKey];
  }
  return defaultValue;
}
export function getApiBaseUrl() {
  return getRuntimeConfigValue("APP_API_BASE_URL", "REACT_APP_API_BASE_URL", "http://127.0.0.1:8000");
}
export function getChatLandingText() {
  return getRuntimeConfigValue(
    "CHAT_LANDING_TEXT",
    "REACT_APP_CHAT_LANDING_TEXT",
    "売上、商品、注文に関する質問ができます。"
  );
}
