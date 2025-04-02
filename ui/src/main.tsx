import React from "react";
import ReactDOM from "react-dom/client";
import { HeroUIProvider } from "@heroui/react";
import App from "./App";
import "./globals.css";
import { pluginManager } from "./core/utils/plugins/PluginManager";
import { FeedbackFormPlugin } from "./plugins/FeedbackFormPlugin";

// Register plugins
pluginManager.register(FeedbackFormPlugin);

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <HeroUIProvider>
      <div className="flex h-screen w-screen items-start justify-center">
        <App />
      </div>
    </HeroUIProvider>
  </React.StrictMode>,
);
