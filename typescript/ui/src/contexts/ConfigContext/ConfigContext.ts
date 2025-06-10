import { ConfigResponse } from "ragbits-api-client";
import { createContext } from "react";

export interface IConfigContext {
  config: ConfigResponse;
}

export const ConfigContext = createContext<IConfigContext | undefined>(
  undefined,
);
