import { lazy, Suspense } from "react";
import PluginWrapper from "../../../core/utils/plugins/PluginWrapper";
import { CredentialsLoginPlugin } from "../plugins/CredentialsLoginPlugin";
import { usePlugin } from "../../../core/utils/plugins/usePlugin";
import { CredentialsLoginPluginName } from "../plugins/CredentialsLoginPlugin";
import {
  OAuth2LoginPluginName,
  OAuth2VisualConfig,
} from "../plugins/OAuth2LoginPlugin";
import { pluginManager } from "../../../core/utils/plugins/PluginManager";

const LazyLogin = lazy(() => import("../components/Login"));

export default function LoginRoute() {
  const credentialsPlugin = usePlugin(CredentialsLoginPluginName);

  // Get all OAuth2 plugins that are registered
  const oauth2Plugins = pluginManager
    .getActivePlugins()
    .filter((plugin) => plugin.name.startsWith(OAuth2LoginPluginName));

  const showDivider = credentialsPlugin && oauth2Plugins.length > 0;

  return (
    <Suspense>
      <LazyLogin>
        {/* Credentials Login - activated if backend supports it */}
        <PluginWrapper
          plugin={CredentialsLoginPlugin}
          component="CredentialsLogin"
          disableSkeleton
        />

        {/* Divider between methods if both are available */}
        {showDivider && (
          <div className="my-2 flex items-center gap-2">
            <div className="border-divider flex-1 border-t" />
            <span className="text-small text-default-500">or</span>
            <div className="border-divider flex-1 border-t" />
          </div>
        )}

        {/* Render OAuth2 Login buttons dynamically */}
        {oauth2Plugins.map((plugin, index) => {
          const provider = plugin.metadata?.provider as string;
          const displayName = plugin.metadata?.displayName as string;
          const visualConfig = plugin.metadata?.visualConfig as
            | OAuth2VisualConfig
            | undefined;

          return (
            <div key={plugin.name}>
              {index > 0 && <div className="my-2" />}
              <PluginWrapper
                plugin={plugin}
                component="OAuth2Login"
                componentProps={{ provider, displayName, visualConfig }}
                disableSkeleton
              />
            </div>
          );
        })}
      </LazyLogin>
    </Suspense>
  );
}
