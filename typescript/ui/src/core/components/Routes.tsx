import { useMemo } from "react";
import { useRoutes } from "react-router";
import { injectPluginRoutes, applyRouteWrappers } from "../utils/routes";
import { BASE_ROUTES } from "../../config";
import { useActivePlugins } from "../utils/plugins/useActivePlugins";

export function Routes() {
  const activePlugins = useActivePlugins();
  const finalRoutes = useMemo(() => {
    const pluginRoutes = injectPluginRoutes(BASE_ROUTES, activePlugins);
    const allWrappers = activePlugins.flatMap((p) => p.routeWrappers ?? []);
    return applyRouteWrappers(pluginRoutes, allWrappers);
  }, [activePlugins]);

  return useRoutes(finalRoutes);
}
