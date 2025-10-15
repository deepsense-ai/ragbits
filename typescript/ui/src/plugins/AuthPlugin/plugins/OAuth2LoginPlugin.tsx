import { lazy } from "react";
import { createPlugin } from "../../../core/utils/plugins/utils";

export const OAuth2LoginPluginName = "OAuth2LoginPlugin";

// Factory function to create OAuth2 login plugin for a specific provider
export const createOAuth2LoginPlugin = (
  provider: string,
  displayName: string,
) => {
  return createPlugin({
    name: `${OAuth2LoginPluginName}_${provider}`,
    components: {
      OAuth2Login: lazy(() => import("../components/OAuth2Login")),
    },
    metadata: {
      provider,
      displayName,
    },
  });
};
