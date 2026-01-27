import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import PluginWrapper from "../../src/core/utils/plugins/PluginWrapper";
import { ComponentProps } from "react";
import HorizontalActions from "../../src/core/components/inputs/PromptInput/HorizontalActions";
import PromptInput from "../../src/core/components/inputs/PromptInput/PromptInput";
import userEvent from "@testing-library/user-event";
import { ChatMessage } from "../../src/core/types/history";
import { MessageRole } from "@ragbits/api-client";

vi.mock(
  "../../src/core/components/inputs/PromptInput/HorizontalActions.tsx",
  () => ({
    default: ({ isVisible }: ComponentProps<typeof HorizontalActions>) =>
      isVisible ? <div>HorizontalActions</div> : null,
  }),
);

vi.mock("../../src/core/utils/plugins/PluginWrapper.tsx", () => ({
  default: ({ component }: ComponentProps<typeof PluginWrapper>) => (
    <div data-testid="feedback-form" data-plugin={component}>
      {component}
    </div>
  ),
}));

vi.mock("../../src/core/utils/useTextAreaCaretDetection.tsx", () => ({
  useCaretLogicalLineDetection: () => ({
    isCaretInFirstLine: () => true,
    isCaretInLastLine: () => true,
  }),
}));

vi.mock("@ragbits/api-client-react", () => ({
  useRagbitsContext: () => ({
    apiClient: {
      uploadFile: vi.fn(),
    },
  }),
  useRagbitsCall: () => ({
    call: vi.fn(),
    isLoading: false,
  }),
}));

const MOCK_HISTORY: ChatMessage[] = [
  {
    role: MessageRole.User,
    content: "Hello, how are you?",
    id: "1",
  },
  {
    role: MessageRole.Assistant,
    content: "I'm fine, thank you. How can I help you today?",
    id: "2",
  },
  {
    role: MessageRole.User,
    content: "I'm doing well, thanks for asking. What's new?",
    id: "3",
  },
];

describe("PromptInput", () => {
  const sendMessage = vi.fn();
  const stopAnswering = vi.fn();
  describe("renders correctly", () => {
    it("renders with HorizontalActions when followupMessages is not null", () => {
      render(
        <PromptInput
          isLoading={false}
          submit={sendMessage}
          stopAnswering={stopAnswering}
          followupMessages={[]}
        />,
      );

      expect(screen.getByText("HorizontalActions")).toBeInTheDocument();
    });

    it("does not render HorizontalActions when followupMessages is null", () => {
      render(
        <PromptInput
          isLoading={false}
          submit={sendMessage}
          stopAnswering={stopAnswering}
          followupMessages={null}
        />,
      );

      expect(screen.queryByText("HorizontalActions")).not.toBeInTheDocument();
    });

    it("renders with all elements", () => {
      render(
        <PromptInput
          isLoading={false}
          submit={sendMessage}
          stopAnswering={stopAnswering}
          followupMessages={[]}
        />,
      );

      expect(screen.getByTestId("prompt-input-input")).toBeInTheDocument();
      const sendButton = screen.getByTestId("send-message");
      expect(sendButton).toBeInTheDocument();
      expect(sendButton).toBeDisabled();
      expect(screen.getByText("ChatOptionsForm")).toBeInTheDocument();
    });

    describe("renders button with custom icon", () => {
      const customIcon = (text: string) => <div>My {text} Icon</div>;

      it("renders custom send icon", () => {
        render(
          <PromptInput
            isLoading={false}
            submit={sendMessage}
            stopAnswering={stopAnswering}
            followupMessages={[]}
            customSendIcon={customIcon("Send")}
            customStopIcon={customIcon("Stop")}
          />,
        );

        const sendButton = screen.getByTestId("send-message");
        expect(sendButton).toHaveTextContent("My Send Icon");
      });

      it("renders custom stop icon", () => {
        render(
          <PromptInput
            isLoading={true}
            submit={sendMessage}
            stopAnswering={stopAnswering}
            followupMessages={[]}
            customSendIcon={customIcon("Send")}
            customStopIcon={customIcon("Stop")}
          />,
        );

        const stopButton = screen.getByTestId("send-message");
        expect(stopButton).toHaveTextContent("My Stop Icon");
      });
    });

    describe("renders send/stop button based on isLoading prop", () => {
      it("renders send button when isLoading is false", async () => {
        render(
          <PromptInput
            isLoading={false}
            submit={sendMessage}
            stopAnswering={stopAnswering}
            followupMessages={[]}
          />,
        );

        await waitFor(() => {
          expect(
            screen.getByTestId("prompt-input-send-icon"),
          ).toBeInTheDocument();
        });
        expect(
          screen.queryByTestId("prompt-input-stop-icon"),
        ).not.toBeInTheDocument();
      });

      it("renders stop button when isLoading is true", async () => {
        render(
          <PromptInput
            isLoading={true}
            submit={sendMessage}
            stopAnswering={stopAnswering}
            followupMessages={[]}
          />,
        );

        await waitFor(() => {
          expect(
            screen.getByTestId("prompt-input-stop-icon"),
          ).toBeInTheDocument();
        });
        expect(
          screen.queryByTestId("prompt-input-send-icon"),
        ).not.toBeInTheDocument();
      });
    });
  });

  it("calls submit when button is clicked", async () => {
    render(
      <PromptInput
        isLoading={false}
        submit={sendMessage}
        stopAnswering={stopAnswering}
      />,
    );

    const input = screen.getByTestId("prompt-input-input");
    const user = userEvent.setup();
    const testMessage = "Test message";
    await user.type(input, testMessage);
    fireEvent.click(screen.getByTestId("send-message"));
    expect(sendMessage).toHaveBeenCalledWith(testMessage);
  });

  it("calls stopAnswering when button is clicked during loading", async () => {
    render(
      <PromptInput
        isLoading={true}
        submit={sendMessage}
        stopAnswering={stopAnswering}
      />,
    );

    const input = screen.getByTestId("prompt-input-input");
    const user = userEvent.setup();
    const testMessage = "Test message";
    await user.type(input, testMessage);
    fireEvent.click(screen.getByTestId("send-message"));
    expect(stopAnswering).toHaveBeenCalled();
  });

  it('goes to previous user message when "ArrowUp" clicked', async () => {
    render(
      <PromptInput
        isLoading={false}
        submit={sendMessage}
        stopAnswering={stopAnswering}
        history={MOCK_HISTORY}
      />,
    );

    const input = screen.getByTestId("prompt-input-input");
    const user = userEvent.setup();
    await user.type(input, "Test message");
    fireEvent.keyDown(input, { key: "ArrowUp" });
    expect(input).toHaveAttribute("data-value", MOCK_HISTORY[2].content);
    fireEvent.keyDown(input, { key: "ArrowUp" });
    expect(input).toHaveAttribute("data-value", MOCK_HISTORY[0].content);
  });

  it('goes to next user message when "ArrowDown" clicked', async () => {
    render(
      <PromptInput
        isLoading={false}
        submit={sendMessage}
        stopAnswering={stopAnswering}
        history={MOCK_HISTORY}
      />,
    );

    const input = screen.getByTestId("prompt-input-input");
    const user = userEvent.setup();
    const testMessage = "Test message";
    await user.type(input, testMessage);
    fireEvent.keyDown(input, { key: "ArrowUp" });
    fireEvent.keyDown(input, { key: "ArrowUp" });
    fireEvent.keyDown(input, { key: "ArrowDown" });
    expect(input).toHaveAttribute("data-value", MOCK_HISTORY[2].content);
    fireEvent.keyDown(input, { key: "ArrowDown" });
    expect(input).toHaveAttribute("data-value", testMessage);
  });

  it('sends message when "Enter" key is pressed', async () => {
    render(
      <PromptInput
        isLoading={false}
        submit={sendMessage}
        stopAnswering={stopAnswering}
        history={MOCK_HISTORY}
      />,
    );

    const input = screen.getByTestId("prompt-input-input");
    const user = userEvent.setup();
    const testMessage = "Test message";
    await user.type(input, testMessage);
    fireEvent.keyDown(input, { key: "Enter" });
    expect(sendMessage).toHaveBeenCalledWith(testMessage);
  });

  it('call "stopAnswering" function submit during loading', async () => {
    render(
      <PromptInput
        isLoading={true}
        submit={sendMessage}
        stopAnswering={stopAnswering}
        history={MOCK_HISTORY}
      />,
    );

    const input = screen.getByTestId("prompt-input-input");
    const user = userEvent.setup();
    const testMessage = "Test message";
    await user.type(input, testMessage);
    fireEvent.keyDown(input, { key: "Enter" });
    expect(stopAnswering).toHaveBeenCalled();
  });
});
