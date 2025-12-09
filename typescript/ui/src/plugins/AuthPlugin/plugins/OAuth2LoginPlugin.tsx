import { lazy } from "react";
import { createPlugin } from "../../../core/utils/plugins/utils";

export const OAuth2LoginPluginName = "OAuth2LoginPlugin";

/**
 * Visual configuration for OAuth2 provider buttons.
 */
export interface OAuth2VisualConfig {
  color?: string | null;
  buttonColor?: string | null;
  textColor?: string | null;
  iconSvg?: string | null;
}

// Factory function to create OAuth2 login plugin for a specific provider
export const createOAuth2LoginPlugin = (
  provider: string,
  displayName: string,
  visualConfig?: OAuth2VisualConfig,
) => {
  return createPlugin({
    name: `${OAuth2LoginPluginName}_${provider}`,
    components: {
      OAuth2Login: lazy(() => import("../components/OAuth2Login")),
    },
    metadata: {
      provider,
      displayName,
      visualConfig,
    },
  });
};
