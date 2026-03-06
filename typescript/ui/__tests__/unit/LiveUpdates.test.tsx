import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ComponentProps } from "react";
import userEvent from "@testing-library/user-event";
import LiveUpdates from "../../src/core/components/ChatMessage/LiveUpdates";
import { ChatMessage } from "../../src/core/types/history";
import PulsingText from "../../src/core/components/PulsingText";

vi.mock("../../src/core/components/PulsingText", () => ({
  default: ({ children }: ComponentProps<typeof PulsingText>) => (
    <div data-testid="pulsing-text">{children}</div>
  ),
}));

describe("LiveUpdates", () => {
  const liveUpdates: ChatMessage["liveUpdates"] = {
    "1": {
      label: "Live update 1",
      description: "Live update 1 description",
    },
    "2": {
      label: "Live update 2",
      description: "Live update 2 description",
    },
  };

  it("renders latest update", () => {
    render(<LiveUpdates shouldShimmer={false} liveUpdates={liveUpdates} />);
    expect(screen.getByText("Live update 2")).toBeInTheDocument();
  });

  it("renders open button", () => {
    render(<LiveUpdates shouldShimmer={false} liveUpdates={liveUpdates} />);
    expect(screen.getByTestId("live-updates-expand")).toBeInTheDocument();
  });

  it("doesn't render open button if there's only one update", () => {
    render(
      <LiveUpdates
        shouldShimmer={false}
        liveUpdates={{
          "1": {
            label: "Live update 1",
            description: "Live update 1 description",
          },
        }}
      />,
    );
    expect(screen.queryByTestId("live-updates-expand")).not.toBeInTheDocument();
  });

  it("shows rest of the updates when expanded", async () => {
    render(<LiveUpdates shouldShimmer={false} liveUpdates={liveUpdates} />);
    const user = userEvent.setup();
    const expandButton = screen.getByTestId("live-updates-expand");
    await user.click(expandButton);
    await waitFor(() => {
      expect(screen.getByText("Live update 1")).toBeVisible();
    });
  });

  it("uses pulsing text when loading", () => {
    render(<LiveUpdates shouldShimmer={true} liveUpdates={liveUpdates} />);
    expect(screen.getByTestId("pulsing-text")).toBeInTheDocument();
  });
});
