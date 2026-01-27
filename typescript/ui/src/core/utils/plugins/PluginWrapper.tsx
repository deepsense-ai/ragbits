import { Suspense } from "react";
import { Plugin } from "../../types/plugins";
import { Skeleton } from "@heroui/react";
import { usePlugin } from "./usePlugin";
import { PropsOf } from "../../types/utility";
type ComponentProps<T> = T extends undefined
  ? { componentProps?: never }
  : {
      componentProps: T;
    };
type PluginWrapperProps<T extends Plugin, C extends keyof T["components"]> = {
  plugin: T;
  component: C;
  skeletonSize?: { width: string; height: string };
  disableSkeleton?: boolean;
} & ComponentProps<PropsOf<T["components"][C]>>;

const PluginWrapper = <T extends Plugin, C extends keyof T["components"]>({
  plugin,
  component,
  skeletonSize,
  disableSkeleton,
  componentProps,
}: PluginWrapperProps<T, C>) => {
  const managedPlugin = usePlugin(plugin.name);
  const skeletonStyle = skeletonSize
    ? { width: skeletonSize.width, height: skeletonSize.height }
    : {};

  if (!managedPlugin) {
    return null;
  }

  const Component = managedPlugin.config.components[component as string];
  try {
    return (
      <Suspense
        fallback={
          disableSkeleton ? null : (
            <Skeleton className="rounded-lg" style={skeletonStyle} />
          )
        }
      >
        <Component {...(componentProps || {})} />
      </Suspense>
    );
  } catch (error) {
    console.error(error);
    return null;
  }
};

export default PluginWrapper;
