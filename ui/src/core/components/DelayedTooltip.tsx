import { Tooltip, TooltipProps } from "@heroui/react";

const DelayedTooltip = (props: TooltipProps) => {
  return <Tooltip delay={300} closeDelay={0} {...props} />;
};

export default DelayedTooltip;
