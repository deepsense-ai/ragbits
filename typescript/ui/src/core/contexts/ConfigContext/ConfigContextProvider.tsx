import { PropsWithChildren, useEffect, useMemo } from "react";
import { ConfigContext } from "./ConfigContext";
import { useRagbitsCall } from "@ragbits/api-client-react";
import { CONFIG_LOADING_PAGE_TITLE } from "../../config";
import InitializationScreen from "../../components/InitializationScreen";
import InitializationErrorScreen from "../../components/InitializationErrorScreen";

export function ConfigContextProvider({ children }: PropsWithChildren) {
  const { call: fetchConfig, ...config } = useRagbitsCall("/api/config");

  const value = useMemo(() => {
    if (!config.data) {
      return null;
    }

    return {
      config: config.data,
    };
  }, [config.data]);

  if (!config.data && !config.error && !config.isLoading) {
    fetchConfig();
  }

  useEffect(() => {
    document.title = CONFIG_LOADING_PAGE_TITLE;
  }, []);

  if (config.isLoading) {
    return <InitializationScreen />;
  }

  if (config.error || !value) {
    return <InitializationErrorScreen />;
  }

  return (
    <ConfigContext.Provider value={value}>{children}</ConfigContext.Provider>
  );
}
