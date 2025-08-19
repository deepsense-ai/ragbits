import { useContext } from "react";
import { HistoryStoreContext } from "./HistoryStoreContext";

export const useInitializeUserStore = () => {
  const context = useContext(HistoryStoreContext);
  if (!context) {
    throw new Error(
      "useInitializeUserStore must be used within a HistoryStoreContextProvider",
    );
  }

  return context.initializeUserStore;
};
