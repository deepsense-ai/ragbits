import { Icon } from "@iconify/react";

export function PlaygroundTab() {
  return (
    <div className="flex h-full flex-col items-center justify-center text-center p-6">
      <Icon
        icon="heroicons:beaker"
        className="text-6xl text-foreground-300 mb-4"
      />
      <h2 className="text-xl font-semibold text-foreground mb-2">Playground</h2>
      <p className="text-foreground-500 max-w-md">
        Experiment with scenarios and test agent behavior interactively. Run
        individual tasks and see results in real-time.
      </p>
      <p className="text-sm text-foreground-400 mt-4">Coming soon</p>
    </div>
  );
}
