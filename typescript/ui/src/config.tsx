import { RouteObject } from "react-router";
import App from "./App";

/**
 * Default configuration used by the UI when `/api/config` doesn't return any
 */
export const DEFAULT_LOGO = "🐰";
export const DEFAULT_TITLE = "Ragbits Chat";
export const DEFAULT_SUBTITLE = "by deepsense.ai";

export const API_URL =
  import.meta.env.VITE_API_URL ??
  (import.meta.env.DEV ? "http://127.0.0.1:8000" : "");

export const BASE_ROUTES: RouteObject[] = [
  {
    path: "/",
    element: <App />,
    children: [],
  },
];
