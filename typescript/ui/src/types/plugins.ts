import { FunctionComponent, LazyExoticComponent } from "react";

export interface Plugin<
  T extends Record<
    string,
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    LazyExoticComponent<FunctionComponent<any>>
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
  > = Record<string, LazyExoticComponent<FunctionComponent<any>>>,
> {
  name: string;
  onActivate?: () => void;
  onDeactivate?: () => void;
  components: T;
}
