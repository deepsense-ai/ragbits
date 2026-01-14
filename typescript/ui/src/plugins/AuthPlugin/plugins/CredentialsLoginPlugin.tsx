import { lazy } from "react";
import { createPlugin } from "../../../core/utils/plugins/utils";

export const CredentialsLoginPluginName = "CredentialsLoginPlugin";
export const CredentialsLoginPlugin = createPlugin({
  name: CredentialsLoginPluginName,
  components: {
    CredentialsLogin: lazy(() => import("../components/CredentialsLogin")),
  },
});
