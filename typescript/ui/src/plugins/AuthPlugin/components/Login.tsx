import { Button, Input } from "@heroui/react";
import { useRagbitsCall } from "@ragbits/api-client-react";
import { ChangeEvent, FormEvent, useState } from "react";
import { useNavigate } from "react-router";
import { useStore } from "zustand";
import { authStore } from "../stores/authStore";
import { AnimatePresence, motion } from "framer-motion";
import { produce } from "immer";
import { useInitializeUserStore } from "../../../core/stores/HistoryStore/useInitializeUserStore";

export default function Login() {
  const [formData, setFormData] = useState({
    username: "",
    password: "",
  });
  const loginRequestFactory = useRagbitsCall("/api/auth/login", {
    headers: {
      "Content-Type": "application/json",
    },
    method: "POST",
  });

  const login = useStore(authStore, (s) => s.login);
  const navigate = useNavigate();
  const initializeUserStore = useInitializeUserStore();
  const [isError, setError] = useState<boolean>(false);

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    setError(false);
    e.preventDefault();
    e.stopPropagation();
    const formData = new FormData(e.currentTarget);
    const username = formData.get("username") as string;
    const password = formData.get("password") as string;

    try {
      // Replace with your API call
      const response = await loginRequestFactory.call({
        body: { username, password },
      });

      if (!response.success || !response.jwt_token || !response.user) {
        setError(true);
        return;
      }

      login(response.user, response.jwt_token);
      initializeUserStore(response.user.user_id);
      navigate("/");
    } catch (e) {
      setError(true);
      console.error("Failed to login", e);
    }
  };

  const handleChange = (field: keyof typeof formData) => {
    return (event: ChangeEvent<HTMLInputElement>) =>
      setFormData((prev) =>
        produce(prev, (draft) => {
          draft[field] = event.target.value;
        }),
      );
  };

  return (
    <div className="flex h-screen w-screen">
      <form
        className="rounded-medium border-small border-divider m-auto flex w-full max-w-xs flex-col gap-4 p-4"
        onSubmit={handleSubmit}
      >
        <div className="text-small">
          <div className="text-foreground truncate leading-5 font-semibold">
            Sign in
          </div>
          <div className="text-default-500 truncate leading-5 font-normal">
            Sign in to start chatting.
          </div>
        </div>
        <Input
          label="Username"
          name="username"
          labelPlacement="outside"
          placeholder="Your username"
          required
          isRequired
          value={formData.username}
          onChange={handleChange("username")}
        />
        <Input
          label="Password"
          labelPlacement="outside"
          id="password"
          name="password"
          type="password"
          placeholder="••••••••"
          required
          isRequired
          value={formData.password}
          onChange={handleChange("password")}
        />

        <AnimatePresence>
          {isError &&
            loginRequestFactory.error &&
            !loginRequestFactory.isLoading && (
              <motion.div
                className="text-small text-danger"
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                transition={{ duration: 0.3, ease: "easeOut" }}
              >
                We couldn't sign you in. Please verify your credentials and try
                again.
              </motion.div>
            )}
        </AnimatePresence>

        <Button
          type="submit"
          color={formData.password && formData.username ? "primary" : "default"}
        >
          Sign in
        </Button>
      </form>
    </div>
  );
}
