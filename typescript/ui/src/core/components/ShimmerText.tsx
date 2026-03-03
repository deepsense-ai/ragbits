import { cn } from "@heroui/react";
import { motion } from "framer-motion";
import { PropsWithChildren } from "react";

const DEFAULT_SHIMMER_DURATION = 1;

interface ShimmerTextProps {
  duration?: number;
  className?: string;
}

export default function ShimmerText({
  duration,
  className,
  children,
}: PropsWithChildren<ShimmerTextProps>) {
  return (
    <motion.div
      className={cn("text-default-500", className)}
      animate={{ opacity: [0.4, 1, 0.4] }}
      transition={{
        duration: duration ?? DEFAULT_SHIMMER_DURATION,
        repeat: Infinity,
        ease: "easeInOut",
      }}
    >
      {children}
    </motion.div>
  );
}
