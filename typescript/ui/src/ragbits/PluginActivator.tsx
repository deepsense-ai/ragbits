import { useEffect } from "react";
import { useConfigContext } from "../core/contexts/ConfigContext/useConfigContext";
import { pluginManager } from "../core/utils/plugins/PluginManager";

// Import plugin names (app layer owns these mappings)
import { FeedbackFormPluginName } from "../plugins/FeedbackPlugin";
import { ChatOptionsPluginName } from "../plugins/ChatOptionsPlugin";
import { SharePluginName } from "../plugins/SharePlugin";
import { ChatHistoryPluginName } from "../plugins/ChatHistoryPlugin";
import { AuthPluginName } from "../plugins/AuthPlugin";
import { UsagePluginName } from "../plugins/UsagePlugin";
import { CredentialsLoginPluginName } from "../plugins/AuthPlugin/plugins/CredentialsLoginPlugin";
import { createOAuth2LoginPlugin } from "../plugins/AuthPlugin/plugins/OAuth2LoginPlugin";
import { UploadPluginName } from "../plugins/UploadPlugin";

export function usePluginActivation() {
  const { config } = useConfigContext();

  useEffect(() => {
    if (!config) return;

    const {
      feedback,
      user_settings,
      conversation_history,
      authentication,
      show_usage,
      supports_upload,
    } = config;

    if (feedback.like.enabled || feedback.dislike.enabled) {
      pluginManager.activate(FeedbackFormPluginName);
    }
    if (user_settings.form) {
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

    if (supports_upload) {
      pluginManager.activate(UploadPluginName);
    }

    pluginManager.activate(SharePluginName);
  }, [config]);
}
