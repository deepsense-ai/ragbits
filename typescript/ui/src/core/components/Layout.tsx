import { Button, cn } from "@heroui/react";
import { Icon } from "@iconify/react";
import { useThemeContext } from "../contexts/ThemeContext/useThemeContext";
import { Theme } from "../contexts/ThemeContext/ThemeContext";
import DelayedTooltip from "./DelayedTooltip";
import { PropsWithChildren, useCallback, useState } from "react";
import { useConfigContext } from "../contexts/ConfigContext/useConfigContext";
import DebugPanel from "./DebugPanel";
import { Slot } from "./Slot";
import { useSlotHasFillers } from "../utils/slots/useSlotHasFillers";
import { useHistoryActions } from "../stores/HistoryStore/selectors";
import { isURL } from "../utils/media";

interface LayoutProps {
  title: string;
  subTitle?: string;
  logo: string;
  classNames?: {
    header?: string;
    title?: string;
    subTitle?: string;
    container?: string;
  };
}

export default function Layout({
  children,
  title,
  subTitle,
  logo,
  classNames,
}: PropsWithChildren<LayoutProps>) {
  const historyEnabled = useSlotHasFillers("layout.sidebar");
  const { config } = useConfigContext();
  const { newConversation: clearHistory, stopAnswering } = useHistoryActions();
  const { setTheme, theme } = useThemeContext();
  const [isDebugOpened, setDebugOpened] = useState(false);

  const toggleTheme = () => {
    setTheme(theme === Theme.DARK ? Theme.LIGHT : Theme.DARK);
  };

  const resetChat = useCallback(() => {
    stopAnswering();
    clearHistory();
  }, [clearHistory, stopAnswering]);

  return (
    <div className="flex h-full min-h-[48rem] justify-center py-4">
      <Slot name="layout.sidebar" disableSkeleton />
      <div
        className={cn(
          "flex grow flex-col px-4 sm:max-w-[1200px]",
          historyEnabled && "pl-0",
        )}
      >
        <header
          className={cn(
            "border-small border-divider flex h-16 min-h-16 items-center justify-between gap-2 rounded-none px-4 py-3",
            classNames?.header,
            historyEnabled ? "rounded-tr-medium" : "rounded-t-medium",
          )}
        >
          <div className="flex w-full items-center gap-2">
            {isURL(logo) ? (
              <img src={logo} className="h-8 w-8" width={32} height={32} />
            ) : (
              <div className="bg-foreground flex h-8 w-8 items-center justify-center rounded-full">
                {logo}
              </div>
            )}
            <div className="w-full min-w-[120px] sm:w-auto">
              <div
                className={cn(
                  "text-small text-foreground truncate leading-5 font-semibold",
                  classNames?.title,
                )}
              >
                {title}
              </div>
              <div
                className={cn(
                  "text-small text-default-500 truncate leading-5 font-normal",
                  classNames?.subTitle,
                )}
              >
                {subTitle}
              </div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Slot
              name="layout.headerActions"
              skeletonSize={{ width: "40px", height: "40px" }}
            />
            {!historyEnabled && (
              <DelayedTooltip content="Clear chat" placement="bottom">
                <Button
                  isIconOnly
                  aria-label="Clear chat"
                  variant="ghost"
                  onPress={resetChat}
                  data-testid="layout-clear-chat-button"
                >
                  <Icon icon="heroicons:arrow-path" />
                </Button>
              </DelayedTooltip>
            )}
            <DelayedTooltip content="Change theme" placement="bottom">
              <Button
                isIconOnly
                aria-label={`Change theme to ${theme === Theme.DARK ? "light" : "dark"}`}
                variant="ghost"
                onPress={toggleTheme}
                data-testid="layout-toggle-theme-button"
              >
                {theme === Theme.DARK ? (
                  <Icon icon="heroicons:sun" />
                ) : (
                  <Icon icon="heroicons:moon" />
                )}
              </Button>
            </DelayedTooltip>
            {config.debug_mode && (
              <DelayedTooltip content="Toggle debug panel" placement="bottom">
                <Button
                  isIconOnly
                  aria-label={`${isDebugOpened ? "Open" : "Close"} debug panel`}
                  variant="ghost"
                  onPress={() => setDebugOpened((o) => !o)}
                  data-testid="layout-debug-button"
                >
                  <Icon icon="heroicons:bug-ant" />
                  {isDebugOpened && (
                    <div className="bg-default-500 absolute top-1/2 right-0 left-0 h-0.5 -rotate-45" />
                  )}
                </Button>
              </DelayedTooltip>
            )}
          </div>
        </header>
        <main className="flex h-full overflow-hidden">
          <div
            className={cn(
              "border-divider flex h-full w-full flex-col gap-4 rounded-none border-0 border-r border-b border-l py-3",
              classNames?.container,
              historyEnabled ? "rounded-br-medium" : "rounded-b-medium",
            )}
          >
            {children}
          </div>
        </main>
      </div>
      <DebugPanel isOpen={isDebugOpened} />
    </div>
  );
}
