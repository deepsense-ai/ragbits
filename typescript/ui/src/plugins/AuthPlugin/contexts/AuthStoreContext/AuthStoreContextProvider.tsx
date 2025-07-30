import { PropsWithChildren, useState } from "react";
import { authStore } from "../../stores/authStore";
import { AuthStoreContext } from "./AuthStoreContext";

export function AuthStoreContextProvider({ children }: PropsWithChildren) {
  const [store] = useState(() => authStore);

  return (
    <AuthStoreContext.Provider value={store}>
      {children}
    </AuthStoreContext.Provider>
  );
}
