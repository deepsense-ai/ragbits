import { useCallback } from "react";
import { Tabs, Tab } from "@heroui/react";
import { Icon } from "@iconify/react";
import { useEvalStore, useEvalStoreApi } from "../../stores/EvalStoreContext";
import { ConversationView } from "./ConversationView";
import { SummaryView } from "./SummaryView";
import type { ViewMode } from "../../types";

export function ResultsContainer() {
  const storeApi = useEvalStoreApi();
  const viewMode = useEvalStore((s) => s.viewMode);
  const selectedScenarioName = useEvalStore((s) => s.selectedScenarioName);

  const handleTabChange = useCallback((key: React.Key) => {
    storeApi.getState().actions.setViewMode(key as ViewMode);
  }, [storeApi]);

  return (
    <div className="flex h-full min-h-0 flex-col">
      {/* View Toggle */}
      <div className="border-b border-divider px-4 py-2">
        <Tabs
          selectedKey={viewMode}
          onSelectionChange={handleTabChange}
          size="sm"
          variant="underlined"
        >
          <Tab
            key="summary"
            title={
              <div className="flex items-center gap-2">
                <Icon icon="heroicons:chart-bar" />
                <span>Summary</span>
              </div>
            }
          />
          <Tab
            key="conversation"
            title={
              <div className="flex items-center gap-2">
                <Icon icon="heroicons:chat-bubble-left-right" />
                <span>Conversation</span>
              </div>
            }
          />
        </Tabs>
      </div>

      {/* Content */}
      <div className="flex-1 min-h-0 overflow-hidden">
        {viewMode === "summary" ? (
          <SummaryView />
        ) : (
          <ConversationView scenarioName={selectedScenarioName} />
        )}
      </div>
    </div>
  );
}
