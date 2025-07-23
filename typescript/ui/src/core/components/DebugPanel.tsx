import { AnimatePresence, motion } from "framer-motion";
import { Accordion, AccordionItem } from "@heroui/react";
import { allExpanded, defaultStyles, JsonView } from "react-json-view-lite";
import "react-json-view-lite/dist/index.css";
import { toJSONSafe } from "../utils/json";
import { useHistoryStore } from "../stores/historyStore";
import { useShallow } from "zustand/shallow";

const DEFAULT_STYLES = {
  container:
    "max-w-full overflow-auto rounded bg-default p-2 font-mono font-normal",
  label: `${defaultStyles.label} !text-default-900`,
  collapseIcon: `${defaultStyles.collapseIcon} !text-default-900`,
  expandIcon: `${defaultStyles.expandIcon} !text-default-900`,
  collapsedContent: `${defaultStyles.collapsedContent} !text-default-900`,
  punctuation: `!text-default-900`,
  stringValue: `${defaultStyles.stringValue} !text-green-600`,
  otherValue: `${defaultStyles.otherValue} !text-purple-500`,
  numberValue: `${defaultStyles.numberValue}`,
  nullValue: `${defaultStyles.nullValue}`,
  booleanValue: `${defaultStyles.booleanValue} !text-yellow-600`,
  undefinedValue: `${defaultStyles.undefinedValue}`,
};

interface DebugPanelProps {
  isOpen: boolean;
}

export default function DebugPanel({ isOpen }: DebugPanelProps) {
  const history = useHistoryStore((s) => s.history);
  const followupMessages = useHistoryStore((s) => s.followupMessages);
  const eventsLog = useHistoryStore((s) => s.eventsLog);
  const context = useHistoryStore(useShallow((s) => s.computed.getContext()));

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{
            scale: 0.6,
            opacity: 0,
            width: 0,
          }}
          animate={{
            scale: 1,
            opacity: 1,
            width: "100%",
          }}
          exit={{
            scale: 0.6,
            opacity: 0,
            width: 0,
          }}
          className="w-full max-w-[33%] overflow-hidden"
        >
          <div
            className="rounded-medium border-small border-divider mr-4 h-full overflow-auto"
            data-testid="debug-panel"
          >
            <div className="border-b-small border-divider min-h-16 p-4 text-lg font-bold">
              <span>Debug</span>
            </div>
            <Accordion className="max-h-full">
              <AccordionItem key="context" aria-label="Context" title="Context">
                <div className="max-h-[664px] overflow-auto">
                  <JsonView
                    data={toJSONSafe(context) ?? {}}
                    shouldExpandNode={allExpanded}
                    style={DEFAULT_STYLES}
                  />
                </div>
              </AccordionItem>
              <AccordionItem key="history" aria-label="History" title="History">
                <div className="max-h-[664px] overflow-auto">
                  <JsonView
                    data={toJSONSafe(history) ?? {}}
                    shouldExpandNode={allExpanded}
                    style={DEFAULT_STYLES}
                  />
                </div>
              </AccordionItem>
              <AccordionItem
                key="folowup-messages"
                aria-label="Followup messages"
                title="Followup messages"
              >
                <div className="max-h-[664px] overflow-auto">
                  <JsonView
                    data={toJSONSafe(followupMessages) ?? {}}
                    shouldExpandNode={allExpanded}
                    style={DEFAULT_STYLES}
                  />
                </div>
              </AccordionItem>
              <AccordionItem key="events" aria-label="Events" title="Events">
                {eventsLog.length === 0 ? (
                  <p>No events in the log</p>
                ) : (
                  <Accordion>
                    {eventsLog.map((events, index) => (
                      <AccordionItem
                        key={`events-${index + 1}`}
                        aria-label={`Events for response number ${index + 1}`}
                        title={`Events for response number ${index + 1}`}
                      >
                        <JsonView
                          data={toJSONSafe(events) ?? {}}
                          shouldExpandNode={allExpanded}
                          style={DEFAULT_STYLES}
                        />
                      </AccordionItem>
                    ))}
                  </Accordion>
                )}
              </AccordionItem>
            </Accordion>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
