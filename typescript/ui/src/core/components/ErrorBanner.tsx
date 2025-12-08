import { Button, cn } from "@heroui/react";
import { Icon } from "@iconify/react";

interface ErrorBannerProps {
  message: string;
  onDismiss: () => void;
  className?: string;
}

export default function ErrorBanner({
  message,
  onDismiss,
  className,
}: ErrorBannerProps) {
  return (
    <div
      data-testid="error-banner"
      className={cn(
        "bg-danger-50 border-danger-200 text-danger-700 rounded-medium flex items-center justify-between gap-3 border px-4 py-3",
        className,
      )}
      role="alert"
    >
      <div className="flex items-center gap-2">
        <Icon
          icon="heroicons:exclamation-triangle"
          className="text-danger h-5 w-5 flex-shrink-0"
        />
        <span className="text-small">{message}</span>
      </div>
      <Button
        isIconOnly
        size="sm"
        variant="light"
        aria-label="Dismiss error"
        onPress={onDismiss}
        className="text-danger-600 hover:text-danger-800 hover:bg-danger-100 h-6 w-6 min-w-6"
      >
        <Icon icon="heroicons:x-mark" className="h-4 w-4" />
      </Button>
    </div>
  );
}
