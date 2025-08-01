import { useCallback, useState } from "react";
import { Icon } from "@iconify/react";
import { Button, cn } from "@heroui/react";
import { motion } from "framer-motion";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";

import ShimmerText from "../ShimmerText";
import { LiveUpdate } from "@ragbits/api-client-react";

type LiveUpdatesProps = {
  shouldShimmer: boolean;
  liveUpdates: Record<string, LiveUpdate["content"]>;
  classNames?: {
    liveUpdates?: string;
  };
};

export default function LiveUpdates({
  shouldShimmer,
  liveUpdates,
  classNames,
}: LiveUpdatesProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const updates = Object.values(liveUpdates);

  const toggleExpanded = useCallback(() => setIsExpanded((prev) => !prev), []);

  const hasMultipleUpdates = updates.length > 1;
  const lastUpdate = updates[updates.length - 1];
  const earlierUpdates = updates.slice(0, -1);
  const shimmerDuration =
    Math.max((lastUpdate.description ?? "").length, lastUpdate.label.length) /
    10;

  return (
    <div
      className={cn("flex flex-col", hasMultipleUpdates && "cursor-pointer")}
      onClick={toggleExpanded}
    >
      <motion.div
        initial={false}
        animate={{
          height: isExpanded ? "auto" : 0,
          opacity: isExpanded ? 1 : 0,
          marginBottom: isExpanded ? "0.5rem" : 0,
        }}
        transition={{ duration: 0.3, ease: "easeInOut" }}
        style={{ overflow: "hidden" }}
      >
        <div className="flex flex-col gap-2">
          {earlierUpdates.map((update, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, y: -10 }}
              animate={{
                opacity: isExpanded ? 1 : 0,
                y: isExpanded ? 0 : -10,
              }}
              transition={{ duration: 0.3 }}
              style={{ pointerEvents: isExpanded ? "auto" : "none" }}
            >
              <div className="text-default-500">{update.label}</div>
              <Markdown
                className={cn(
                  "markdown-container prose dark:prose-invert text-default-400 max-w-full text-sm",
                  classNames?.liveUpdates,
                )}
                remarkPlugins={[remarkGfm]}
              >
                {update.description}
              </Markdown>
            </motion.div>
          ))}
        </div>
      </motion.div>

      <div className="flex items-center gap-4">
        <div className="relative overflow-hidden bg-transparent">
          {shouldShimmer ? (
            <ShimmerText duration={shimmerDuration}>
              <div>{lastUpdate.label}</div>
              <Markdown
                className={cn(
                  "markdown-container prose dark:prose-invert max-w-full text-sm",
                  classNames?.liveUpdates,
                )}
                remarkPlugins={[remarkGfm]}
              >
                {lastUpdate.description}
              </Markdown>
            </ShimmerText>
          ) : (
            <>
              <div className="text-default-500">{lastUpdate.label}</div>
              <Markdown
                className={cn(
                  "markdown-container prose dark:prose-invert text-default-400 max-w-full text-sm",
                  classNames?.liveUpdates,
                )}
                remarkPlugins={[remarkGfm]}
              >
                {lastUpdate.description}
              </Markdown>
            </>
          )}
        </div>
        {hasMultipleUpdates && (
          <Button
            variant="light"
            isIconOnly
            onPress={toggleExpanded}
            data-testid="live-updates-expand"
          >
            <motion.div
              initial={{ rotate: 0 }}
              animate={{ rotate: isExpanded ? 180 : 0 }}
              transition={{ duration: 0.3 }}
            >
              <Icon icon="heroicons:chevron-down" />
            </motion.div>
          </Button>
        )}
      </div>
    </div>
  );
}
