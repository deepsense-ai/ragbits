import { render, screen, within, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect } from "vitest";
import { ChatMessage } from "../../../../src/core/types/history";
import UsageButton from "../../../../src/plugins/UsagePlugin/components/UsageButton";

const mockUsage: Exclude<ChatMessage["usage"], undefined> = {
  "gpt-4": {
    n_requests: 2,
    prompt_tokens: 100,
    completion_tokens: 200,
    total_tokens: 300,
    estimated_cost: 0.05,
  },
  "gpt-3.5": {
    n_requests: 1,
    prompt_tokens: 50,
    completion_tokens: 100,
    total_tokens: 150,
    estimated_cost: 0.01,
  },
};

describe("UsageButton", () => {
  const user = userEvent.setup();
  it("renders the info button", () => {
    render(<UsageButton usage={mockUsage} />);
    expect(
      screen.getByRole("button", { name: /open usage details/i }),
    ).toBeInTheDocument();
  });

  it("shows tooltip with summary info on hover", async () => {
    render(<UsageButton usage={mockUsage} />);
    const button = screen.getByRole("button", { name: /open usage details/i });

    await user.tab();

    expect(await screen.findByText(/Prompt tokens/i)).toBeInTheDocument();
    expect(screen.getByText("150")).toBeInTheDocument();
    expect(screen.getByText("300")).toBeInTheDocument();
    expect(screen.getByText("450")).toBeInTheDocument();
    expect(screen.getByText(/0\.06/)).toBeInTheDocument();

    await user.unhover(button);
  });

  it("opens modal with detailed usage table when clicked", async () => {
    render(<UsageButton usage={mockUsage} />);
    await user.click(
      screen.getByRole("button", { name: /open usage details/i }),
    );

    const dialog = await screen.findByRole("dialog");
    expect(within(dialog).getByText(/usage details/i)).toBeInTheDocument();

    const table = within(dialog).getByRole("grid");

    const getRowByFirstCell = (text: string) => {
      const cell = within(table).getByText(text);
      return cell.closest('[role="row"]') || cell.closest("tr");
    };

    const gpt4Row = getRowByFirstCell("gpt-4");
    expect(gpt4Row).toHaveTextContent("2");
    expect(gpt4Row).toHaveTextContent("300");

    const gpt35Row = getRowByFirstCell("gpt-3.5");
    expect(gpt35Row).toHaveTextContent("1");
    expect(gpt35Row).toHaveTextContent("150");

    const totalRow = getRowByFirstCell("Total");
    expect(totalRow).toHaveTextContent("3");
    expect(totalRow).toHaveTextContent("450");
    expect(totalRow).toHaveTextContent("0.06");
  });

  it("closes modal when pressing Escape", async () => {
    render(<UsageButton usage={mockUsage} />);
    await user.click(
      screen.getByRole("button", { name: /open usage details/i }),
    );

    expect(await screen.findByRole("dialog")).toBeInTheDocument();

    await user.keyboard("{Escape}");

    await waitFor(() => {
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    });
  });
});
