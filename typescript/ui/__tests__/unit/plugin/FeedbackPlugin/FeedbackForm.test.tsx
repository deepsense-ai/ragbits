import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, Mock } from "vitest";
import {
  FeedbackType,
  MessageRole,
  RagbitsContextProvider,
  useRagbitsCall,
} from "@ragbits/api-client-react";
import FeedbackForm from "../../../../src/plugins/FeedbackPlugin/components/FeedbackForm";
import { useHistoryActions } from "../../../../src/core/stores/HistoryStore/selectors";
import { useConfigContext } from "../../../../src/core/contexts/ConfigContext/useConfigContext";

vi.mock("../../../../src/core/stores/HistoryStore/selectors", () => ({
  useHistoryActions: vi.fn(() => ({
    mergeExtensions: vi.fn(),
  })),
}));

vi.mock("../../../../src/core/contexts/ConfigContext/useConfigContext", () => ({
  useConfigContext: vi.fn(() => ({
    config: {
      feedback: {
        like: {
          enabled: true,
          form: { title: "Like Feedback", properties: {} },
        },
        dislike: {
          enabled: true,
          form: { title: "Dislike Feedback", properties: {} },
        },
      },
    },
  })),
}));

vi.mock("@ragbits/api-client-react", async (importOriginal) => ({
  ...(await importOriginal()),
  useRagbitsCall: vi.fn(() => ({
    call: vi.fn().mockResolvedValue(undefined),
  })),
}));

vi.mock("../../../../src/core/forms", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../../../../src/core/forms")>()),
  useTransformErrors: vi.fn(() => (errors: unknown) => errors),
}));

const mergeExtensionsMock = vi.fn();
const callMock = vi.fn();
function mockRagbitsCall() {
  (useRagbitsCall as Mock).mockReturnValue({
    call: callMock,
  });
}
function mockActions() {
  (useHistoryActions as Mock).mockReturnValue({
    mergeExtensions: mergeExtensionsMock,
  });
}
function mockConfigContext() {
  (useConfigContext as Mock).mockReturnValue({
    config: {
      feedback: {
        like: { enabled: true, form: null },
        dislike: { enabled: true, form: null },
      },
    },
  });
}

const message = {
  id: "msg-1",
  serverId: "server-1",
  extensions: {},
  role: MessageRole.Assistant,
  content: "Test message",
};

describe("FeedbackForm", () => {
  const user = userEvent.setup();

  const WrappedForm = () => {
    return (
      <RagbitsContextProvider baseUrl="http://localhost">
        <FeedbackForm message={message} />
      </RagbitsContextProvider>
    );
  };

  it("renders like and dislike buttons", () => {
    render(<WrappedForm />);
    expect(screen.getByTestId("feedback-like")).toBeInTheDocument();
    expect(screen.getByTestId("feedback-dislike")).toBeInTheDocument();
  });

  it("opens modal when like button clicked", async () => {
    render(<WrappedForm />);
    await user.click(screen.getByTestId("feedback-like"));

    expect(await screen.findByText(/Like Feedback/i)).toBeInTheDocument();
  });

  it("opens modal when dislike button clicked", async () => {
    render(<WrappedForm />);
    await user.click(screen.getByTestId("feedback-dislike"));

    expect(await screen.findByText(/Dislike Feedback/i)).toBeInTheDocument();
  });

  it("calls mergeExtensions and feedback call on submit", async () => {
    mockActions();
    mockRagbitsCall();

    render(<WrappedForm />);
    await user.click(screen.getByTestId("feedback-like"));
    await user.click(screen.getByTestId("feedback-submit"));

    await waitFor(() => {
      expect(mergeExtensionsMock).toHaveBeenCalledWith(message.id, {
        feedbackType: FeedbackType.Like,
      });
      expect(callMock).toHaveBeenCalledWith({
        body: {
          message_id: message.serverId,
          feedback: FeedbackType.Like,
          payload: {},
        },
      });
    });
  });

  it("closes modal on cancel", async () => {
    render(<WrappedForm />);
    await user.click(screen.getByTestId("feedback-like"));
    const cancelBtn = screen.getByRole("button", {
      name: /Close feedback form/i,
    });
    await user.click(cancelBtn);

    await waitFor(() => {
      expect(screen.queryByText(/Like Feedback/i)).not.toBeInTheDocument();
    });
  });

  it("does not render if schema is null", () => {
    mockConfigContext();
    const { container } = render(<WrappedForm />);
    expect(container.firstChild).toBeNull();
  });
});
