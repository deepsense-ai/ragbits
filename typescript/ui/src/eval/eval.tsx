import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { HeroUIProvider } from "@heroui/react";
import "../globals.css";
import { ThemeContextProvider } from "../core/contexts/ThemeContext/ThemeContextProvider";
import { RagbitsContextProvider } from "@ragbits/api-client-react";
import { loadIcons } from "@iconify/react";
import { HashRouter } from "react-router";
import { EvalStoreProvider } from "./stores/EvalStoreContext";
import { EvalApp } from "./EvalApp";

// API URL - defaults to port 8001 for eval server
const EVAL_API_URL =
  import.meta.env.VITE_EVAL_API_URL ??
  (import.meta.env.DEV ? "http://127.0.0.1:8001" : "");

// Preload icons
loadIcons([
  "heroicons:check",
  "heroicons:x-mark",
  "heroicons:play",
  "heroicons:stop",
  "heroicons:arrow-path",
  "heroicons:sun",
  "heroicons:moon",
  "heroicons:chevron-down",
  "heroicons:chevron-right",
  "heroicons:document-text",
  "heroicons:clipboard",
  "heroicons:trash",
  "heroicons:pencil",
  "heroicons:eye",
  "heroicons:chart-bar",
  "heroicons:chat-bubble-left-right",
  "heroicons:clock",
  "heroicons:currency-dollar",
  "heroicons:cpu-chip",
]);

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <HeroUIProvider>
      <RagbitsContextProvider baseUrl={EVAL_API_URL}>
        <ThemeContextProvider>
          <EvalStoreProvider>
            <HashRouter>
              <EvalApp />
            </HashRouter>
          </EvalStoreProvider>
        </ThemeContextProvider>
      </RagbitsContextProvider>
    </HeroUIProvider>
  </StrictMode>,
);
