import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { HeroUIProvider } from "@heroui/react";
import App from "./App.tsx";
import "./globals.css";
import { HistoryProvider } from "./core/contexts/HistoryContext/HistoryContextProvider.tsx";
import { ThemeContextProvider } from "./core/contexts/ThemeContext/ThemeContextProvider.tsx";
import { RagbitsProvider } from "@ragbits/api-client-react";
import { loadIcons } from "@iconify/react";
import { pluginManager } from "./core/utils/plugins/PluginManager.ts";
import { FeedbackFormPlugin } from "./plugins/FeedbackPlugin/index.tsx";
import { ConfigContextProvider } from "./core/contexts/ConfigContext/ConfigContextProvider.tsx";

//Register plugins
pluginManager.register(FeedbackFormPlugin);

// Preload icons
loadIcons([
  "heroicons:check",
  "heroicons:clipboard",
  "heroicons:arrow-path",
  "heroicons:sun",
  "heroicons:moon",
  "heroicons:arrow-down",
  "heroicons:arrow-up",
  "heroicons:chevron-down",
  "heroicons:bug-ant",
]);

const API_URL =
  import.meta.env.VITE_API_URL ??
  (import.meta.env.DEV ? "http://127.0.0.1:8000" : "");

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <HeroUIProvider>
      <ThemeContextProvider>
        <RagbitsProvider baseUrl={API_URL}>
          <ConfigContextProvider>
            <HistoryProvider>
              <App />
            </HistoryProvider>
          </ConfigContextProvider>
        </RagbitsProvider>
      </ThemeContextProvider>
    </HeroUIProvider>
  </StrictMode>,
);
