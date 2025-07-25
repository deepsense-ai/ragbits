import { render, screen, waitFor } from "@testing-library/react";
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

vi.mock("../../src/core/stores/HistoryStore/selectors", () => {
  return {
    useHistoryActions: vi.fn(),
  };
});

vi.mock(
  "../../src/plugins/ChatHistoryPlugin/components/ChatHistory.tsx",
  () => ({
    default: () => <div>ChatHistory</div>,
  }),
);

import { useConfigContext } from "../../src/core/contexts/ConfigContext/useConfigContext";
import { useThemeContext } from "../../src/core/contexts/ThemeContext/useThemeContext";
import { Theme } from "../../src/core/contexts/ThemeContext/ThemeContext";
import { useHistoryActions } from "../../src/core/stores/HistoryStore/selectors";
import { pluginManager } from "../../src/core/utils/plugins/PluginManager";
import {
  ChatHistoryPlugin,
  ChatHistoryPluginName,
} from "../../src/plugins/ChatHistoryPlugin";

function mockConfig(
  isDebugEnabled: boolean = false,
  withClientSideHistory: boolean = false,
) {
  (useConfigContext as Mock).mockReturnValue({
    config: {
      debug_mode: isDebugEnabled,
      conversationHistory: withClientSideHistory,
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
  it("renders with chat history", async () => {
    pluginManager.register(ChatHistoryPlugin);
    pluginManager.activate(ChatHistoryPluginName);
    mockConfig(false, true);
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
    // Chat history
    await waitFor(() => {
      expect(screen.getByText("ChatHistory")).toBeInTheDocument();
      expect(
        screen.queryByTestId("layout-clear-chat-button"),
      ).not.toBeInTheDocument();
    });

    expect(
      screen.getByTestId("layout-toggle-theme-button"),
    ).toBeInTheDocument();
    expect(screen.queryByTestId("layout-debug-button")).toBeNull();
  });
  it("renders without chat history", async () => {
    pluginManager.deactivate(ChatHistoryPluginName);
    mockConfig(false, false);
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
    // Chat history

    // Chat history
    await waitFor(() => {
      expect(screen.queryByText("ChatHistory")).not.toBeInTheDocument();
      expect(
        screen.getByTestId("layout-clear-chat-button"),
      ).toBeInTheDocument();
    });

    expect(
      screen.getByTestId("layout-toggle-theme-button"),
    ).toBeInTheDocument();
    expect(screen.queryByTestId("layout-debug-button")).toBeNull();
  });
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

    expect(
      screen.getByTestId("layout-toggle-theme-button"),
    ).toBeInTheDocument();
    expect(screen.queryByTestId("layout-debug-button")).toBeDefined();
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
