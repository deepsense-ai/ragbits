import { AuthStoreContext } from "./AuthStoreContext";
import { useDynamicStore } from "../../../../core/utils/plugins/utils";
import { AuthStore } from "../../stores/authStore";

export const useAuthStore = <T>(selector: (s: AuthStore) => T) =>
  useDynamicStore(AuthStoreContext)(selector);
