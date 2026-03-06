import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import PulsingText from "../../src/core/components/PulsingText";

describe("PulsingText", () => {
  it("renders children", () => {
    render(<PulsingText>Loading...</PulsingText>);
    expect(screen.getByText("Loading...")).toBeInTheDocument();
  });

  it("applies default text-default-500 class", () => {
    const { container } = render(<PulsingText>Test</PulsingText>);
    const wrapper = container.firstChild as HTMLElement;
    expect(wrapper.className).toContain("text-default-500");
  });

  it("applies custom className alongside default class", () => {
    const { container } = render(
      <PulsingText className="text-red-500">Test</PulsingText>,
    );
    const wrapper = container.firstChild as HTMLElement;
    expect(wrapper.className).toContain("text-red-500");
  });
});
