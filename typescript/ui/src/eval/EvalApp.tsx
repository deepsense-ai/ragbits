import { useEffect, useRef } from "react";
import { useRoutes } from "react-router";
import { useRagbitsContext } from "@ragbits/api-client-react";
import { useEvalStore, useEvalStoreApi } from "./stores/EvalStoreContext";
import { Spinner } from "@heroui/react";
import { EVAL_ROUTES } from "./routes";
import type { EvalConfig } from "./types";

// Check for mock mode via URL param: ?mock=true
const USE_MOCK_DATA = new URLSearchParams(window.location.search).has("mock");

export function EvalApp() {
  const { client } = useRagbitsContext();
  const storeApi = useEvalStoreApi();
  const isConfigLoading = useEvalStore((s) => s.isConfigLoading);
  const configError = useEvalStore((s) => s.configError);
  const loadedRef = useRef(false);

  const routes = useRoutes(EVAL_ROUTES);

  useEffect(() => {
    if (loadedRef.current) return;
    loadedRef.current = true;

    // Use mock data if ?mock is in URL
    if (USE_MOCK_DATA) {
      storeApi.getState().actions.loadMockData();
      return;
    }

    async function loadConfig() {
      const { setConfigLoading, setConfig, setConfigError } = storeApi.getState().actions;
      setConfigLoading(true);
      try {
        const response = await client.makeRequest("/api/eval/config" as "/api/config");
        setConfig(response as unknown as EvalConfig);
      } catch (error) {
        setConfigError(
          error instanceof Error ? error.message : "Failed to load config",
        );
      }
    }

    loadConfig();
  }, [client, storeApi]);

  if (isConfigLoading) {
    return (
      <div className="flex h-full items-center justify-center bg-background">
        <div className="flex flex-col items-center gap-4">
          <Spinner size="lg" />
          <p className="text-foreground-500">Loading evaluation configuration...</p>
        </div>
      </div>
    );
  }

  if (configError) {
    return (
      <div className="flex h-full items-center justify-center bg-background">
        <div className="flex flex-col items-center gap-4 text-center">
          <div className="text-6xl">!</div>
          <h1 className="text-xl font-semibold text-danger">
            Failed to Connect
          </h1>
          <p className="max-w-md text-foreground-500">
            Could not connect to the evaluation API. Make sure the EvalAPI
            server is running.
          </p>
          <p className="text-sm text-foreground-400">{configError}</p>
          <button
            onClick={() => window.location.reload()}
            className="mt-4 rounded-lg bg-primary px-4 py-2 text-white hover:bg-primary-600"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return routes;
}
