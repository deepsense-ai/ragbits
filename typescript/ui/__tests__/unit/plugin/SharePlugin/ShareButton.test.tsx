import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach, Mock } from "vitest";
import { strToU8, zlibSync, strFromU8 } from "fflate";
import ShareButton from "../../../../src/plugins/SharePlugin/components/ShareButton";
import { useHistoryStore } from "../../../../src/core/stores/HistoryStore/useHistoryStore";

vi.mock("../../../../src/core/stores/HistoryStore/useHistoryStore", () => ({
  useHistoryStore: vi.fn(),
}));

const restoreMock = vi.fn();
function mockHistoryStore() {
  (useHistoryStore as Mock).mockImplementation((selector) =>
    selector({
      primitives: {
        restore: restoreMock,
        getCurrentConversation: vi.fn().mockReturnValue({
          chatOptions: { option: "value" },
          history: [{ role: "user", content: "hi" }],
          serverState: { server: true },
          conversationId: "123",
          followupMessages: [],
        }),
      },
    }),
  );
}

describe("ShareButton", () => {
  const user = userEvent.setup();

  beforeEach(() => {
    restoreMock.mockReset();
    mockHistoryStore();
    Object.defineProperty(navigator, "clipboard", {
      value: {
        writeText: vi.fn(),
        readText: vi.fn(),
      },
      configurable: true,
    });
  });

  it("opens and closes the modal", async () => {
    render(<ShareButton />);
    const button = screen.getByRole("button", { name: /share conversation/i });

    await user.click(button);
    expect(await screen.findByText(/share conversation/i)).toBeInTheDocument();

    await user.click(
      screen.getByRole("button", { name: /close share modal/i }),
    );
    await waitFor(() =>
      expect(screen.queryByText(/share conversation/i)).not.toBeInTheDocument(),
    );
  });

  it("copies encoded state to clipboard and changes icon", async () => {
    render(<ShareButton />);
    const button = screen.getByRole("button", { name: /share conversation/i });

    await user.click(button);
    await user.click(
      screen.getByRole("button", { name: /copy to clipboard/i }),
    );

    expect(navigator.clipboard.writeText).toHaveBeenCalledTimes(1);

    expect(await screen.findByText("heroicons:check")).toBeInTheDocument();
    await waitFor(
      async () =>
        expect(await screen.findByText("heroicons:share")).toBeInTheDocument(),
      {
        timeout: 5000,
      },
    );
  });

  it("restores state from valid pasted clipboard content", async () => {
    render(<ShareButton />);

    const state = {
      chatOptions: { option: "value" },
      history: [{ role: "user", content: "hi" }],
      serverState: { server: true },
      conversationId: "123",
      followupMessages: [],
    };

    const payload = `<RAGBITS-STATE>${JSON.stringify(state)}</RAGBITS-STATE>`;
    const buffer = strToU8(payload);
    const compressed = zlibSync(buffer, { level: 9 });
    const encoded = btoa(strFromU8(compressed, true));
    await userEvent.paste(encoded);

    expect(restoreMock).toHaveBeenCalledWith(
      state.history,
      state.followupMessages,
      state.chatOptions,
      state.serverState,
      state.conversationId,
    );
  });

  it("ignores invalid pasted clipboard content", async () => {
    render(<ShareButton />);
    await userEvent.paste(
      "MTA1LDExMCwxMTgsOTcsMTA4LDEwNSwxMDAsNDUsMTAwLDk3LDExNiw5Nw==",
    ); // string "invalid-data" in base64

    expect(restoreMock).not.toHaveBeenCalled();
  });
});
