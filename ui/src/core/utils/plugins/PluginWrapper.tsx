import { Suspense } from "react";
import { Plugin } from "./PluginManager";
import { Skeleton } from "@heroui/react";
import { usePluginManager } from "./usePluginManager";

interface PluginWrapperProps<T extends Plugin> {
  plugin: T;
  component: keyof T["components"];
  skeletonSize?: { width: string; height: string };
  disableSkeleton?: boolean;
}

const PluginWrapper = <T extends Plugin>({
  plugin,
  component,
  skeletonSize,
  disableSkeleton,
}: PluginWrapperProps<T>) => {
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
        {Component ? <Component /> : null}
      </Suspense>
    );
  } catch (error) {
    console.error(error);
    return null;
  }
};

export default PluginWrapper;
