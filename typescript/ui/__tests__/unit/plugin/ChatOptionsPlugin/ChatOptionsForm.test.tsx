import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, Mock, afterEach } from "vitest";
import ChatOptionsForm from "../../../../src/plugins/ChatOptionsPlugin/components/ChatOptionsForm";
import { useHistoryActions } from "../../../../src/core/stores/HistoryStore/selectors";
import { useConfigContext } from "../../../../src/core/contexts/ConfigContext/useConfigContext";

vi.mock("../../../../src/core/stores/HistoryStore/selectors", () => ({
  useConversationProperty: vi.fn(() => ({})),
  useHistoryActions: vi.fn(() => ({
    setConversationProperties: vi.fn(),
    initializeChatOptions: vi.fn(),
  })),
}));

vi.mock("../../../../src/core/stores/HistoryStore/useHistoryStore", () => ({
  useHistoryStore: vi.fn(() => ({ currentConversation: {} })),
}));

vi.mock("../../../../src/core/contexts/ConfigContext/useConfigContext", () => ({
  useConfigContext: vi.fn(() => ({
    config: {
      user_settings: {
        form: {
          title: "User Settings",
          type: "object",
          properties: { example: { type: "string" } },
        },
      },
    },
  })),
}));

vi.mock("../../../../src/core/forms", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../../../../src/core/forms")>()),
  useTransformErrors: vi.fn(() => (errors: unknown) => errors),
}));

vi.mock("@rjsf/utils/lib/schema/getDefaultFormState", () => ({
  getDefaultBasedOnSchemaType: vi.fn(() => ({ example: "default" })),
}));

const setConversationProperitesMock = vi.fn();
const initializeChatOptionsMock = vi.fn();
function mockActions() {
  (useHistoryActions as Mock).mockReturnValue({
    setConversationProperties: setConversationProperitesMock,
    initializeChatOptions: initializeChatOptionsMock,
  });
}
function mockConfigContext() {
  (useConfigContext as Mock).mockReturnValue({
    config: { user_settings: { form: null } },
  });
}
describe("ChatOptionsForm", () => {
  const user = userEvent.setup();

  afterEach(() => {
    vi.clearAllMocks();
  });

  it("renders open button", () => {
    render(<ChatOptionsForm />);
    const button = screen.getByTestId("open-chat-options");
    expect(button).toBeInTheDocument();
  });

  it("opens modal when button clicked", async () => {
    render(<ChatOptionsForm />);
    await user.click(screen.getByTestId("open-chat-options"));
    expect(await screen.findByText(/User Settings/i)).toBeInTheDocument();
  });

  it("calls setChatOptions on submit", async () => {
    mockActions();
    render(<ChatOptionsForm />);
    await user.click(screen.getByTestId("open-chat-options"));

    await user.click(screen.getByTestId("chat-options-submit"));

    await waitFor(() => {
      expect(setConversationProperitesMock).toHaveBeenCalledWith(
        expect.anything(),
        {
          chatOptions: {},
        },
      );
    });
  });

  it("restores defaults when Restore defaults clicked", async () => {
    mockActions();
    render(<ChatOptionsForm />);
    await user.click(screen.getByTestId("open-chat-options"));

    const restoreBtn = screen.getByRole("button", {
      name: /Restore default user settings/i,
    });
    await user.click(restoreBtn);

    await waitFor(() => {
      expect(setConversationProperitesMock).toHaveBeenCalledWith(
        expect.anything(),
        { chatOptions: { example: "default" } },
      );
    });
  });

  it("closes modal when Cancel clicked", async () => {
    render(<ChatOptionsForm />);
    await user.click(screen.getByTestId("open-chat-options"));

    const cancelBtn = screen.getByRole("button", {
      name: /Close chat options form/i,
    });
    await user.click(cancelBtn);

    await waitFor(() => {
      expect(screen.queryByText(/User Settings/i)).not.toBeInTheDocument();
    });
  });

  it("initializes chat options on mount", async () => {
    render(<ChatOptionsForm />);
    expect(initializeChatOptionsMock).toHaveBeenCalledWith({
      example: "default",
    });
  });

  it("renders nothing if schema is null", () => {
    mockConfigContext();
    const { container } = render(<ChatOptionsForm />);
    expect(container.firstChild).toBeNull();
  });
});
