import { cn } from "@heroui/react";
import { motion } from "framer-motion";
import { PropsWithChildren } from "react";

const DEFAULT_PULSE_DURATION = 1;

interface PulsingTextProps {
  duration?: number;
  className?: string;
}

export default function PulsingText({
  duration,
  className,
  children,
}: PropsWithChildren<PulsingTextProps>) {
  return (
    <motion.div
      className={cn(className)}
      animate={{ opacity: [0.4, 1, 0.4] }}
      transition={{
        duration: duration ?? DEFAULT_PULSE_DURATION,
        repeat: Infinity,
        ease: "easeInOut",
      }}
    >
      {children}
    </motion.div>
  );
}
