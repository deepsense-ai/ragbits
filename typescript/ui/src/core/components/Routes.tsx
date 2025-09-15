import { useMemo } from "react";
import { useRoutes } from "react-router";
import { injectPluginRoutes, applyRouteWrappers } from "../utils/routes";
import { useActivePlugins } from "../utils/plugins/useActivePlugins";
import { ROUTES } from "../../routes";

export function Routes() {
  const activePlugins = useActivePlugins();
  const finalRoutes = useMemo(() => {
    const pluginRoutes = injectPluginRoutes(ROUTES, activePlugins);
    const allWrappers = activePlugins.flatMap((p) => p.routeWrappers ?? []);
    return applyRouteWrappers(pluginRoutes, allWrappers);
  }, [activePlugins]);

  return useRoutes(finalRoutes);
}
