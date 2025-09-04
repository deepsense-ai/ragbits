import { CircularProgress, cn } from "@heroui/react";

export default function InitializationScreen() {
  return (
    <div
      className={cn(
        "bg-background flex h-screen w-screen items-start justify-center",
      )}
    >
      <div className="text-default-900 m-auto flex flex-col items-center gap-4">
        <CircularProgress size="lg" />
        <p>Initializing...</p>
      </div>
    </div>
  );
}
