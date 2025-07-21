import { Icon } from "@iconify/react";

type LoadingIndicatorProps = {
  content: string;
};

const LoadingIndicator = ({ content }: LoadingIndicatorProps) => {
  return (
    <div className="flex items-center gap-2 text-default-500">
      <Icon icon="heroicons:arrow-path" className="animate-spin" />
      <span>{content.length > 0 ? "Generating..." : "Thinking..."}</span>
    </div>
  );
};

export default LoadingIndicator;
