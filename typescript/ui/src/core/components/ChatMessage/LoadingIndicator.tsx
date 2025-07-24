import { Icon } from "@iconify/react";

const LoadingIndicator = () => {
  return (
    <div className="text-default-500 flex items-center gap-2">
      <Icon
        icon="heroicons:arrow-path"
        className="animate-spin"
        data-testid="loading-indicator"
      />
    </div>
  );
};

export default LoadingIndicator;
