import { render, screen, waitFor } from "@testing-library/react";
import { describe, it, expect, beforeEach, vi, Mock } from "vitest";
import ChatMessage from "../../src/core/components/ChatMessage/ChatMessage";
import { MessageRoleType } from "@ragbits/api-client-react";
import { enableMapSet } from "immer";
import PluginWrapper from "../../src/core/utils/plugins/PluginWrapper";
import { ComponentProps, PropsWithChildren } from "react";

vi.mock("../../src/core/stores/HistoryStore/useHistoryStore", () => {
  return {
    useHistoryStore: vi.fn(),
  };
});

vi.mock("../../src/core/stores/HistoryStore/selectors", () => {
  return {
    useConversationProperty: vi.fn(),
    useMessage: vi.fn(),
  };
});

import userEvent from "@testing-library/user-event";
import {
  useConversationProperty,
  useMessage,
} from "../../src/core/stores/HistoryStore/selectors";
import { useHistoryStore } from "../../src/core/stores/HistoryStore/useHistoryStore";

function mockStore(
  role: MessageRoleType,
  isLoading: boolean = false,
  content?: string,
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
    }),
  );
  (useMessage as Mock).mockImplementation(() => {
    return {
      id: role,
      serverId: role,
      content:
        content ?? (role === "assistant" ? "Hello, world!" : "Hi there!"),
      role,
      references:
        role === "assistant"
          ? [
              {
                title: "Example",
                url: "https://example.com",
                content: "Hello, world!",
              },
            ]
          : [],
    };
  });
}

vi.mock("../../src/core/utils/plugins/PluginWrapper.tsx", () => ({
  default: ({ component }: ComponentProps<typeof PluginWrapper>) => (
    <div data-testid="feedback-form" data-plugin={component}>
      {component}
    </div>
  ),
}));

vi.mock("../DelayedTooltip.tsx", () => ({
  DelayedTooltip: ({ children }: PropsWithChildren) => children,
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
      mockStore("assistant");
      render(<ChatMessage messageId="assistant" />);
      const wrapper = screen.getByTestId("chat-message-wrapper");
      expect(wrapper).not.toHaveClass("flex-row-reverse");
    });

    it("has correct content", () => {
      mockStore("assistant");
      render(<ChatMessage messageId="assistant" />);
      expect(screen.getByText("Hello, world!")).toBeInTheDocument();
      // Check references
      expect(screen.getByText("Example")).toBeInTheDocument();
      expect(screen.getByText("Example")).toHaveAttribute(
        "href",
        "https://example.com",
      );
    });

    it("shows feedback from when enabled", () => {
      mockStore("assistant");
      vi.mock(
        "../../src/core/contexts/ConfigContex/useConfigContext.tsx",
        () => ({
          config: {
            feedback: {
              like: {
                enabled: true,
                form: null,
              },
              dislike: {
                enabled: true,
                form: null,
              },
            },
          },
        }),
      );

      render(<ChatMessage messageId="assistant" />);
      expect(screen.getByTestId("feedback-form")).toBeInTheDocument();
    });

    it("displays loading state for assistant message without content", () => {
      mockStore("assistant", true, "");
      render(<ChatMessage messageId="assistant" />);
      expect(screen.getByTestId("loading-indicator")).toBeInTheDocument();
    });

    it("copies content to clipboard when copy button is clicked", async () => {
      mockStore("assistant");
      render(<ChatMessage messageId="assistant" />);
      const user = userEvent.setup();
      const copyButton = screen.getByLabelText("Copy message");
      await user.click(copyButton);
      const clipboardText = await navigator.clipboard.readText();
      expect(clipboardText).toBe("Hello, world!");
      await waitFor(async () => {
        expect(
          await screen.findByTestId("chat-message-copy-icon"),
        ).toHaveAttribute("data-icon", "heroicons:check");
      });
      // Not waiting for the icon to change due to current bug with fake timers and userEvent
      // https://github.com/testing-library/user-event/issues/1115
    });
  });

  describe("user role", () => {
    it("is correctly aligned", () => {
      mockStore("user");
      render(<ChatMessage messageId="user" />);
      const wrapper = screen.getByTestId("chat-message-wrapper");
      expect(wrapper).toHaveClass("flex-row-reverse");
    });
    it("has correct content", () => {
      mockStore("user");
      render(<ChatMessage messageId="user" />);
      expect(screen.getByText("Hi there!")).toBeInTheDocument();
    });
  });
});
