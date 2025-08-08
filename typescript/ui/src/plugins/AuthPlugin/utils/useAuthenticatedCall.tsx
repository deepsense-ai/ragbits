import { useRagbitsCall } from "@ragbits/api-client-react";
import { useAuthStore } from "../contexts/AuthStoreContext/useAuthStore";
import { produce } from "immer";

const useAuthenticatedCall: typeof useRagbitsCall = (
  endpoint,
  defaultOptions,
) => {
  const [token, isAuthEnabled] = useAuthStore((s) => s.token);
  const optionsWithAuth = produce(defaultOptions, (draft) => {
    if (!draft?.headers || !isAuthEnabled) {
      return;
    }

    draft.headers["Authorization"] = `Bearer ${token}`;
  });

  return useRagbitsCall(endpoint, optionsWithAuth);
};

export default useAuthenticatedCall;
