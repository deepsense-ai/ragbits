import { lazy } from "react";
import { createPlugin } from "../../core/utils/plugins/utils";
import AuthGuard from "./components/AuthGuard";
import LoginRoute from "./routes/LoginRoute";

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
      wrapper: (children) => <AuthGuard>{children}</AuthGuard>,
    },
  ],
});
