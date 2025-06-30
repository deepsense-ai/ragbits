import { FunctionComponent } from "react";

export type PropsOf<T> =
  T extends FunctionComponent<infer P>
    ? NoProps<P> extends true
      ? undefined
      : P
    : undefined;
export type NoProps<T> = keyof T extends never ? true : false;
