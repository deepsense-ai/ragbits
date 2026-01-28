import { Suspense, useSyncExternalStore, ReactNode, useMemo } from "react";
import { Skeleton } from "@heroui/react";
import { SlotName, SlotPropsMap } from "../types/slots";
import { pluginManager } from "../utils/plugins/PluginManager";

interface SlotProps<S extends SlotName> {
  name: S;
  props?: SlotPropsMap[S];
  fallback?: ReactNode;
  skeletonSize?: { width: string; height: string };
  disableSkeleton?: boolean;
}

export function Slot<S extends SlotName>({
  name,
  props = {} as SlotPropsMap[S],
  fallback,
  skeletonSize,
  disableSkeleton,
}: SlotProps<S>) {
  const fillers = useSyncExternalStore(
    (cb) => pluginManager.subscribe(cb),
    () => pluginManager.getSlotFillers(name),
  );

  const activeFillers = useMemo(
    () => fillers.filter((f) => !f.condition || f.condition()),
    [fillers],
  );

  if (activeFillers.length === 0) {
    return fallback ?? null;
  }

  const skeleton = disableSkeleton ? null : (
    <Skeleton
      className="rounded-lg"
      style={
        skeletonSize
          ? { width: skeletonSize.width, height: skeletonSize.height }
          : undefined
      }
    />
  );

  return (
    <>
      {activeFillers.map((filler, index) => {
        const Component = filler.component;
        return (
          <Suspense key={index} fallback={skeleton}>
            {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
            <Component {...(props as any)} />
          </Suspense>
        );
      })}
    </>
  );
}
