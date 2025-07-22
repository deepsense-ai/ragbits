/**
 * Note: Children components should have `text-transparent` class applied for
 * the shimmer effect to be displayed correctly.
 */

import { cn } from "@heroui/react";
import { motion } from "framer-motion";
import { PropsWithChildren } from "react";

const DEFAULT_SHIMMER_DURATION = 2;

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
      className={cn(
        "relative inline-block bg-gradient-to-r from-neutral-600 via-neutral-200 to-neutral-600 bg-clip-text text-transparent",
        className,
      )}
      initial={{ backgroundPosition: "200% 0%" }}
      animate={{ backgroundPosition: "-200% 0%" }}
      transition={{
        duration: duration ?? DEFAULT_SHIMMER_DURATION,
        repeat: Infinity,
        ease: "linear",
      }}
      style={{
        backgroundSize: "400% 100%",
      }}
    >
      {children}
    </motion.div>
  );
}
