import { Icon } from "@iconify/react";

const LoadingIndicator = () => {
  return (
    <div className="flex items-center gap-2 text-default-500">
      <Icon icon="heroicons:arrow-path" className="animate-spin" />
    </div>
  );
};

export default LoadingIndicator;
