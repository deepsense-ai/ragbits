import { createContext, useContext, useRef, type PropsWithChildren } from "react";
import { useStore } from "zustand";
import { createEvalStore, type EvalStore, type EvalStoreApi } from "./evalStore";

const EvalStoreContext = createContext<EvalStoreApi | null>(null);

export function EvalStoreProvider({ children }: PropsWithChildren) {
  const storeRef = useRef<EvalStoreApi | null>(null);

  if (!storeRef.current) {
    storeRef.current = createEvalStore();
  }

  return (
    <EvalStoreContext.Provider value={storeRef.current}>
      {children}
    </EvalStoreContext.Provider>
  );
}

export function useEvalStore<T>(selector: (state: EvalStore) => T): T {
  const store = useContext(EvalStoreContext);
  if (!store) {
    throw new Error("useEvalStore must be used within EvalStoreProvider");
  }
  return useStore(store, selector);
}

export function useEvalStoreApi(): EvalStoreApi {
  const store = useContext(EvalStoreContext);
  if (!store) {
    throw new Error("useEvalStoreApi must be used within EvalStoreProvider");
  }
  return store;
}
