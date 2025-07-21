import { ScrollShadow, cn, Button } from "@heroui/react";
import { AnimatePresence, motion } from "framer-motion";

interface HorizontalActionsProps {
  actions: string[];
  isVisible: boolean;
  sendMessage: (text: string) => void;
}

export default function HorizontalActions({
  isVisible,
  actions,
  sendMessage,
}: HorizontalActionsProps) {
  return (
    <AnimatePresence>
      {isVisible && (
        <motion.div
          key="horizontal-actions"
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ overflow: "hidden", opacity: 0, height: 0 }}
          transition={{
            type: "tween",
            ease: "easeInOut",
            duration: 0.3,
          }}
        >
          <ScrollShadow
            className={cn("flex flex-nowrap gap-2 py-2 transition-all")}
            orientation="horizontal"
            role="group"
            aria-label="Predefined message actions"
            aria-roledescription="Horizontal scrollable list"
            data-testid="horizontal-actions"
          >
            <div className="m-auto flex gap-2">
              {actions.map((text, index) => (
                <Button
                  key={index}
                  className="flex"
                  variant="flat"
                  onPress={() => sendMessage(text)}
                  aria-label={`Send message: ${text}`}
                >
                  <p>{text}</p>
                </Button>
              ))}
            </div>
          </ScrollShadow>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
