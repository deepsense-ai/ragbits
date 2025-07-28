import React from "react";
import { describe, it, expect, afterAll, vi } from "vitest";
import {
  act,
  render,
  renderHook,
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
} from "@ragbits/api-client-react";
import { useConfigContext } from "../src/core/contexts/ConfigContext/useConfigContext";
import { ConfigContextProvider } from "../src/core/contexts/ConfigContext/ConfigContextProvider";
import userEvent from "@testing-library/user-event";
import PromptInput from "../src/core/components/inputs/PromptInput/PromptInput";
import { pluginManager } from "../src/core/utils/plugins/PluginManager";
import { ChatOptionsPlugin } from "../src/plugins/ChatOptionsPlugin";
import { useHistoryStore } from "../src/core/stores/historyStore";
import { enableMapSet } from "immer";
import FeedbackForm from "../src/plugins/FeedbackPlugin/components/FeedbackForm";

const chatResponseTypes: ChatResponseType[] = [
  "text",
  "reference",
  "state_update",
  "message_id",
  "conversation_id",
  "live_update",
  "followup_messages",
] as const;

describe("Integration tests", () => {
  enableMapSet();
  const BASE_URL = "http://127.0.0.1:8000";
  const renderWithHook = <R,>(hook: () => R) => {
    return renderHook(() => hook(), {
      wrapper: ({ children }: { children: React.ReactNode }) => {
        return (
          <RagbitsContextProvider baseUrl={BASE_URL}>
            <ConfigContextProvider>{children}</ConfigContextProvider>
          </RagbitsContextProvider>
        );
      },
    });
  };
  /**
   * This should test all default endpoints from the API
   * using UIs mechanims
   */
  describe("/api/config", () => {
    it("should return config", async () => {
      const { result } = renderWithHook(() => useConfigContext());

      await waitFor(() => {
        expect(result.current).not.toBeNull();
      });

      const config = result.current.config;
      // Customization
      expect(config).toHaveProperty("customization");
      // Debug mode
      expect(config).toHaveProperty("debug_mode");
      expect(typeof config.debug_mode).toBe("boolean");
      // Feedback
      expect(config).toHaveProperty("feedback");

      expect(config.feedback).toHaveProperty("like");
      expect(typeof config.feedback.like.enabled === "boolean").toBe(true);
      expect(config.feedback).toHaveProperty("like");
      expect(
        config.feedback.like.form === null ||
          config.feedback.like.form instanceof Object,
      ).toBe(true);

      expect(config.feedback).toHaveProperty("dislike");
      expect(typeof config.feedback.dislike.enabled === "boolean").toBe(true);
      expect(config.feedback).toHaveProperty("dislike");
      expect(
        config.feedback.dislike.form === null ||
          config.feedback.dislike.form instanceof Object,
      ).toBe(true);
    });
  });

  describe("/api/chat", { timeout: 30000 }, () => {
    describe("should call chat endpoint with correct data", () => {
      const makeStreamRequestSpy = vi.spyOn(
        RagbitsClient.prototype,
        "makeStreamRequest",
      );

      afterAll(() => {
        useHistoryStore.getState().actions.clearHistory();
      });

      it("should call chat endpoint with empty request", async () => {
        await act(() => {
          useHistoryStore.getState().actions.sendMessage("Test message");
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
        );

        await waitFor(
          () => {
            expect(useHistoryStore.getState().isLoading).toBe(false);
          },
          {
            timeout: 20000, // Long timeout because of the sleep between live updates
          },
        );
      });

      it("should call chat endpoint with correct request", async () => {
        await act(() => {
          useHistoryStore.getState().actions.sendMessage("Test message 2");
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
                role: "user",
              },
              { content: expect.any(String), role: "assistant" },
            ],
            message: "Test message 2",
          },
          expect.anything(), // We don't care about callbacks
          expect.anything(), // We don't care about AbortSignal
        );

        await waitFor(
          () => {
            expect(useHistoryStore.getState().isLoading).toBe(false);
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
          followupMessages,
        } = useHistoryStore.getState();
        const WrappedInput = () => (
          <RagbitsContextProvider baseUrl={BASE_URL}>
            <ConfigContextProvider>
              <PromptInput
                isLoading={false}
                submit={sendMessage}
                stopAnswering={stopAnswering}
                followupMessages={followupMessages}
              />
            </ConfigContextProvider>
          </RagbitsContextProvider>
        );

        render(<WrappedInput />);
        const user = userEvent.setup();
        const chatOptionsButton =
          await screen.findByTestId("open-chat-options");
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
                role: "user",
              },
              { content: expect.any(String), role: "assistant" },
              { content: "Test message 2", role: "user" },
              { content: expect.any(String), role: "assistant" },
            ],
            message: "Test message 3",
          },
          expect.anything(), // We don't care about callbacks
          expect.anything(), // We don't care about AbortSignal
        );
        await waitFor(
          () => {
            expect(useHistoryStore.getState().isLoading).toBe(false);
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
              expect(event.type).toBeOneOf(chatResponseTypes);
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
        useHistoryStore.getState().actions.sendMessage("Test message");
      });

      await waitFor(
        () => {
          expect(useHistoryStore.getState().isLoading).toBe(false);
        },
        {
          timeout: 20000, // Long timeout because of the sleep between live updates
        },
      );
    });
  });

  describe("/api/feedback", () => {
    describe("should send correct request based on config", async () => {
      it("handles like form", async () => {
        const feedback = render(<FeedbackForm messageServerId="msg-123" />, {
          wrapper: ({ children }: { children: React.ReactNode }) => {
            return (
              <RagbitsContextProvider baseUrl={BASE_URL}>
                <ConfigContextProvider>{children}</ConfigContextProvider>
              </RagbitsContextProvider>
            );
          },
        });

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
            feedback: "like",
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
        const feedback = render(<FeedbackForm messageServerId="msg-123" />, {
          wrapper: ({ children }: { children: React.ReactNode }) => {
            return (
              <RagbitsContextProvider baseUrl={BASE_URL}>
                <ConfigContextProvider>{children}</ConfigContextProvider>
              </RagbitsContextProvider>
            );
          },
        });
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
            feedback: "dislike",
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
