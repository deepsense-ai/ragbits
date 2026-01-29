import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { HeroUIProvider } from "@heroui/react";
import "./globals.css";
import { ThemeContextProvider } from "./core/contexts/ThemeContext/ThemeContextProvider.tsx";
import { RagbitsContextProvider } from "@ragbits/api-client-react";
import { loadIcons } from "@iconify/react";
import { pluginManager } from "./core/utils/plugins/PluginManager.ts";
import { FeedbackFormPlugin } from "./plugins/FeedbackPlugin/index.tsx";
import { ChatOptionsPlugin } from "./plugins/ChatOptionsPlugin/index.tsx";
import { ConfigContextProvider } from "./core/contexts/ConfigContext/ConfigContextProvider.tsx";
import { API_URL } from "./core/config.tsx";
import { SharePlugin } from "./plugins/SharePlugin/index.tsx";
import { ChatHistoryPlugin } from "./plugins/ChatHistoryPlugin/index";
import { BrowserRouter } from "react-router";
import { Routes } from "./core/components/Routes.tsx";
import { AuthPlugin } from "./plugins/AuthPlugin/index.tsx";
import { UsagePlugin } from "./plugins/UsagePlugin/index.tsx";
import { CredentialsLoginPlugin } from "./plugins/AuthPlugin/plugins/CredentialsLoginPlugin.tsx";
import RagbitsHistoryStoreProvider from "./ragbits/stores/HistoryStore/RagbitsHistoryStoreProvider.tsx";
import { UploadPlugin } from "./plugins/UploadPlugin/index.tsx";

//Register plugins
pluginManager.register(FeedbackFormPlugin);
pluginManager.register(ChatOptionsPlugin);
pluginManager.register(SharePlugin);
pluginManager.register(ChatHistoryPlugin);
pluginManager.register(AuthPlugin);
pluginManager.register(UsagePlugin);
pluginManager.register(CredentialsLoginPlugin);
pluginManager.register(UploadPlugin);
// OAuth2 login plugins are registered dynamically in PluginActivator

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
  "heroicons:cog-6-tooth",
  "heroicons:bug-ant",
  "heroicons:trash",
]);

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <HeroUIProvider>
      <RagbitsContextProvider baseUrl={API_URL}>
        <ThemeContextProvider>
          <ConfigContextProvider>
            <RagbitsHistoryStoreProvider>
              <BrowserRouter>
                <Routes />
              </BrowserRouter>
            </RagbitsHistoryStoreProvider>
          </ConfigContextProvider>
        </ThemeContextProvider>
      </RagbitsContextProvider>
    </HeroUIProvider>
  </StrictMode>,
);
