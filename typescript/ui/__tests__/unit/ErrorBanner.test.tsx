import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import userEvent from "@testing-library/user-event";
import ErrorBanner from "../../src/core/components/ErrorBanner";

describe("ErrorBanner", () => {
  it("renders the error message", () => {
    render(<ErrorBanner message="Something went wrong" onDismiss={() => {}} />);

    expect(screen.getByText("Something went wrong")).toBeInTheDocument();
  });

  it("renders the dismiss button", () => {
    render(<ErrorBanner message="Test error" onDismiss={() => {}} />);

    expect(screen.getByLabelText("Dismiss error")).toBeInTheDocument();
  });

  it("calls onDismiss when dismiss button is clicked", async () => {
    const onDismiss = vi.fn();
    render(<ErrorBanner message="Test error" onDismiss={onDismiss} />);

    const user = userEvent.setup();
    await user.click(screen.getByLabelText("Dismiss error"));

    expect(onDismiss).toHaveBeenCalledOnce();
  });

  it("has the correct test id", () => {
    render(<ErrorBanner message="Test" onDismiss={() => {}} />);

    expect(screen.getByTestId("error-banner")).toBeInTheDocument();
  });

  it("has role alert for accessibility", () => {
    render(<ErrorBanner message="Test" onDismiss={() => {}} />);

    expect(screen.getByRole("alert")).toBeInTheDocument();
  });

  it("applies custom className", () => {
    render(
      <ErrorBanner
        message="Test"
        onDismiss={() => {}}
        className="custom-class"
      />,
    );

    expect(screen.getByTestId("error-banner")).toHaveClass("custom-class");
  });
});
