import { Button, cn } from "@heroui/react";
import { Icon } from "@iconify/react";
import { useThemeContext } from "../contexts/ThemeContext/useThemeContext";
import { Theme } from "../contexts/ThemeContext/ThemeContext";
import DelayedTooltip from "./DelayedTooltip";
import { PropsWithChildren, useCallback, useState } from "react";
import { useConfigContext } from "../contexts/ConfigContext/useConfigContext";
import DebugPanel from "./DebugPanel";
import { useHistoryActions } from "../stores/historyStore";
import PluginWrapper from "../utils/plugins/PluginWrapper";
import { SharePlugin } from "../../plugins/SharePlugin";
import ChatHistory from "./ChatHistory";

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
  const { config } = useConfigContext();
  const { clearHistory, stopAnswering } = useHistoryActions();
  const { setTheme, theme } = useThemeContext();
  const [isDebugOpened, setDebugOpened] = useState(false);

  const toggleTheme = () => {
    setTheme(theme === Theme.DARK ? Theme.LIGHT : Theme.DARK);
  };

  const resetChat = useCallback(() => {
    stopAnswering();
    clearHistory();
  }, [clearHistory, stopAnswering]);

  function isURL(input: string): boolean {
    if (isAbsoluteURL(input)) {
      return true;
    }

    return looksLikeRelativeURL(input) && isRelativeURL(input);
  }

  function isAbsoluteURL(str: string): boolean {
    try {
      new URL(str);
      return true;
    } catch {
      return false;
    }
  }

  function isRelativeURL(str: string): boolean {
    try {
      const DUMMY_BASE_URL = "http://base.local";
      new URL(str, DUMMY_BASE_URL);
      return true;
    } catch {
      return false;
    }
  }

  function looksLikeRelativeURL(str: string): boolean {
    // Reject emojis, spaces, and unrelated strings.
    return /^[./~\w%-][\w./~%-]*$/.test(str);
  }

  return (
    <div className="flex h-full min-h-[48rem] justify-center py-4">
      <div className="flex flex-col">
        <header
          className={cn(
            "flex h-16 min-h-16 items-center justify-between gap-2 rounded-none rounded-tl-medium border-small border-r-0 border-divider px-4 py-3",
            classNames?.header,
          )}
        >
          <div className="flex w-full items-center gap-2">
            {isURL(logo) ? (
              <img src={logo} className="h-8 w-8" width={32} height={32} />
            ) : (
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-foreground">
                {logo}
              </div>
            )}
            <div className="w-full min-w-[120px] sm:w-auto">
              <div
                className={cn(
                  "truncate text-small font-semibold leading-5 text-foreground",
                  classNames?.title,
                )}
              >
                {title}
              </div>
              <div
                className={cn(
                  "truncate text-small font-normal leading-5 text-default-500",
                  classNames?.subTitle,
                )}
              >
                {subTitle}
              </div>
            </div>
          </div>
        </header>
        <ChatHistory />
      </div>
      <div className="flex w-full flex-col sm:max-w-[1000px]">
        <div
          className={cn(
            "flex h-16 min-h-16 items-center justify-end gap-2 rounded-none rounded-tr-medium border-small border-l-0 border-divider px-4 py-3",
            classNames?.header,
          )}
        >
          <PluginWrapper
            plugin={SharePlugin}
            component="ShareButton"
            componentProps={undefined}
            skeletonSize={{
              width: "40px",
              height: "40px",
            }}
          />
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
                <div
                  className={cn(
                    "absolute left-0 right-0 top-1/2 h-0.5 -rotate-45 bg-default-500 transition-all",
                    isDebugOpened ? "opacity-100" : "opacity-0",
                  )}
                />
              </Button>
            </DelayedTooltip>
          )}
        </div>
        <main className="flex h-full overflow-hidden">
          <div
            className={cn(
              "flex h-full w-full flex-col gap-4 rounded-none rounded-br-medium border-0 border-b border-l border-r border-divider py-3",
              classNames?.container,
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
