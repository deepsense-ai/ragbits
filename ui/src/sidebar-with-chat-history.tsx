import React from "react";
import { Button, Spacer, useDisclosure, cn } from "@heroui/react";
import { Icon } from "@iconify/react";

import SidebarDrawer from "./sidebar-drawer";

/**
 * 💡 TIP: You can use the usePathname hook from Next.js App Router to get the current pathname
 * and use it as the active key for the Sidebar component.
 *
 * ```tsx
 * import {usePathname} from "next/navigation";
 *
 * const pathname = usePathname();
 * const currentPath = pathname.split("/")?.[1]
 *
 * <Sidebar defaultSelectedKey="home" selectedKeys={[currentPath]} />
 * ```
 */

export default function Component({
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
  const { isOpen, onOpen, onOpenChange } = useDisclosure();

  const content = (
    <div className="relative flex h-full w-72 flex-1 flex-col p-6">
      <div className="flex items-center gap-2 px-2">
        <div className="flex h-8 w-8 items-center justify-center rounded-full bg-foreground">
          🐰
        </div>
        <span className="text-base font-bold uppercase leading-6 text-foreground">
          RAGBITS
        </span>
      </div>

      <Spacer y={8} />

      <Button
        fullWidth
        className="mb-6 mt-2 h-[44px] justify-start gap-3 bg-default-foreground px-3 py-[10px] text-default-50"
        startContent={
          <Icon
            className="text-default-50"
            icon="solar:chat-round-dots-linear"
            width={24}
          />
        }
      >
        New Chat
      </Button>
    </div>
  );

  return (
    <div className="flex h-full min-h-[48rem] w-full py-4">
      <SidebarDrawer
        className="h-full flex-none rounded-[14px] bg-default-50"
        isOpen={isOpen}
        onOpenChange={onOpenChange}
      >
        {content}
      </SidebarDrawer>
      <div className="flex w-full flex-col px-4 sm:max-w-[calc(100%_-_288px)]">
        <header
          className={cn(
            "flex h-16 min-h-16 items-center justify-between gap-2 rounded-none rounded-t-medium border-small border-divider px-4 py-3",
            classNames?.["header"],
          )}
        >
          <Button
            isIconOnly
            className="flex sm:hidden"
            size="sm"
            variant="light"
            onPress={onOpen}
          >
            <Icon
              className="text-default-500"
              height={24}
              icon="solar:hamburger-menu-outline"
              width={24}
            />
          </Button>
          {(title || subTitle) && (
            <div className="w-full min-w-[120px] sm:w-auto">
              <div className="truncate text-small font-semibold leading-5 text-foreground">
                {title}
              </div>
              <div className="truncate text-small font-normal leading-5 text-default-500">
                {subTitle}
              </div>
            </div>
          )}
          {header}
        </header>
        <main className="flex h-full">
          <div className="flex h-full w-full flex-col gap-4 rounded-none rounded-b-medium border-0 border-b border-l border-r border-divider py-3">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
