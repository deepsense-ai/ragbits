import { lazy } from "react";
import { createPlugin } from "../../core/utils/plugins/utils";
import LoginRoute from "./routes/LoginRoute";
import AuthRoute from "./routes/AuthRoute";

const LogoutButton = lazy(() => import("./components/LogoutButton"));

export const AuthPluginName = "AuthPlugin";
export const AuthPlugin = createPlugin({
  name: AuthPluginName,
  components: {
    LogoutButton,
  },
  routes: [
    {
      path: `/login`,
      element: <LoginRoute />,
    },
  ],
  routeWrappers: [
    {
      target: "global",
      wrapper: (children) => <AuthRoute>{children}</AuthRoute>,
    },
  ],
  slots: [
    {
      slot: "layout.headerActions",
      component: LogoutButton,
      priority: 10,
    },
  ],
});

// TODO: Handle token refresh when implemented
// TODO: Handle different auth backends
