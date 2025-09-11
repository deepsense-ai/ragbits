import React from "react";
import {
  describe,
  it,
  expect,
  afterAll,
  vi,
  beforeEach,
  afterEach,
  Mock,
} from "vitest";
import {
  act,
  render,
  waitFor,
  screen,
  fireEvent,
} from "@testing-library/react";
import {
  RagbitsClient,
  RagbitsContextProvider,
  StreamCallbacks,
  ChatResponse,
  ChatResponseType,
  MessageRole,
  FeedbackType,
} from "@ragbits/api-client-react";
import { ConfigContextProvider } from "../../src/core/contexts/ConfigContext/ConfigContextProvider";
import userEvent from "@testing-library/user-event";
import PromptInput from "../../src/core/components/inputs/PromptInput/PromptInput";
import { pluginManager } from "../../src/core/utils/plugins/PluginManager";
import { ChatOptionsPlugin } from "../../src/plugins/ChatOptionsPlugin";
import FeedbackForm from "../../src/plugins/FeedbackPlugin/components/FeedbackForm";
import { createHistoryStore } from "../../src/core/stores/HistoryStore/historyStore";
import { createStore } from "zustand";
import { useHistoryStore } from "../../src/core/stores/HistoryStore/useHistoryStore";
import { HistoryStore } from "../../src/types/history";

vi.mock("../../src/core/stores/HistoryStore/useHistoryStore", () => {
  return {
    useHistoryStore: vi.fn(),
  };
});

vi.mock("idb-keyval", () => ({
  get: vi.fn(),
  set: vi.fn(),
  del: vi.fn(),
  clear: vi.fn(),
  keys: vi.fn(),
}));

const historyStore = createStore(createHistoryStore);
historyStore.getState()._internal._setHasHydrated(true);

(useHistoryStore as Mock).mockImplementation(
  (selector: (s: HistoryStore) => unknown) => selector(historyStore.getState()),
);

describe("Integration tests", () => {
  const BASE_URL = "http://127.0.0.1:8000";

  describe("/api/chat", { timeout: 30000 }, () => {
    describe("should call chat endpoint with correct data", () => {
      afterAll(() => {
        historyStore.getState().actions.newConversation();
      });

      it("should call chat endpoint with empty request", async () => {
        const makeStreamRequestSpy = vi.spyOn(
          RagbitsClient.prototype,
          "makeStreamRequest",
        );
        await act(() => {
          historyStore.getState().actions.sendMessage("Test message");
        });

        expect(makeStreamRequestSpy).toHaveBeenCalledWith(
          "/api/chat",
          {
            context: {},
            history: [],
            message: "Test message",
          },
          expect.anything(), // We don't care about callbacks
          expect.anything(), // We don't care about AbortSignal
          expect.anything(), // We don't care about headers
        );

        await waitFor(
          () => {
            expect(
              historyStore.getState().primitives.getCurrentConversation()
                .isLoading,
            ).toBe(false);
          },
          {
            timeout: 20000, // Long timeout because of the sleep between live updates
          },
        );
      });

      it("should call chat endpoint with correct request", async () => {
        const makeStreamRequestSpy = vi.spyOn(
          RagbitsClient.prototype,
          "makeStreamRequest",
        );
        await act(() => {
          historyStore.getState().actions.sendMessage("Test message 2");
        });

        expect(makeStreamRequestSpy).toHaveBeenCalledWith(
          "/api/chat",
          {
            context: {
              conversation_id: expect.any(String),
              signature: expect.any(String),
              state: expect.any(Object),
            },
            history: [
              {
                content: "Test message",
                role: MessageRole.User,
              },
              { content: expect.any(String), role: MessageRole.Assistant },
            ],
            message: "Test message 2",
          },
          expect.anything(), // We don't care about callbacks
          expect.anything(), // We don't care about AbortSignal
          expect.anything(), // We don't care about headers
        );

        await waitFor(
          () => {
            expect(
              historyStore.getState().primitives.getCurrentConversation()
                .isLoading,
            ).toBe(false);
          },
          {
            timeout: 20000, // Long timeout because of the sleep between live updates
          },
        );
      });

      it("should call chat endpoint with selected options", async () => {
        pluginManager.register(ChatOptionsPlugin);
        const {
          actions: { sendMessage, stopAnswering },
          primitives: { getCurrentConversation },
        } = historyStore.getState();
        const WrappedInput = () => (
          <RagbitsContextProvider baseUrl={BASE_URL}>
            <ConfigContextProvider>
              <PromptInput
                isLoading={false}
                submit={sendMessage}
                stopAnswering={stopAnswering}
                followupMessages={getCurrentConversation().followupMessages}
              />
            </ConfigContextProvider>
          </RagbitsContextProvider>
        );
        const makeStreamRequestSpy = vi.spyOn(
          RagbitsClient.prototype,
          "makeStreamRequest",
        );

        render(<WrappedInput />);
        const user = userEvent.setup();
        const chatOptionsButton = await screen.findByTestId(
          "open-chat-options",
          undefined,
          {
            timeout: 5000,
          },
        );
        await user.click(chatOptionsButton);
        const selectTrigger = await screen.findByLabelText("Language", {
          selector: "select",
        });
        await user.selectOptions(selectTrigger, ["Polish"]);
        const submitButton = await screen.findByText("Save");
        await user.click(submitButton);

        const input = await screen.findByRole("textbox");
        fireEvent.change(input, { target: { value: "Test message 3" } });

        const sendButton = await screen.findByTestId("send-message");
        await user.click(sendButton);

        expect(makeStreamRequestSpy).toHaveBeenCalledWith(
          "/api/chat",
          {
            context: {
              conversation_id: expect.any(String),
              signature: expect.any(String),
              state: expect.any(Object),
              user_settings: {
                language: "Polish",
              },
            },
            history: [
              {
                content: "Test message",
                role: MessageRole.User,
              },
              { content: expect.any(String), role: MessageRole.Assistant },
              { content: "Test message 2", role: MessageRole.User },
              { content: expect.any(String), role: MessageRole.Assistant },
            ],
            message: "Test message 3",
          },
          expect.anything(), // We don't care about callbacks
          expect.anything(), // We don't care about AbortSignal
          expect.anything(), // We don't care about headers
        );
        await waitFor(
          () => {
            expect(
              historyStore.getState().primitives.getCurrentConversation()
                .isLoading,
            ).toBe(false);
          },
          {
            timeout: 20000, // Long timeout because of the sleep between live updates
          },
        );
      });
    });
    it("should recieve stream of known events", async () => {
      const originalMakeStreamRequest =
        RagbitsClient.prototype.makeStreamRequest;
      vi.spyOn(RagbitsClient.prototype, "makeStreamRequest").mockImplementation(
        function (this: RagbitsClient, endpoint, data, callbacks, signal) {
          const modifiedCallbacks = {
            ...(callbacks as StreamCallbacks<unknown>),
            onMessage: (event: ChatResponse) => {
              expect(Object.values(ChatResponseType)).toContain(event.type);
            },
          };

          return originalMakeStreamRequest.call(
            this,
            endpoint,
            data,
            modifiedCallbacks,
            signal,
          );
        },
      );

      await act(() => {
        historyStore.getState().actions.sendMessage("Test message");
      });

      await waitFor(
        () => {
          expect(
            historyStore.getState().primitives.getCurrentConversation()
              .isLoading,
          ).toBe(false);
        },
        {
          timeout: 20000, // Long timeout because of the sleep between live updates
        },
      );
    });
  });

  describe("/api/feedback", () => {
    describe("should send correct request based on config", async () => {
      let messageId: string = "";
      beforeEach(() => {
        messageId = historyStore
          .getState()
          .primitives.addMessage(historyStore.getState().currentConversation, {
            content: "Mock content",
            role: MessageRole.Assistant,
            serverId: "msg-123",
          });
      });
      afterEach(() => {
        historyStore.getState().actions.newConversation();
      });
      it("handles like form", async () => {
        const feedback = render(
          <FeedbackForm
            message={
              historyStore.getState().primitives.getCurrentConversation()
                .history[messageId]
            }
          />,
          {
            wrapper: ({ children }: { children: React.ReactNode }) => {
              return (
                <RagbitsContextProvider baseUrl={BASE_URL}>
                  <ConfigContextProvider>{children}</ConfigContextProvider>
                </RagbitsContextProvider>
              );
            },
          },
        );

        const makeRequestSpy = vi.spyOn(RagbitsClient.prototype, "makeRequest");
        const user = userEvent.setup();
        const likeButton = await feedback.findByTestId("feedback-like");
        await user.click(likeButton);
        // Find all nodes from example config
        const likeReason = await feedback.findByLabelText("Like Reason");
        await user.type(likeReason, "Example reason");
        // Submit the form
        const submitButton = await feedback.findByTestId("feedback-submit");
        await user.click(submitButton);

        expect(makeRequestSpy).toHaveBeenCalledWith("/api/feedback", {
          body: {
            message_id: "msg-123",
            feedback: FeedbackType.Like,
            payload: {
              like_reason: "Example reason",
            },
          },
          headers: expect.anything(),
          method: "POST",
          signal: expect.anything(),
        });
      });

      it("handles dislike form", async () => {
        const feedback = render(
          <FeedbackForm
            message={
              historyStore.getState().primitives.getCurrentConversation()
                .history[messageId]!
            }
          />,
          {
            wrapper: ({ children }: { children: React.ReactNode }) => {
              return (
                <RagbitsContextProvider baseUrl={BASE_URL}>
                  <ConfigContextProvider>{children}</ConfigContextProvider>
                </RagbitsContextProvider>
              );
            },
          },
        );
        const makeRequestSpy = vi.spyOn(RagbitsClient.prototype, "makeRequest");

        const user = userEvent.setup();
        const dislikeButton = await feedback.findByTestId("feedback-dislike");
        await user.click(dislikeButton);
        const feedbackField = await feedback.findByLabelText("Feedback");
        await user.type(feedbackField, "Example feedback");
        const selectTrigger = await screen.findByLabelText("Issue Type", {
          selector: "select",
        });
        await user.selectOptions(selectTrigger, ["Other"]);
        const submitButton = await feedback.findByTestId("feedback-submit");
        await user.click(submitButton);

        expect(makeRequestSpy).toHaveBeenCalledWith("/api/feedback", {
          body: {
            message_id: "msg-123",
            feedback: FeedbackType.Dislike,
            payload: {
              feedback: "Example feedback",
              issue_type: "Other",
            },
          },
          headers: expect.anything(),
          method: "POST",
          signal: expect.anything(),
        });
      });
    });
  });
});
