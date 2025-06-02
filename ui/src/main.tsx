import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { HeroUIProvider } from "@heroui/react";
import App from "./App";
import "./globals.css";
import { HistoryProvider } from "./contexts/HistoryContext/HistoryContextProvider";
import { ThemeContextProvider } from "./contexts/ThemeContext/ThemeContextProvider";
import { loadIcons } from "@iconify/react";
import { pluginManager } from "./core/utils/plugins/PluginManager.ts";
import { FeedbackFormPlugin } from "./plugins/FeedbackFormPlugin";

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
]);

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <HeroUIProvider>
      <HistoryProvider>
        <ThemeContextProvider>
          <App />
        </ThemeContextProvider>
      </HistoryProvider>
    </HeroUIProvider>
  </StrictMode>,
);
