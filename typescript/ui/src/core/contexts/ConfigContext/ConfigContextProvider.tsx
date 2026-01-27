import { PropsWithChildren, useEffect, useMemo } from "react";
import { ConfigContext } from "./ConfigContext";
import { useRagbitsCall } from "@ragbits/api-client-react";
import { FeedbackFormPluginName } from "../../../plugins/FeedbackPlugin";
import { ChatOptionsPluginName } from "../../../plugins/ChatOptionsPlugin";
import { pluginManager } from "../../utils/plugins/PluginManager";
import { SharePluginName } from "../../../plugins/SharePlugin";
import { ChatHistoryPluginName } from "../../../plugins/ChatHistoryPlugin";
import { CONFIG_LOADING_PAGE_TITLE } from "../../../config";
import { AuthPluginName } from "../../../plugins/AuthPlugin";
import { UsagePluginName } from "../../../plugins/UsagePlugin";
import { CredentialsLoginPluginName } from "../../../plugins/AuthPlugin/plugins/CredentialsLoginPlugin";
import { createOAuth2LoginPlugin } from "../../../plugins/AuthPlugin/plugins/OAuth2LoginPlugin";
import InitializationScreen from "../../components/InitializationScreen";
import InitializationErrorScreen from "../../components/InitializationErrorScreen";

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
      conversation_history,
      authentication,
      show_usage,
    } = config.data;

    if (feedback.like.enabled || feedback.dislike.enabled) {
      pluginManager.activate(FeedbackFormPluginName);
    }
    if (userSettings.form) {
      pluginManager.activate(ChatOptionsPluginName);
    }
    if (conversation_history) {
      pluginManager.activate(ChatHistoryPluginName);
    }
    if (authentication.enabled) {
      pluginManager.activate(AuthPluginName);

      // Activate appropriate login plugins based on auth types
      if (authentication.auth_types.includes("credentials")) {
        pluginManager.activate(CredentialsLoginPluginName);
      }

      // Dynamically create and activate OAuth2 login plugins for each provider
      if (
        authentication.auth_types.includes("oauth2") &&
        authentication.oauth2_providers
      ) {
        authentication.oauth2_providers.forEach((provider) => {
          const oauth2Plugin = createOAuth2LoginPlugin(
            provider.name,
            provider.display_name || provider.name,
            {
              color: provider.color,
              buttonColor: provider.button_color,
              textColor: provider.text_color,
              iconSvg: provider.icon_svg,
            },
          );
          pluginManager.register(oauth2Plugin);
          pluginManager.activate(oauth2Plugin.name);
        });
      }
    }
    if (show_usage) {
      pluginManager.activate(UsagePluginName);
    }

    pluginManager.activate(SharePluginName);
  }, [config.data]);

  if (!config.data && !config.error && !config.isLoading) {
    fetchConfig();
  }

  useEffect(() => {
    document.title = CONFIG_LOADING_PAGE_TITLE;
  }, []);

  if (config.isLoading) {
    return <InitializationScreen />;
  }

  if (config.error || !value) {
    return <InitializationErrorScreen />;
  }

  return (
    <ConfigContext.Provider value={value}>{children}</ConfigContext.Provider>
  );
}
