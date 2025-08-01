import { RouteObject } from "react-router";
import { Plugin, PluginRouteWrapper } from "../../types/plugins";

export function injectPluginRoutes(
  base: RouteObject[],
  plugins: Plugin[],
): RouteObject[] {
  const enhancedRoutes = [...base];

  for (const plugin of plugins) {
    for (const route of plugin.routes ?? []) {
      if (!route.target) {
        enhancedRoutes.push(route);
        continue;
      }

      const parent = findRouteByPath(enhancedRoutes, route.target);
      if (!parent) {
        console.warn(`Target route "${route.target}" not found`);
        continue;
      }

      parent.children ??= [];
      parent.children.push({
        path: route.path,
        element: route.element,
        children: route.children,
      });
    }
  }

  return enhancedRoutes;
}

export function findRouteByPath(
  routes: RouteObject[],
  path: string,
): RouteObject | undefined {
  for (const route of routes) {
    if (route.path === path) return route;
    if (!route.children) continue;

    const found = findRouteByPath(route.children, path);
    if (!found) continue;
    return found;
  }
  return undefined;
}

export function applyRouteWrappers(
  routes: RouteObject[],
  wrappers: PluginRouteWrapper[],
): RouteObject[] {
  return routes.map((route) => {
    const path = route.path ?? "";
    const applicableWrappers = wrappers.filter(
      (w) => w.target === "global" || w.target === path,
    );

    let wrappedElement = route.element;
    for (const { wrapper } of applicableWrappers) {
      wrappedElement = wrapper(wrappedElement);
    }

    const resultingRoute = {
      ...route,
      element: wrappedElement,
    };

    if (route.children) {
      resultingRoute.children = applyRouteWrappers(route.children, wrappers);
    }

    return resultingRoute;
  });
}
