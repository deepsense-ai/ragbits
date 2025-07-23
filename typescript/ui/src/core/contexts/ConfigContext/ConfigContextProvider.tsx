import { PropsWithChildren, useEffect, useMemo } from "react";
import { ConfigContext } from "./ConfigContext";
import { useRagbitsCall } from "@ragbits/api-client-react";
import { CircularProgress, cn } from "@heroui/react";
import { FeedbackFormPluginName } from "../../../plugins/FeedbackPlugin";
import { ChatOptionsPluginName } from "../../../plugins/ChatOptionsPlugin";
import { pluginManager } from "../../utils/plugins/PluginManager";
import { SharePluginName } from "../../../plugins/SharePlugin";
import { HistoryStoreContextProvider } from "../../stores/HistoryStore/HistoryStoreContextProvider";
import { ChatHistoryPluginName } from "../../../plugins/ChatHistoryPlugin";

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

    const {
      feedback,
      user_settings: userSettings,
      client_side_history,
    } = config.data;
    if (feedback.like.enabled || feedback.dislike.enabled) {
      pluginManager.activate(FeedbackFormPluginName);
    }
    if (userSettings.form) {
      pluginManager.activate(ChatOptionsPluginName);
    }
    if (client_side_history) {
      pluginManager.activate(ChatHistoryPluginName);
    }

    pluginManager.activate(SharePluginName);
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
          "bg-background flex h-screen w-screen items-start justify-center",
        )}
      >
        <div className="text-default-900 m-auto flex flex-col items-center gap-4">
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
          "bg-background flex h-screen w-screen items-start justify-center",
        )}
      >
        <div className="text-default-900 m-auto flex flex-col items-center gap-4">
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
    <ConfigContext.Provider value={value}>
      <HistoryStoreContextProvider
        shouldStoreHistory={value.config.client_side_history}
      >
        {children}
      </HistoryStoreContextProvider>
    </ConfigContext.Provider>
  );
}
