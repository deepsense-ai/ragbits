import { Suspense } from "react";
import { Plugin } from "../../../types/plugins";
import { Skeleton } from "@heroui/react";
import { usePluginManager } from "./usePluginManager";
import { PropsOf } from "../../../types/utility";

interface PluginWrapperProps<
  T extends Plugin,
  C extends keyof T["components"],
> {
  plugin: T;
  component: C;
  componentProps: PropsOf<T["components"][C]>;
  skeletonSize?: { width: string; height: string };
  disableSkeleton?: boolean;
}

const PluginWrapper = <T extends Plugin, C extends keyof T["components"]>({
  plugin,
  component,
  skeletonSize,
  disableSkeleton,
  componentProps,
}: PluginWrapperProps<T, C>) => {
  const managedPlugin = usePluginManager(plugin.name);
  const skeletonStyle = skeletonSize
    ? { width: skeletonSize.width, height: skeletonSize.height }
    : {};

  if (!managedPlugin) {
    return null;
  }

  const Component = managedPlugin.components[component as string];
  try {
    return (
      <Suspense
        fallback={
          disableSkeleton ? null : (
            <Skeleton className="rounded-lg" style={skeletonStyle} />
          )
        }
      >
        {Component ? <Component {...(componentProps || {})} /> : null}
      </Suspense>
    );
  } catch (error) {
    console.error(error);
    return null;
  }
};

export default PluginWrapper;
