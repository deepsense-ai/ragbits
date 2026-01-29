import { RouteObject } from "react-router";
import { Plugin, PluginRouteWrapper } from "../types/plugins";
import { produce } from "immer";

export function injectPluginRoutes(
  base: RouteObject[],
  plugins: Plugin[],
): RouteObject[] {
  return produce(base, (draft) => {
    for (const plugin of plugins) {
      for (const route of plugin.routes ?? []) {
        if (!route.target) {
          draft.push(route);
          continue;
        }

        const parent = findRouteByPathInDraft(draft, route.target);
        if (!parent) {
          console.warn(`Target route "${route.target}" not found`);
          continue;
        }

        if (!parent.children) {
          parent.children = [];
        }

        parent.children.push({
          path: route.path,
          element: route.element,
          children: route.children,
        });
      }
    }
  });
}

// This version is safe with Immer drafts
function findRouteByPathInDraft(
  routes: RouteObject[],
  path: string,
): RouteObject | undefined {
  for (const route of routes) {
    if (route.path === path) return route;
    if (route.children) {
      const found = findRouteByPathInDraft(route.children, path);
      if (found) return found;
    }
  }
  return undefined;
}

export function applyRouteWrappers(
  routes: RouteObject[],
  wrappers: PluginRouteWrapper[],
): RouteObject[] {
  const wrap = (routes: RouteObject[]): RouteObject[] => {
    return routes.map((route) => {
      const path = route.path ?? "";
      const applicableWrappers = wrappers.filter(
        (w) => w.target === "global" || w.target === path,
      );

      let wrappedElement = route.element;
      for (const { wrapper } of applicableWrappers) {
        wrappedElement = wrapper(wrappedElement);
      }

      const newRoute = {
        ...route,
        element: wrappedElement,
      };

      if (route.children) {
        newRoute.children = wrap(route.children);
      }

      return newRoute;
    });
  };

  return wrap(routes);
}
