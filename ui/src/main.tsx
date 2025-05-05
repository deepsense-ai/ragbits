import React from "react";
import ReactDOM from "react-dom/client";
import { HeroUIProvider } from "@heroui/react";
import App from "./App";
import "./globals.css";
import { ChatHistoryProvider } from "./contexts/HistoryContext/HistoryContextProvider";
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
]);

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <HeroUIProvider>
      <ChatHistoryProvider>
        <ThemeContextProvider>
          <App />
        </ThemeContextProvider>
      </ChatHistoryProvider>
    </HeroUIProvider>
  </React.StrictMode>,
);
