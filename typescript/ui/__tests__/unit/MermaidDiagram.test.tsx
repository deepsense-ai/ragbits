import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";

// Mock mermaid library
vi.mock("mermaid", () => ({
  default: {
    initialize: vi.fn(),
    render: vi.fn(),
  },
}));

// Mock ThemeContext
vi.mock("../../src/core/contexts/ThemeContext/useThemeContext", () => ({
  useThemeContext: vi.fn(),
}));

// Import after mocks
import MermaidDiagram from "../../src/core/components/ChatMessage/MermaidDiagram";
import { Theme } from "../../src/core/contexts/ThemeContext/ThemeContext";
import mermaid from "mermaid";
import { useThemeContext } from "../../src/core/contexts/ThemeContext/useThemeContext";

describe("MermaidDiagram", () => {
  const validMermaidChart = `graph TD
    A[Start] --> B{Decision}
    B -->|Yes| C[Action 1]
    B -->|No| D[Action 2]`;

  beforeEach(() => {
    vi.clearAllMocks();
    (useThemeContext as ReturnType<typeof vi.fn>).mockReturnValue({
      theme: Theme.LIGHT,
      setTheme: vi.fn(),
    });
  });

  it("renders loading state initially", () => {
    (mermaid.render as ReturnType<typeof vi.fn>).mockImplementation(
      () => new Promise(() => {}), // Never resolves
    );

    const { container } = render(<MermaidDiagram chart={validMermaidChart} />);

    // Check for loading state elements (shimmer animation and icon)
    const loadingContainer = container.querySelector(".bg-default-200");
    expect(loadingContainer).toBeInTheDocument();

    // Check for the chart icon in loading state
    const chartIcon = container.querySelector("svg");
    expect(chartIcon).toBeInTheDocument();
  });

  it("renders valid mermaid diagram", async () => {
    const mockSvg = '<svg id="test-diagram">Test Diagram</svg>';
    (mermaid.render as ReturnType<typeof vi.fn>).mockResolvedValue({
      svg: mockSvg,
    });

    render(<MermaidDiagram chart={validMermaidChart} />);

    await waitFor(() => {
      expect(
        mermaid.initialize as ReturnType<typeof vi.fn>,
      ).toHaveBeenCalledWith(
        expect.objectContaining({
          startOnLoad: false,
          theme: "default",
          securityLevel: "strict",
          fontFamily: "arial, sans-serif",
        }),
      );
    });

    await waitFor(() => {
      expect(mermaid.render as ReturnType<typeof vi.fn>).toHaveBeenCalledWith(
        expect.stringMatching(/^mermaid-/),
        validMermaidChart,
      );
    });

    await waitFor(() => {
      const container = document.querySelector(".mermaid-container");
      expect(container).toBeInTheDocument();
      expect(container?.innerHTML).toContain("Test Diagram");
    });
  });

  it("renders diagram with dark theme", async () => {
    (useThemeContext as ReturnType<typeof vi.fn>).mockReturnValue({
      theme: Theme.DARK,
      setTheme: vi.fn(),
    });

    const mockSvg = '<svg id="test-diagram">Dark Diagram</svg>';
    (mermaid.render as ReturnType<typeof vi.fn>).mockResolvedValue({
      svg: mockSvg,
    });

    render(<MermaidDiagram chart={validMermaidChart} />);

    await waitFor(() => {
      expect(
        mermaid.initialize as ReturnType<typeof vi.fn>,
      ).toHaveBeenCalledWith(
        expect.objectContaining({
          startOnLoad: false,
          theme: "dark",
          securityLevel: "strict",
          fontFamily: "arial, sans-serif",
        }),
      );
    });
  });

  it("displays error for invalid mermaid syntax", async () => {
    const errorMessage = "Parse error on line 1";
    (mermaid.render as ReturnType<typeof vi.fn>).mockRejectedValue(
      new Error(errorMessage),
    );

    const { container } = render(
      <MermaidDiagram chart="invalid mermaid syntax" />,
    );

    await waitFor(() => {
      expect(screen.getByText("Mermaid Syntax Error")).toBeInTheDocument();
      expect(screen.getByText(errorMessage)).toBeInTheDocument();
    });

    // Check for error icon by looking for the SVG element
    const errorIcon = container.querySelector("svg");
    expect(errorIcon).toBeInTheDocument();
  });

  it("handles non-Error exceptions", async () => {
    (mermaid.render as ReturnType<typeof vi.fn>).mockRejectedValue(
      "String error",
    );

    render(<MermaidDiagram chart="invalid" />);

    await waitFor(() => {
      expect(screen.getByText("Mermaid Syntax Error")).toBeInTheDocument();
      expect(screen.getByText("Failed to render diagram")).toBeInTheDocument();
    });
  });

  it("initializes with dark theme when theme context is dark", async () => {
    (useThemeContext as ReturnType<typeof vi.fn>).mockReturnValue({
      theme: Theme.DARK,
      setTheme: vi.fn(),
    });

    const mockSvg = '<svg id="test-diagram-dark">Dark Diagram</svg>';
    (mermaid.render as ReturnType<typeof vi.fn>).mockResolvedValue({
      svg: mockSvg,
    });

    render(<MermaidDiagram chart={validMermaidChart} />);

    await waitFor(() => {
      expect(
        mermaid.initialize as ReturnType<typeof vi.fn>,
      ).toHaveBeenCalledWith(expect.objectContaining({ theme: "dark" }));
    });

    await waitFor(() => {
      const container = document.querySelector(".mermaid-container");
      expect(container).toBeInTheDocument();
      expect(container?.innerHTML).toContain("Dark Diagram");
    });
  });

  it("re-renders when chart content changes", async () => {
    const mockSvg = '<svg id="test-diagram">Test Diagram</svg>';
    (mermaid.render as ReturnType<typeof vi.fn>).mockResolvedValue({
      svg: mockSvg,
    });

    const { rerender } = render(<MermaidDiagram chart={validMermaidChart} />);

    await waitFor(() => {
      expect(mermaid.render as ReturnType<typeof vi.fn>).toHaveBeenCalledTimes(
        1,
      );
    });

    const newChart = "graph LR\n  A --> B";
    rerender(<MermaidDiagram chart={newChart} />);

    await waitFor(() => {
      expect(mermaid.render as ReturnType<typeof vi.fn>).toHaveBeenCalledTimes(
        2,
      );
      expect(mermaid.render as ReturnType<typeof vi.fn>).toHaveBeenCalledWith(
        expect.stringMatching(/^mermaid-/),
        newChart,
      );
    });
  });

  it("generates unique IDs for each instance", async () => {
    const mockSvg = '<svg id="test-diagram">Test Diagram</svg>';
    (mermaid.render as ReturnType<typeof vi.fn>).mockResolvedValue({
      svg: mockSvg,
    });

    render(<MermaidDiagram chart={validMermaidChart} />);
    render(<MermaidDiagram chart={validMermaidChart} />);

    await waitFor(() => {
      expect(mermaid.render as ReturnType<typeof vi.fn>).toHaveBeenCalledTimes(
        2,
      );
    });

    // Get the IDs passed to mermaid.render
    const firstCallId = (mermaid.render as ReturnType<typeof vi.fn>).mock
      .calls[0][0];
    const secondCallId = (mermaid.render as ReturnType<typeof vi.fn>).mock
      .calls[1][0];

    expect(firstCallId).toMatch(/^mermaid-/);
    expect(secondCallId).toMatch(/^mermaid-/);
    expect(firstCallId).not.toBe(secondCallId);
  });

  it("applies custom classNames", async () => {
    const mockSvg = '<svg id="test-diagram">Test Diagram</svg>';
    (mermaid.render as ReturnType<typeof vi.fn>).mockResolvedValue({
      svg: mockSvg,
    });
    const customClass = "custom-class";

    render(
      <MermaidDiagram chart={validMermaidChart} classNames={customClass} />,
    );

    await waitFor(() => {
      const container = document.querySelector(".mermaid-container");
      expect(container).toHaveClass(customClass);
    });
  });
});

// Note: Streaming behavior is tested via integration tests
// The isStreaming prop prevents mermaid diagrams from rendering
// while the message content is being streamed, avoiding errors
// from incomplete mermaid syntax.
