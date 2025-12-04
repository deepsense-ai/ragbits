import { render, screen, waitFor } from "@testing-library/react";
import { describe, it, expect, beforeEach, vi, Mock } from "vitest";
import ChatMessage from "../../src/core/components/ChatMessage/ChatMessage";
import { MessageRole } from "@ragbits/api-client-react";
import { enableMapSet } from "immer";
import { ComponentProps, PropsWithChildren } from "react";
import { Slot } from "../../src/core/components/Slot";

vi.mock("../../src/core/stores/HistoryStore/useHistoryStore", () => {
  return {
    useHistoryStore: vi.fn(),
  };
});

vi.mock("../../src/core/stores/HistoryStore/selectors", () => {
  return {
    useConversationProperty: vi.fn(),
    useMessage: vi.fn(),
    useHistoryActions: vi.fn(() => ({
      sendSilentConfirmation: vi.fn(),
    })),
  };
});

vi.mock("@ragbits/api-client-react", () => {
  return {
    useRagbitsContext: vi.fn(() => ({
      client: {
        // Mock client methods if needed
      },
    })),
    MessageRole: {
      Assistant: "assistant",
      User: "user",
    },
  };
});

import userEvent from "@testing-library/user-event";
import {
  useConversationProperty,
  useMessage,
} from "../../src/core/stores/HistoryStore/selectors";
import { useHistoryStore } from "../../src/core/stores/HistoryStore/useHistoryStore";

function mockStore(
  role: MessageRole,
  isLoading: boolean = false,
  content?: string,
  error?: string,
) {
  (useConversationProperty as unknown as Mock).mockImplementation((selector) =>
    selector({
      lastMessageId: role,
      isLoading,
      history: {},
    }),
  );
  (useHistoryStore as unknown as Mock).mockImplementation((selector) =>
    selector({
      addMessage: vi.fn(),
      actions: {
        sendSilentConfirmation: vi.fn(),
      },
    }),
  );
  (useMessage as Mock).mockImplementation(() => {
    return {
      id: role,
      serverId: role,
      content:
        content ??
        (role === MessageRole.Assistant ? "Hello, world!" : "Hi there!"),
      role,
      references:
        role === MessageRole.Assistant
          ? [
              {
                title: "Example",
                url: "https://example.com",
                content: "Hello, world!",
              },
            ]
          : [],
      error: error ?? null,
      usage: {
        "litellm:gpt4-mini": {
          n_requests: 0,
          estimated_cost: 0,
          prompt_tokens: 0,
          completion_tokens: 0,
          total_tokens: 0,
        },
      },
    };
  });
}

vi.mock("../../src/core/components/Slot.tsx", () => ({
  Slot: ({ name }: ComponentProps<typeof Slot>) => {
    if (name === "message.actions") {
      return (
        <>
          <div data-testid="feedback-form">FeedbackForm</div>
          <div data-testid="usage-button">UsageButton</div>
        </>
      );
    }
    return null;
  },
}));

vi.mock("react-markdown", () => ({
  default: ({ children }: PropsWithChildren) => (
    <div className="markdown-content">{children}</div>
  ),
}));

describe("ChatMessage", () => {
  enableMapSet();
  beforeEach(() => {
    vi.resetModules();
    vi.clearAllMocks();
  });
  describe("assistant role", () => {
    it("is correctly aligned", () => {
      mockStore(MessageRole.Assistant);
      render(<ChatMessage messageId={MessageRole.Assistant} />);
      const wrapper = screen.getByTestId("chat-message-wrapper");
      expect(wrapper).not.toHaveClass("flex-row-reverse");
    });

    it("has correct content", () => {
      mockStore(MessageRole.Assistant);
      render(<ChatMessage messageId={MessageRole.Assistant} />);
      expect(screen.getByText("Hello, world!")).toBeInTheDocument();
      // Check references
      expect(screen.getByText("Example")).toBeInTheDocument();
      expect(screen.getByText("Example")).toHaveAttribute(
        "href",
        "https://example.com",
      );
    });

    it("shows feedback from when enabled", () => {
      mockStore(MessageRole.Assistant);

      render(<ChatMessage messageId={MessageRole.Assistant} />);
      expect(screen.getByTestId("feedback-form")).toBeInTheDocument();
    });

    it("shows usage button when enabled", () => {
      mockStore(MessageRole.Assistant);

      render(<ChatMessage messageId={MessageRole.Assistant} />);
      expect(screen.getByTestId("usage-button")).toBeInTheDocument();
    });

    it("displays loading state for assistant message without content", () => {
      mockStore(MessageRole.Assistant, true, "");
      render(<ChatMessage messageId={MessageRole.Assistant} />);
      expect(screen.getByTestId("loading-indicator")).toBeInTheDocument();
    });

    it("copies content to clipboard when copy button is clicked", async () => {
      mockStore(MessageRole.Assistant);
      render(<ChatMessage messageId={MessageRole.Assistant} />);
      const user = userEvent.setup();
      const copyButton = screen.getByLabelText("Copy message");
      await user.click(copyButton);
      const clipboardText = await navigator.clipboard.readText();
      expect(clipboardText).toBe("Hello, world!");
      await waitFor(async () => {
        expect(await screen.findByText("heroicons:check"));
      });
      await waitFor(
        async () => {
          expect(await screen.findByText("heroicons:clipboard"));
        },
        { timeout: 5000 },
      );
    });

    it("displays error banner when error is present", () => {
      mockStore(MessageRole.Assistant, false, undefined, "An error occurred");
      render(<ChatMessage messageId={MessageRole.Assistant} />);
      expect(screen.getByText("An error occurred")).toBeInTheDocument();
    });
  });

  describe("user role", () => {
    it("is correctly aligned", () => {
      mockStore(MessageRole.User);
      render(<ChatMessage messageId={MessageRole.User} />);
      const wrapper = screen.getByTestId("chat-message-wrapper");
      expect(wrapper).toHaveClass("flex-row-reverse");
    });
    it("has correct content", () => {
      mockStore(MessageRole.User);
      render(<ChatMessage messageId={MessageRole.User} />);
      expect(screen.getByText("Hi there!")).toBeInTheDocument();
    });
  });
});
