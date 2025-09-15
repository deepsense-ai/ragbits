import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import ExamplePluginComponent from "../../../../src/plugins/ExamplePlugin/components/ExamplePluginComponent";

describe("ExamplePluginComponent", () => {
  it("renders the heading and paragraph", () => {
    render(<ExamplePluginComponent />);

    expect(
      screen.getByRole("heading", { name: /example plugin/i }),
    ).toBeInTheDocument();
    expect(screen.getByText(/this is an example plugin/i)).toBeInTheDocument();
  });
});
