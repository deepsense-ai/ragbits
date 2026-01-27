import { useContext } from "react";
import { ConfigContext, IConfigContext } from "./ConfigContext";

const DEFAULT_CONFIG: IConfigContext = {
  config: {
    feedback: {
      like: { enabled: false, form: null },
      dislike: { enabled: false, form: null },
    },
    user_settings: { form: null },
    conversation_history: false,
    authentication: { enabled: false, auth_types: [], oauth2_providers: [] },
    show_usage: false,
    debug_mode: false,
    customization: null,
  },
};

export const useConfigContext = (): IConfigContext => {
  const context = useContext(ConfigContext);
  return context ?? DEFAULT_CONFIG;
};
