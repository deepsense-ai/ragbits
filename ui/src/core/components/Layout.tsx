import React from "react";
import { Button, cn } from "@heroui/react";
import { Icon } from "@iconify/react";
import { useHistoryContext } from "../../contexts/HistoryContext/useHistoryContext";
import { useThemeContext } from "../../contexts/ThemeContext/useThemeContext";
import { Theme } from "../../contexts/ThemeContext/ThemeContext";

export default function Layout({
  children,
  header,
  title,
  subTitle,
  classNames = {},
}: {
  children?: React.ReactNode;
  header?: React.ReactNode;
  title?: string;
  subTitle?: string;
  classNames?: Record<string, string>;
}) {
  const { clearMessages } = useHistoryContext();
  const { setTheme, theme } = useThemeContext();

  const toggleTheme = () => {
    setTheme(theme === Theme.DARK ? Theme.LIGHT : Theme.DARK);
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
            classNames?.["header"],
          )}
        >
          {(title || subTitle) && (
            <div className="flex w-full items-center gap-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-foreground">
                🐰
              </div>
              <div className="w-full min-w-[120px] sm:w-auto">
                <div className="truncate text-small font-semibold leading-5 text-foreground">
                  {title}
                </div>
                <div className="truncate text-small font-normal leading-5 text-default-500">
                  {subTitle}
                </div>
              </div>
            </div>
          )}
          {header}
          <div className="flex items-center gap-2">
            <Button
              isIconOnly
              aria-label="Clear chat"
              variant="ghost"
              onPress={clearMessages}
            >
              <Icon icon="heroicons:arrow-path" />
            </Button>
            <Button
              isIconOnly
              aria-label="Clear chat"
              variant="ghost"
              onPress={toggleTheme}
            >
              {theme === Theme.DARK ? (
                <Icon icon="heroicons:sun" />
              ) : (
                <Icon icon="heroicons:moon" />
              )}
            </Button>
          </div>
        </header>
        <main className="flex h-full overflow-hidden">
          <div className="flex h-full w-full flex-col gap-4 rounded-none rounded-b-medium border-0 border-b border-l border-r border-divider py-3">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
