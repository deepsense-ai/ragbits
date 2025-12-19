import { useLocation, useNavigate } from "react-router";
import { Tabs, Tab } from "@heroui/react";
import { Icon } from "@iconify/react";

const TABS = [
  { key: "runs", label: "Runs", icon: "heroicons:play-circle", path: "/runs" },
  { key: "new", label: "New Run", icon: "heroicons:plus-circle", path: "/new" },
  {
    key: "scenarios",
    label: "Scenarios",
    icon: "heroicons:document-text",
    path: "/scenarios",
  },
  { key: "personas", label: "Personas", icon: "heroicons:user", path: "/personas" },
  {
    key: "playground",
    label: "Playground",
    icon: "heroicons:beaker",
    path: "/playground",
  },
] as const;

export function EvalTabs() {
  const location = useLocation();
  const navigate = useNavigate();

  // Determine active tab from URL
  const getActiveTab = () => {
    const path = location.pathname;
    if (path.startsWith("/runs")) return "runs";
    if (path.startsWith("/new")) return "new";
    if (path.startsWith("/scenarios")) return "scenarios";
    if (path.startsWith("/personas")) return "personas";
    if (path.startsWith("/playground")) return "playground";
    return "runs";
  };

  const handleTabChange = (key: React.Key) => {
    const tab = TABS.find((t) => t.key === key);
    if (tab) {
      navigate(tab.path);
    }
  };

  return (
    <div className="border-b border-divider px-6">
      <Tabs
        selectedKey={getActiveTab()}
        onSelectionChange={handleTabChange}
        variant="underlined"
        classNames={{
          tabList: "gap-6",
          cursor: "bg-primary",
          tab: "px-0 h-12",
        }}
      >
        {TABS.map((tab) => (
          <Tab
            key={tab.key}
            title={
              <div className="flex items-center gap-2">
                <Icon icon={tab.icon} className="text-lg" />
                <span>{tab.label}</span>
              </div>
            }
          />
        ))}
      </Tabs>
    </div>
  );
}
