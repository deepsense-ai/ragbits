import React from "react";
import ReactDOM from "react-dom/client";
import { HeroUIProvider } from "@heroui/react";
import App from "./App";
import "./globals.css";
import { pluginManager } from "./core/utils/plugins/PluginManager";
import {
  FeedbackFormPlugin,
  FeedbackFormPluginName,
} from "./plugins/FeedbackFormPlugin";
import { ChatHistoryProvider } from "./contexts/HistoryContext/HistoryContextProvider";
import { ThemeContextProvider } from "./contexts/ThemeContext/ThemeContextProvider";

// Register plugins
pluginManager.register(FeedbackFormPlugin);

// Activate plugins
pluginManager.activate(FeedbackFormPluginName);

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
