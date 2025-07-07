import React from "react";
import { describe, it, expect, beforeAll, afterAll, vi } from "vitest";
import {
  act,
  render,
  renderHook,
  RenderHookResult,
  waitFor,
  screen,
} from "@testing-library/react";
import {
  ChatResponseType,
  MessageRole,
  RagbitsClient,
  RagbitsProvider,
  StreamCallbacks,
  TypedChatResponse,
} from "@ragbits/api-client-react";
import { useConfigContext } from "../core/contexts/ConfigContext/useConfigContext";
import { ConfigContextProvider } from "../core/contexts/ConfigContext/ConfigContextProvider";
import { HistoryContextProvider } from "../core/contexts/HistoryContext/HistoryContextProvider";
import { useHistoryContext } from "../core/contexts/HistoryContext/useHistoryContext";
import { HistoryContext } from "../types/history";
import FeedbackForm from "../plugins/FeedbackPlugin/components/FeedbackForm";
import userEvent from "@testing-library/user-event";

describe("Integration tests", () => {
  const baseUrl = "http://127.0.0.1:8000";
  const renderWithHook = <R,>(hook: () => R) => {
    return renderHook(() => hook(), {
      wrapper: ({ children }: { children: React.ReactNode }) => {
        return (
          <RagbitsProvider baseUrl={baseUrl}>
            <ConfigContextProvider>
              <HistoryContextProvider>{children}</HistoryContextProvider>
            </ConfigContextProvider>
          </RagbitsProvider>
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
      expect(config.feedback.like).toHaveProperty("enabled");
      expect(typeof config.feedback.like.enabled === "boolean").toBe(true);
      expect(config.feedback.like).toHaveProperty("form");
      expect(
        config.feedback.like.form === null ||
          config.feedback.like.form instanceof Object,
      ).toBe(true);

      expect(config.feedback).toHaveProperty("dislike");
      expect(config.feedback.dislike).toHaveProperty("enabled");
      expect(typeof config.feedback.dislike.enabled === "boolean").toBe(true);
      expect(config.feedback.dislike).toHaveProperty("form");
      expect(
        config.feedback.dislike.form === null ||
          config.feedback.dislike.form instanceof Object,
      ).toBe(true);
    });
  });

  describe("/api/chat", { timeout: 30000 }, () => {
    describe("should call chat endpoint with correct data", () => {
      let renderedHistory: RenderHookResult<HistoryContext, null>;
      const makeStreamRequestSpy = vi.spyOn(
        RagbitsClient.prototype,
        "makeStreamRequest",
      );

      beforeAll(() => {
        const rendered = renderWithHook(() => useHistoryContext());
        renderedHistory = rendered;
      });

      afterAll(() => {
        renderedHistory.unmount();
      });

      it("should call chat endpoint with empty request", async () => {
        // Send example message to get context from the server
        const historyContext = renderedHistory.result;
        await waitFor(() => {
          expect(historyContext.current).not.toBeNull();
        });

        await act(() => {
          historyContext.current.sendMessage("Test message");
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
            expect(historyContext.current.isLoading).toBe(false);
          },
          {
            timeout: 20000, // Long timeout because of the sleep between live updates
          },
        );
      });

      it("should call chat endpoint with correct request", async () => {
        const historyContext = renderedHistory.result;
        await act(() => {
          historyContext.current.sendMessage("Test message 2");
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
                role: MessageRole.USER,
              },
              { content: expect.any(String), role: MessageRole.ASSISTANT },
            ],
            message: "Test message 2",
          },
          expect.anything(), // We don't care about callbacks
          expect.anything(), // We don't care about AbortSignal
        );

        await waitFor(
          () => {
            expect(historyContext.current.isLoading).toBe(false);
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
            onMessage: (event: TypedChatResponse) => {
              expect(event.type).toBeOneOf(Object.values(ChatResponseType));
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

      const renderedHistory = renderWithHook(() => useHistoryContext());
      const historyContext = renderedHistory.result;
      await waitFor(() => {
        expect(historyContext.current).not.toBeNull();
      });

      await act(() => {
        historyContext.current.sendMessage("Test message");
      });

      await waitFor(
        () => {
          expect(historyContext.current.isLoading).toBe(false);
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
              <RagbitsProvider baseUrl={baseUrl}>
                <ConfigContextProvider>
                  <HistoryContextProvider>{children}</HistoryContextProvider>
                </ConfigContextProvider>
              </RagbitsProvider>
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
              <RagbitsProvider baseUrl={baseUrl}>
                <ConfigContextProvider>
                  <HistoryContextProvider>{children}</HistoryContextProvider>
                </ConfigContextProvider>
              </RagbitsProvider>
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
