import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import PulsingText from "../../src/core/components/PulsingText";

describe("PulsingText", () => {
  it("renders children", () => {
    render(<PulsingText>Loading...</PulsingText>);
    expect(screen.getByText("Loading...")).toBeInTheDocument();
  });

  it("applies custom className without hardcoded color", () => {
    const { container } = render(
      <PulsingText className="text-red-500">Test</PulsingText>,
    );
    const wrapper = container.firstChild as HTMLElement;
    expect(wrapper.className).toContain("text-red-500");
    expect(wrapper.className).not.toContain("text-default-500");
  });

  it("does not apply any color class when no className is provided", () => {
    const { container } = render(<PulsingText>Test</PulsingText>);
    const wrapper = container.firstChild as HTMLElement;
    expect(wrapper.className).not.toContain("text-default-500");
  });
});
