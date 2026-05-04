import { Spinner, Tooltip } from "@heroui/react";
import { Icon } from "@iconify/react";
import { AnimatePresence, motion } from "framer-motion";
import { useCallback, useEffect, useState } from "react";
import { useRagbitsContext } from "@ragbits/api-client-react";
import { useConfigContext } from "../../../core/contexts/ConfigContext/useConfigContext";

const TOOL_ICONS: Record<string, string> = {
  search_web: "heroicons:globe-alt",
  query_slack: "simple-icons:slack",
  search_drive: "simple-icons:googledrive",
  query_notion: "simple-icons:notion",
  query_wiki: "heroicons:book-open",
  code_interpreter: "heroicons:code-bracket",
  get_current_date: "heroicons:calendar",
  search_people: "heroicons:users",
  search_calendar_events: "simple-icons:googlecalendar",
};

const CATEGORY_ICONS: Record<string, string> = {
  "External Data Sources": "heroicons:globe-alt",
  "Internal Data Sources": "heroicons:circle-stack",
  Utilities: "heroicons:wrench-screwdriver",
  Planning: "heroicons:clipboard-document-list",
};

function stripEmoji(name: string): string {
  return name.replace(/^\p{Extended_Pictographic}️?\s*/u, "");
}

export default function ToolsPanel() {
  const { client } = useRagbitsContext();
  const { config } = useConfigContext();
  const tools = config?.available_tools ?? [];
  const googleIncrementalOAuth = config?.google_incremental_oauth;

  const [grantedScopes, setGrantedScopes] = useState<Set<string>>(new Set());
  const [googleStatusChecked, setGoogleStatusChecked] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  const checkGoogleStatus = useCallback(async () => {
    if (!googleIncrementalOAuth?.enabled) {
      setGoogleStatusChecked(true);
      setIsLoading(false);
      return;
    }
    try {
      const baseUrl = client.getBaseUrl();
      const response = await fetch(`${baseUrl}/api/auth/google/status`, {
        credentials: "include",
      });
      if (response.ok) {
        const data = await response.json();
        setGrantedScopes(new Set<string>(data.granted as string[]));
      }
    } catch {
      // Google OAuth status unavailable, treat as no scopes granted
    } finally {
      setGoogleStatusChecked(true);
      setIsLoading(false);
    }
  }, [client, googleIncrementalOAuth?.enabled]);

  useEffect(() => {
    void checkGoogleStatus();
  }, [checkGoogleStatus]);


  const getConnectUrl = (googleScope: string | null): string | null => {
    if (!googleScope || !googleIncrementalOAuth?.enabled) return null;
    if (grantedScopes.has(googleScope)) return null;
    return `${client.getBaseUrl()}/api/auth/google/connect?scope=${googleScope}`;
  };

  const groupedTools = tools.reduce<
    Record<string, typeof tools>
  >((acc, tool) => {
    if (!acc[tool.category]) acc[tool.category] = [];
    acc[tool.category].push(tool);
    return acc;
  }, {});

  if (tools.length === 0) return null;

  if (isLoading && googleIncrementalOAuth?.enabled) {
    return (
      <div className="flex justify-center py-4">
        <Spinner size="sm" />
      </div>
    );
  }

  return (
    <AnimatePresence>
      <motion.div
        key="tools-panel"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="flex flex-col gap-3"
      >
        <p className="text-small text-foreground truncate leading-5 font-semibold">
          Available Tools
        </p>
        <div className="flex flex-col gap-3 overflow-auto">
          {Object.entries(groupedTools).map(([category, categoryTools]) => (
            <div key={category} className="flex flex-col gap-1">
              <div className="flex items-center gap-1.5 px-1">
                <Icon
                  icon={CATEGORY_ICONS[category] || "heroicons:squares-2x2"}
                  className="text-default-400 h-3 w-3 flex-shrink-0"
                />
                <p className="text-tiny text-default-400 truncate font-medium tracking-wide uppercase">
                  {category}
                </p>
              </div>
              <div className="flex flex-col">
                {categoryTools.map((tool) => {
                  const connectUrl = getConnectUrl(tool.google_scope);
                  const needsConnect = tool.has_access && connectUrl !== null;

                  const tooltipContent = !tool.has_access
                    ? "Restricted — insufficient permissions"
                    : needsConnect
                      ? "Click Connect to grant access"
                      : "Available";

                  const statusDot = !tool.has_access ? "bg-danger" : "bg-success";

                  return (
                    <Tooltip
                      key={tool.tool_id}
                      content={googleStatusChecked ? tooltipContent : "Checking status..."}
                      placement="right"
                      delay={600}
                      closeDelay={0}
                    >
                      <div
                        className={`rounded-medium flex items-center gap-2 px-2 py-1.5 transition-colors ${
                          !tool.has_access
                            ? "opacity-50 hover:bg-danger-50"
                            : "hover:bg-default-100"
                        }`}
                      >
                        <Icon
                          icon={TOOL_ICONS[tool.tool_id] || "heroicons:wrench"}
                          className={`h-4 w-4 flex-shrink-0 ${
                            tool.has_access ? "text-default-500" : "text-default-300"
                          }`}
                        />
                        <span
                          className={`text-small truncate ${
                            tool.has_access ? "text-default-700" : "text-default-400"
                          }`}
                        >
                          {stripEmoji(tool.display_name)}
                        </span>
                        {needsConnect ? (
                          <button
                            onClick={() => {
                              const popup = window.open(
                                connectUrl,
                                "oauth_connect",
                                "width=500,height=650,scrollbars=yes",
                              );
                              const timer = setInterval(() => {
                                if (popup?.closed) {
                                  clearInterval(timer);
                                  void checkGoogleStatus();
                                }
                              }, 500);
                            }}
                            className="ml-auto shrink-0 rounded px-2 py-0.5 text-tiny font-medium text-primary hover:bg-primary-50"
                          >
                            Connect
                          </button>
                        ) : (
                          <div
                            className={`ml-auto h-1.5 w-1.5 flex-shrink-0 rounded-full ${statusDot}`}
                          />
                        )}
                      </div>
                    </Tooltip>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      </motion.div>
    </AnimatePresence>
  );
}
