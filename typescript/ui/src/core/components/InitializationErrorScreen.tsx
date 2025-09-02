import { cn } from "@heroui/react";

export default function InitializationErrorScreen() {
  return (
    <div
      className={cn(
        "bg-background flex h-screen w-screen items-start justify-center",
      )}
    >
      <div className="text-default-900 m-auto flex flex-col items-center gap-4">
        <p className="text-large">
          Something went wrong during chat initialization.
        </p>
        <p className="text-small text-default-500">Try refreshing the page.</p>
      </div>
    </div>
  );
}
