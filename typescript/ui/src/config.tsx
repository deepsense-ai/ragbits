/**
 * Default configuration used by the UI when `/api/config` doesn't return any
 */
export const DEFAULT_LOGO = "🐰";
export const DEFAULT_TITLE = "Ragbits Chat";
export const DEFAULT_SUBTITLE = "by deepsense.ai";
export const CONFIG_LOADING_PAGE_TITLE = "Loading...";

export const API_URL =
  import.meta.env.VITE_API_URL ??
  (import.meta.env.DEV ? "http://localhost:8000" : "");
