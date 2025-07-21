import { render, screen } from "@testing-library/react";
import { describe, expect, it, Mock, vi } from "vitest";
import userEvent from "@testing-library/user-event";
import Layout from "../../src/core/components/Layout";
vi.mock("../../src/core/components/DebugPanel", () => ({
  default: ({ isOpen }: { isOpen: boolean }) => (
    <div>isOpen: {JSON.stringify(isOpen)}</div>
  ),
}));

vi.mock("../../src/core/contexts/ConfigContext/useConfigContext", () => {
  return {
    useConfigContext: vi.fn(),
  };
});

vi.mock("../../src/core/contexts/ThemeContext/useThemeContext", () => {
  return {
    useThemeContext: vi.fn(),
  };
});

vi.mock("../../src/core/stores/historyStore", () => {
  return {
    useHistoryActions: vi.fn(),
  };
});

import { useHistoryActions } from "../../src/core/stores/historyStore";
import { useConfigContext } from "../../src/core/contexts/ConfigContext/useConfigContext";
import { useThemeContext } from "../../src/core/contexts/ThemeContext/useThemeContext";
import { Theme } from "../../src/core/contexts/ThemeContext/ThemeContext";

function mockConfig(isDebugEnabled: boolean = false) {
  (useConfigContext as Mock).mockReturnValue({
    config: {
      debug_mode: isDebugEnabled,
    },
  });
}

const setThemeMock = vi.fn();
function mockTheme(theme: Theme) {
  (useThemeContext as Mock).mockReturnValue({
    theme: theme,
    setTheme: setThemeMock,
  });
}

const clearHistoryMock = vi.fn();
const stopAnsweringMock = vi.fn();
(useHistoryActions as Mock).mockReturnValue({
  clearHistory: clearHistoryMock,
  stopAnswering: stopAnsweringMock,
});

describe("Layout", () => {
  it("renders without debug panel", () => {
    mockConfig();
    mockTheme(Theme.LIGHT);
    render(
      <Layout
        title="Custom Title"
        subTitle="Custom Subtitle"
        logo="Custom Logo"
      >
        <div data-testid="children">Children</div>
      </Layout>,
    );
    expect(screen.getByTestId("children")).toBeInTheDocument();
    expect(screen.getByText("Custom Title")).toBeInTheDocument();
    expect(screen.getByText("Custom Subtitle")).toBeInTheDocument();
    expect(screen.getByText("Custom Logo")).toBeInTheDocument();

    expect(screen.getByTestId("layout-clear-chat-button")).toBeInTheDocument();
    expect(
      screen.getByTestId("layout-toggle-theme-button"),
    ).toBeInTheDocument();
    expect(screen.queryByTestId("layout-debug-button")).toBeNull();
  });

  it('renders with debug panel when "debug" is true', () => {
    mockConfig(true);
    mockTheme(Theme.LIGHT);
    render(
      <Layout
        title="Custom Title"
        subTitle="Custom Subtitle"
        logo="Custom Logo"
      >
        <div data-testid="children">Children</div>
      </Layout>,
    );
    expect(screen.getByTestId("children")).toBeInTheDocument();
    expect(screen.getByText("Custom Title")).toBeInTheDocument();
    expect(screen.getByText("Custom Subtitle")).toBeInTheDocument();
    expect(screen.getByText("Custom Logo")).toBeInTheDocument();

    expect(screen.getByTestId("layout-clear-chat-button")).toBeInTheDocument();
    expect(
      screen.getByTestId("layout-toggle-theme-button"),
    ).toBeInTheDocument();
    expect(screen.queryByTestId("layout-debug-button")).toBeDefined();
  });

  it('calls clearHistory and stopAnswering when "clear chat" button is clicked', async () => {
    mockConfig();
    mockTheme(Theme.LIGHT);
    render(
      <Layout
        title="Custom Title"
        subTitle="Custom Subtitle"
        logo="Custom Logo"
      >
        <div data-testid="children">Children</div>
      </Layout>,
    );
    const user = userEvent.setup();
    const clearChatButton = screen.getByTestId("layout-clear-chat-button");
    await user.click(clearChatButton);
    expect(clearHistoryMock).toHaveBeenCalled();
    expect(stopAnsweringMock).toHaveBeenCalled();
  });
  it('calls setTheme when "toggle theme" button is clicked', async () => {
    mockConfig();
    mockTheme(Theme.LIGHT);
    render(
      <Layout
        title="Custom Title"
        subTitle="Custom Subtitle"
        logo="Custom Logo"
      >
        <div data-testid="children">Children</div>
      </Layout>,
    );
    const user = userEvent.setup();
    const toggleThemeButton = screen.getByTestId("layout-toggle-theme-button");
    await user.click(toggleThemeButton);
    expect(setThemeMock).toHaveBeenCalled();
  });
  it('shows debug panel when "debug button" is clicked', async () => {
    mockConfig(true);
    mockTheme(Theme.LIGHT);
    render(
      <Layout
        title="Custom Title"
        subTitle="Custom Subtitle"
        logo="Custom Logo"
      >
        <div data-testid="children">Children</div>
      </Layout>,
    );
    expect(screen.getByText("isOpen: false")).toBeInTheDocument();
    const user = userEvent.setup();
    const debugButton = screen.getByTestId("layout-debug-button");
    await user.click(debugButton);
    expect(screen.getByText("isOpen: true")).toBeInTheDocument();
  });
});
