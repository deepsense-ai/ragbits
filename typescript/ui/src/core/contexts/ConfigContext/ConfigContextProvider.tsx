import { PropsWithChildren, useEffect, useMemo } from "react";
import { ConfigContext } from "./ConfigContext";
import { useRagbitsCall } from "@ragbits/api-client-react";
import { CircularProgress, cn } from "@heroui/react";
import { FeedbackFormPluginName } from "../../../plugins/FeedbackPlugin";
import { pluginManager } from "../../utils/plugins/PluginManager";

export function ConfigContextProvider({ children }: PropsWithChildren) {
  const { call: fetchConfig, ...config } = useRagbitsCall("/api/config");

  const value = useMemo(() => {
    if (!config.data) {
      return null;
    }

    return {
      config: config.data,
    };
  }, [config.data]);

  useEffect(() => {
    if (!config.data) {
      return;
    }

    const { feedback } = config.data;
    if (feedback.like.enabled || feedback.dislike.enabled) {
      pluginManager.activate(FeedbackFormPluginName);
    }
  }, [config.data]);

  // Load config on mount
  if (!config.data && !config.error && !config.isLoading) {
    fetchConfig();
  }

  // TODO: Consider adding minimal timeout for config to not flash users with this screen
  if (config.isLoading) {
    return (
      <div
        className={cn(
          "flex h-screen w-screen items-start justify-center bg-background",
        )}
      >
        <div className="m-auto flex flex-col items-center gap-4 text-default-900">
          <CircularProgress size="lg" />
          <p>Initializing...</p>
        </div>
      </div>
    );
  }

  if (config.error || !value) {
    return (
      <div
        className={cn(
          "flex h-screen w-screen items-start justify-center bg-background",
        )}
      >
        <div className="m-auto flex flex-col items-center gap-4 text-default-900">
          <p className="text-large">
            Something went wrong during chat initialization.
          </p>
          <p className="text-small text-default-500">
            Try refreshing the page.
          </p>
        </div>
      </div>
    );
  }

  return (
    <ConfigContext.Provider value={value}>{children}</ConfigContext.Provider>
  );
}
