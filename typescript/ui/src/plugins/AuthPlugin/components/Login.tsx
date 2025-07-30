import { Button, Input } from "@heroui/react";
import { useRagbitsCall } from "@ragbits/api-client-react";
import { FormEvent } from "react";
import { useNavigate } from "react-router";
import { useStore } from "zustand";
import { authStore } from "../stores/authStore";

interface AuthEndpoints {
  "/api/auth/login": {
    method: "POST";
    request: {
      username: string;
      password: string;
    };
    response: {
      success: boolean;
      user: Record<string, string> | null;
      session_id: string | null;
      error_message: string | null;
    };
  };
  "/api/auth/logout": {
    method: "POST";
    request: {
      session_id: string;
    };
    response: {
      success: boolean;
    };
  };
}

export default function Login() {
  const loginRequestFactory = useRagbitsCall<AuthEndpoints, "/api/auth/login">(
    "/api/auth/login",
    {
      headers: {
        "Content-Type": "application/json",
      },
      method: "POST",
    },
  );

  const login = useStore(authStore, (s) => s.login);
  const navigate = useNavigate();

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
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

      // TODO: Improve types of response
      if (!response.success || !response.session_id || !response.user) {
        // TODO: Show error
        return;
      }

      login(
        {
          email: response.user.email,
        },
        response.session_id,
      );
      navigate("/");
    } catch (e) {
      console.error("Failed to login", e);
    }
  };

  return (
    <div className="flex h-screen w-screen">
      <form
        className="rounded-medium border-small border-divider m-auto flex flex-col gap-4 p-4"
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
        />
        <Input
          label="Password"
          labelPlacement="outside"
          id="password"
          name="password"
          type="password"
          placeholder="••••••••"
          required
        />

        <Button type="submit">Sign in</Button>
      </form>
    </div>
  );
}
