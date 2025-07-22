import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import DebugPanel from "../../src/core/components/DebugPanel";
import { ComponentProps } from "react";
import { JsonView } from "react-json-view-lite";
import userEvent from "@testing-library/user-event";

vi.mock("react-json-view-lite", async (importOriginal) => ({
  ...(await importOriginal<typeof import("react-json-view-lite")>()),
  JsonView: ({ data }: ComponentProps<typeof JsonView>) => (
    <div>{JSON.stringify(data)}</div>
  ),
}));

vi.mock("../../src/core/stores/historyStore", () => ({
  useConversationProperty: (
    selector: (s: Record<string, unknown>) => unknown,
  ) =>
    selector({
      history: ["History Section"],
      followupMessages: ["Followup messages Section"],
      eventsLog: [["Events Section"]],
      context: { context_section: "Context Section" },
    }),
  useHistoryStore: (selector: (s: Record<string, unknown>) => unknown) =>
    selector({
      computed: {
        getContext: () => ({ context_section: "Context Section" }),
      },
    }),
}));

describe("DebugPanel", () => {
  const SECTIONS = ["Context", "History", "Followup messages", "Events"];
  it("should render correctly", () => {
    render(<DebugPanel isOpen />);
    expect(screen.getByTestId("debug-panel")).toBeInTheDocument();
    SECTIONS.forEach((section) => {
      expect(screen.getByText(section)).toBeInTheDocument();
    });
  });
  it("doesn't show when isOpen=false", () => {
    render(<DebugPanel isOpen={false} />);
    expect(screen.queryByTestId("debug-panel")).not.toBeInTheDocument();
  });
  it("renders correct data in each section", async () => {
    render(<DebugPanel isOpen />);
    const user = userEvent.setup();
    for (const section of SECTIONS) {
      const sectionTitle = screen.getByText(section);
      await user.click(sectionTitle);
      await waitFor(() => {
        expect(
          section === "Events"
            ? screen.getByText(/Events for response/)
            : screen.getByText(new RegExp(`${section} Section`)),
        ).toBeInTheDocument();
      });
    }
  });
});
