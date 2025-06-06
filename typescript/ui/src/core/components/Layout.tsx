import { Button, cn } from "@heroui/react";
import { Icon } from "@iconify/react";
import { useHistoryContext } from "../../contexts/HistoryContext/useHistoryContext";
import { useThemeContext } from "../../contexts/ThemeContext/useThemeContext";
import { Theme } from "../../contexts/ThemeContext/ThemeContext";
import DelayedTooltip from "./DelayedTooltip";
import { ReactNode } from "react";

interface LayoutProps {
  children: ReactNode;
  title: string;
  subTitle?: string;
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
  classNames,
}: LayoutProps) {
  const { clearHistory, stopAnswering } = useHistoryContext();
  const { setTheme, theme } = useThemeContext();

  const toggleTheme = () => {
    setTheme(theme === Theme.DARK ? Theme.LIGHT : Theme.DARK);
  };

  const resetChat = () => {
    stopAnswering();
    clearHistory();
  };

  return (
    <div
      className={cn(
        "flex h-full min-h-[48rem] justify-center py-4",
        theme === Theme.DARK && "dark",
      )}
    >
      <div className="flex w-full flex-col px-4 sm:max-w-[1200px]">
        <header
          className={cn(
            "flex h-16 min-h-16 items-center justify-between gap-2 rounded-none rounded-t-medium border-small border-divider px-4 py-3",
            classNames?.header,
          )}
        >
          <div className="flex w-full items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-foreground">
              🐰
            </div>
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
          <div className="flex items-center gap-2">
            <DelayedTooltip content="Clear chat" placement="bottom">
              <Button
                isIconOnly
                aria-label="Clear chat"
                variant="ghost"
                onPress={resetChat}
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
              >
                {theme === Theme.DARK ? (
                  <Icon icon="heroicons:sun" />
                ) : (
                  <Icon icon="heroicons:moon" />
                )}
              </Button>
            </DelayedTooltip>
          </div>
        </header>
        <main className="flex h-full overflow-hidden">
          <div
            className={cn(
              "flex h-full w-full flex-col gap-4 rounded-none rounded-b-medium border-0 border-b border-l border-r border-divider py-3",
              classNames?.container,
            )}
          >
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
