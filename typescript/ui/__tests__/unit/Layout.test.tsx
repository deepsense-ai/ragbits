import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, Mock, vi, beforeEach, afterEach } from "vitest";
import userEvent from "@testing-library/user-event";
import Layout from "../../src/core/components/Layout";
import { Slot } from "../../src/core/components/Slot";
import { ComponentProps } from "react";

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

// Track whether chat history should be enabled
let chatHistoryEnabled = false;

vi.mock("../../src/core/components/Slot.tsx", () => ({
  Slot: ({ name }: ComponentProps<typeof Slot>) => {
    if (name === "layout.sidebar" && chatHistoryEnabled) {
      return <div>ChatHistory</div>;
    }
    if (name === "layout.headerActions") {
      return <div data-testid="header-actions-slot">HeaderActions</div>;
    }
    return null;
  },
}));

vi.mock("../../src/core/utils/slots/useSlotHasFillers.ts", () => ({
  useSlotHasFillers: (slot: string) => {
    if (slot === "layout.sidebar") {
      return chatHistoryEnabled;
    }
    return false;
  },
}));

import { useConfigContext } from "../../src/core/contexts/ConfigContext/useConfigContext";
import { useThemeContext } from "../../src/core/contexts/ThemeContext/useThemeContext";
import { Theme } from "../../src/core/contexts/ThemeContext/ThemeContext";
import { useHistoryActions } from "../../src/core/stores/HistoryStore/selectors";

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

const newConversationMock = vi.fn();
const stopAnsweringMock = vi.fn();
(useHistoryActions as Mock).mockReturnValue({
  newConversation: newConversationMock,
  stopAnswering: stopAnsweringMock,
});

describe("Layout", () => {
  beforeEach(() => {
    chatHistoryEnabled = false;
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it("renders with chat history", async () => {
    chatHistoryEnabled = true;
    mockConfig(false);
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
    chatHistoryEnabled = false;
    mockConfig(false);
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

    // Chat history should not be present
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
