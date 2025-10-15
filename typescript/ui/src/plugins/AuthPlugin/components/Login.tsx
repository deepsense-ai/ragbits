import { useEffect, ReactNode } from "react";

export interface LoginProps {
  children: ReactNode;
}

export default function Login({ children }: LoginProps) {
  useEffect(() => {
    document.title = "Login";
  }, []);

  return (
    <div className="flex h-screen w-screen">
      <div className="rounded-medium border-small border-divider m-auto flex w-full max-w-xs flex-col gap-4 p-4">
        <div className="text-small">
          <div className="text-foreground truncate leading-5 font-semibold">
            Sign in
          </div>
          <div className="text-default-500 truncate leading-5 font-normal">
            Sign in to start chatting.
          </div>
        </div>
        {children}
      </div>
    </div>
  );
}
