import { describe, it, expect, vi } from "vitest";
import HorizontalActions from "../../src/core/components/inputs/PromptInput/HorizontalActions";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

describe("HorizontalActions", () => {
  const MOCK_ACTIONS = ["Action 1", "Action"];
  const sendMessageMock = vi.fn();
  it("renders correctly", async () => {
    render(
      <HorizontalActions
        actions={MOCK_ACTIONS}
        isVisible
        sendMessage={sendMessageMock}
      />,
    );
    expect(screen.getByTestId("horizontal-actions")).toBeInTheDocument();
    MOCK_ACTIONS.forEach((action) => {
      expect(screen.getByText(action)).toBeInTheDocument();
    });
  });

  it("doesn't render when isVisible is false", async () => {
    render(
      <HorizontalActions
        actions={MOCK_ACTIONS}
        isVisible={false}
        sendMessage={sendMessageMock}
      />,
    );
    await waitFor(() =>
      expect(screen.queryByTestId("horizontal-actions")).toBeNull(),
    );
  });

  it("calls sendMessage when a button is clicked", async () => {
    render(
      <HorizontalActions
        actions={MOCK_ACTIONS}
        isVisible
        sendMessage={sendMessageMock}
      />,
    );
    await waitFor(() =>
      expect(screen.getByTestId("horizontal-actions")).toBeInTheDocument(),
    );
    const user = userEvent.setup();
    const button = screen.getByText(MOCK_ACTIONS[0]);
    await user.click(button);
    expect(sendMessageMock).toHaveBeenCalledWith(MOCK_ACTIONS[0]);
  });
});
