import React from "react";
import ReactDOM from "react-dom/client";
import { HeroUIProvider } from "@heroui/react";
import App from "./App";
import "./globals.css";
import { ExamplePlugin } from "./plugins/ExamplePlugin";
import { pluginManager } from "./utils/plugins/PluginManager";

// Register plugins
pluginManager.register(ExamplePlugin);

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <HeroUIProvider>
      <div className="flex h-screen w-screen items-start justify-center">
        <App />
      </div>
    </HeroUIProvider>
  </React.StrictMode>,
);
