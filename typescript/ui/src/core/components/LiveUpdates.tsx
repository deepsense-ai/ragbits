import { useCallback, useState } from "react";
import { ChatMessage } from "../../types/history";
import { motion } from "framer-motion";
import { Icon } from "@iconify/react";
import { Button } from "@heroui/react";
import ShimmerText from "./ShimmerText";

interface LiveUpdatesProps {
  isLoading: boolean;
  liveUpdates: ChatMessage["liveUpdates"];
}

export default function LiveUpdates({
  isLoading,
  liveUpdates,
}: LiveUpdatesProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const updates = liveUpdates ? Array.from(liveUpdates.values()) : null;

  const toggleExpanded = useCallback(() => setIsExpanded((prev) => !prev), []);

  if (!updates) {
    return null;
  }

  const lastUpdate = updates[updates.length - 1];
  const earlierUpdates = updates.slice(0, -1);
  const shimmerDuration =
    Math.max((lastUpdate.description ?? "").length, lastUpdate.label.length) /
    10;

  return (
    <div className="flex cursor-pointer flex-col" onClick={toggleExpanded}>
      <motion.div
        initial={false}
        animate={{
          height: isExpanded ? "auto" : 0,
          opacity: isExpanded ? 1 : 0,
        }}
        transition={{ duration: 0.3, ease: "easeInOut" }}
        style={{ overflow: "hidden" }}
      >
        <div className="flex flex-col gap-2">
          {earlierUpdates.map((update, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: isExpanded ? 1 : 0, y: isExpanded ? 0 : -10 }}
              transition={{ duration: 0.3 }}
              style={{ pointerEvents: isExpanded ? "auto" : "none" }}
            >
              <div className="text-default-500">{update.label}</div>
              <div className="text-sm text-default-400">
                {update.description}
              </div>
            </motion.div>
          ))}
        </div>
      </motion.div>

      <div className="mt-2 flex items-center justify-between gap-4">
        <div className="relative overflow-hidden bg-transparent">
          {isLoading ? (
            <ShimmerText duration={shimmerDuration}>
              <div>{lastUpdate.label}</div>
              <div className="text-sm">{lastUpdate.description}</div>
            </ShimmerText>
          ) : (
            <>
              <div className="text-default-500">{lastUpdate.label}</div>
              <div className="text-sm text-default-400">
                {lastUpdate.description}
              </div>
            </>
          )}
        </div>
        <motion.div
          className="flex flex-col"
          animate={{ opacity: [1, 0.5, 1] }}
          transition={{ duration: 5, repeat: Infinity }}
        ></motion.div>
        <Button variant="light" isIconOnly onPress={toggleExpanded}>
          <motion.div
            initial={{ rotate: 0 }}
            animate={{ rotate: isExpanded ? 180 : 0 }}
            transition={{ duration: 0.3 }}
          >
            <Icon icon="heroicons:chevron-down" />
          </motion.div>
        </Button>
      </div>
    </div>
  );
}
