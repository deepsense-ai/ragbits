import { lazy } from "react";
import { createPlugin } from "../../core/utils/plugins/utils";
import LoginRoute from "./routes/LoginRoute";
import AuthRoute from "./routes/AuthRoute";

export const AuthPluginName = "AuthPlugin";
export const AuthPlugin = createPlugin({
  name: AuthPluginName,
  components: {
    LogoutButton: lazy(() => import("./components/LogoutButton")),
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
});

// TODO: Handle token refresh when implemented
// TODO: Handle different auth backends
