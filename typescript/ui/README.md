# Ragbits UI

A modern, responsive chat interface built with React, TypeScript, and Vite for the Ragbits conversational AI platform.

## Overview

The Ragbits UI is a sophisticated chat interface that provides a seamless conversational experience with AI agents. Built with modern web technologies, it features a clean design, real-time messaging, markdown support, and extensible plugin architecture.

## Features

- **Real-time Chat Interface**: Smooth, responsive chat experience with auto-scrolling and message history
- **Markdown Support**: Rich text rendering with GitHub Flavored Markdown (GFM) support
- **Theme Support**: Light and dark theme switching with HeroUI components
- **Plugin Architecture**: Extensible plugin system for custom functionality
- **Customizable Branding**: Configurable logo, title, and welcome messages
- **Follow-up Messages**: AI-suggested follow-up questions for better conversation flow
- **Loading States**: Visual feedback during message processing
- **Responsive Design**: Optimized for desktop and mobile devices

## Tech Stack

- **Framework**: React 18.3 with TypeScript
- **Build Tool**: Vite 6.3
- **UI Components**: HeroUI React 2.6
- **Styling**: Tailwind CSS 3.4 with PostCSS
- **Icons**: Heroicons and Iconify
- **Forms**: React Hook Form with Zod validation
- **Markdown**: React Markdown with remark-gfm
- **Animations**: Framer Motion
- **Code Quality**: ESLint, Prettier, TypeScript

## Project Structure

```
src/
├── core/
│   ├── components/     # Reusable UI components
│   ├── contexts/       # React contexts for state management
│   └── utils/          # Utility functions
├── plugins/            # Plugin system
│   ├── ExamplePlugin/  # Example plugin implementation
│   └── FeedbackPlugin/ # Feedback collection plugin
├── types/              # TypeScript type definitions
├── App.tsx            # Main application component
├── config.ts          # Default configuration (can be overriden by response from `/api/config`)
├── globals.css        # Global styles
└── main.tsx          # Application entry point
```

## Getting Started

### Prerequisites

- Node.js 18+
- npm or yarn

### Installation

1. Install dependencies:

```bash
npm install
```

2. (Optional) create env file:

```bash
cp .env.example .env.development
```

and edit `VITE_API_URL` to point to your local server.

3. Start the development server:

```bash
npm run dev
```

3. Open your browser and navigate to `http://localhost:5173`

### Available Scripts

- `npm run dev` - Start development server with hot reload
- `npm run build` - Build for production
- `npm run preview` - Preview production build
- `npm run lint` - Run ESLint
- `npm run format` - Format code with Prettier
- `npm run format:check` - Check code formatting

## Using Decoupled Components in Your Project

The UI components are designed to be decoupled and reusable in external projects. This section explains how to integrate them into a new application.

### Required Packages

Copy the dependencies from this project's `package.json`. The key packages are:

**UI & Styling:**

```json
{
  "@heroui/react": "^2.8.1",
  "@heroicons/react": "^2.2.0",
  "framer-motion": "^12.23.6",
  "tailwindcss": "^4.1.11",
  "@tailwindcss/postcss": "^4.1.11",
  "@tailwindcss/vite": "^4.1.11",
  "@tailwindcss/typography": "^0.5.16"
}
```

**Core Dependencies:**

```json
{
  "@ragbits/api-client-react": "*",
  "react": "^18.3.1",
  "react-dom": "^18.3.1",
  "react-router": "^7.7.1",
  "zustand": "^5.0.6",
  "immer": "^10.1.1",
  "uuid": "^11.1.0"
}
```

For the complete list, reference this project's `package.json`.

### Provider Hierarchy

Set up your application with the following provider structure:

```tsx
import { StrictMode } from "react";
import { HeroUIProvider } from "@heroui/react";
import { RagbitsContextProvider } from "@ragbits/api-client-react";
import { ThemeContextProvider } from "./core/contexts/ThemeContext/ThemeContextProvider";
import HistoryStoreContextProvider from "./core/stores/HistoryStore/HistoryStoreContextProvider";
import App from "./App";

const API_URL = "https://your-api.com";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <HeroUIProvider>
      <RagbitsContextProvider baseUrl={API_URL}>
        <ThemeContextProvider>
          <HistoryStoreContextProvider>
            <div className="bg-background flex h-screen w-screen items-start justify-center">
              <div className="h-full w-full max-w-full">
                <App />
              </div>
            </div>
          </HistoryStoreContextProvider>
        </ThemeContextProvider>
      </RagbitsContextProvider>
    </HeroUIProvider>
  </StrictMode>,
);
```

#### Provider Descriptions

| Provider                      | Purpose                                                          |
| ----------------------------- | ---------------------------------------------------------------- |
| `HeroUIProvider`              | HeroUI component library context for theming and accessibility   |
| `RagbitsContextProvider`      | Provides the Ragbits API client with the configured base URL     |
| `ThemeContextProvider`        | Manages light/dark theme switching with localStorage persistence |
| `HistoryStoreContextProvider` | Manages chat history and conversation state                      |

### Setting Up Styles

#### 1. Copy `globals.css`

Copy the `src/globals.css` file to your project and import it in your entry point:

```css
@import "tailwindcss";
@plugin "@tailwindcss/typography";
@plugin "../hero.ts";

/* NOTE: Update this path based on your project structure */
@source "../../../node_modules/@heroui/theme/dist/**/*.{js,ts,jsx,tsx}";
@custom-variant dark (&:is(.dark *));

@theme {
  --breakpoint-xs: 28rem;
  --animate-pop-in: pop-in 0.2s ease-out forwards;

  @keyframes pop-in {
    0% {
      transform: scale(0.8);
      opacity: 0;
    }
    100% {
      transform: scale(1);
      opacity: 1;
    }
  }
}

.markdown-container code::before,
.markdown-container code::after {
  content: none;
}

.prose {
  overflow-wrap: break-word;
}
```

#### 2. Update HeroUI Theme Path

**Important:** The `@source` directive path may need to be updated based on your project structure:

```css
/* Original path (for this project's structure) */
@source "../../../node_modules/@heroui/theme/dist/**/*.{js,ts,jsx,tsx}";

/* Example: If globals.css is in src/ */
@source "../node_modules/@heroui/theme/dist/**/*.{js,ts,jsx,tsx}";

/* Example: If globals.css is in src/styles/ */
@source "../../node_modules/@heroui/theme/dist/**/*.{js,ts,jsx,tsx}";
```

#### 3. Copy HeroUI Plugin

Copy the `hero.ts` file to your project root (or update the `@plugin` path in `globals.css`):

```typescript
// hero.ts
import { heroui } from "@heroui/react";
export default heroui();
```

### Using the `storeInitializer` Prop

The `HistoryStoreContextProvider` accepts a `storeInitializer` prop for dependency injection, allowing you to customize the store behavior:

```tsx
import HistoryStoreContextProvider from "./core/stores/HistoryStore/HistoryStoreContextProvider";
import { createStore } from "zustand";
import { immer } from "zustand/middleware/immer";

// Create a custom store initializer
const createCustomHistoryStore = immer((set, get) => ({
  // ... your custom store implementation
  conversations: {},
  currentConversation: "default",

  actions: {
    sendMessage: async (text, ragbitsClient) => {
      // Custom message handling logic
      const response = await myCustomAPI.chat(text);
      // Update state...
    },
    newConversation: () => {
      // Custom conversation creation
    },
    // ... other actions
  },

  primitives: {
    getCurrentConversation: () =>
      get().conversations[get().currentConversation],
    addMessage: (conversationId, message) => {
      // Add message to conversation
    },
    // ... other primitives
  },

  _internal: {
    _hasHydrated: true,
    _setHasHydrated: () => {},
    handleResponse: () => {},
  },
}));

// Use your custom initializer
<HistoryStoreContextProvider storeInitializer={createCustomHistoryStore}>
  <App />
</HistoryStoreContextProvider>;
```

#### Store Initializer Interface

The store must implement the `HistoryStore` interface:

```typescript
interface HistoryStore {
  conversations: Record<string, Conversation>;
  currentConversation: string;

  computed: {
    getContext: () => Record<string, unknown>;
  };

  actions: {
    newConversation: () => string;
    selectConversation: (conversationId: string) => void;
    deleteConversation: (conversationId: string) => void;
    sendMessage: (
      text: string,
      ragbitsClient: RagbitsClient,
      additionalContext?: Record<string, unknown>,
    ) => void;
    stopAnswering: () => void;
    // ... other actions
  };

  primitives: {
    addMessage: (
      conversationId: string,
      message: Omit<ChatMessage, "id">,
    ) => string;
    deleteMessage: (conversationId: string, messageId: string) => void;
    getCurrentConversation: () => Conversation;
    // ... other primitives
  };

  _internal: {
    _hasHydrated: boolean;
    _setHasHydrated: (state: boolean) => void;
    handleResponse: (conversationIdRef, messageId, response) => void;
  };
}
```

#### Waiting for Hydration

If your store needs async initialization (e.g., loading from IndexedDB), use the `waitForHydration` prop:

```tsx
<HistoryStoreContextProvider
  storeInitializer={createPersistentStore}
  waitForHydration={true}
>
  {/* App will show loading screen until store is hydrated */}
  <App />
</HistoryStoreContextProvider>
```

### Minimal Setup (Without Custom Store)

For basic usage, `HistoryStoreContextProvider` provides a minimal in-memory store by default:

```tsx
<HistoryStoreContextProvider>
  {/* Uses built-in minimal store */}
  <App />
</HistoryStoreContextProvider>
```

This minimal store:

- Stores conversations in memory only (no persistence)
- Provides basic conversation management
- Does not make API calls (you need to handle that separately)

### Using History Store Hooks

Access the store in your components:

```typescript
import { useHistoryStore, useHistoryActions } from "./core/stores/HistoryStore/selectors";

function ChatComponent() {
  // Get actions
  const { sendMessage, newConversation, stopAnswering } = useHistoryActions();

  // Get current conversation messages
  const messages = useHistoryStore((s) =>
    Object.values(s.primitives.getCurrentConversation().history)
  );

  // Get specific state
  const currentConversationId = useHistoryStore((s) => s.currentConversation);

  return (
    <div>
      {messages.map((msg) => (
        <Message key={msg.id} message={msg} />
      ))}
      <button onClick={() => sendMessage("Hello!", ragbitsClient)}>
        Send
      </button>
    </div>
  );
}
```

### What Works in Standalone Mode

- Chat input and message display
- Theme switching (light/dark)
- Basic conversation flow
- Custom store implementations
- Core UI components

### What Requires Additional Setup

- **Plugins**: Need explicit registration and activation
- **Conversation persistence**: Requires custom store with IndexedDB
- **Config-based customization**: Requires `ConfigContextProvider`
- **Authentication**: Requires `AuthPlugin` activation

## Plugin System

The UI supports a powerful plugin architecture for extending functionality. Plugins can inject components into predefined UI slots, add routes, wrap existing routes, and run lifecycle hooks.

### Plugin Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     Plugin Registration                      │
│         pluginManager.register(myPlugin)                     │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                  Plugin Activation                           │
│         pluginManager.activate(pluginName)                   │
└──────────────────────┬──────────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        ▼              ▼              ▼
  ┌─────────────┐ ┌────────────┐ ┌──────────────┐
  │ Register    │ │ Inject     │ │ Call         │
  │ Slots       │ │ Routes     │ │ onActivate   │
  └─────────────┘ └────────────┘ └──────────────┘
```

### Creating a Plugin

Use the `createPlugin` helper function to define a type-safe plugin:

```typescript
// src/plugins/MyPlugin/index.tsx
import { lazy } from "react";
import { createPlugin } from "../../core/utils/plugins/utils";

// Lazy-load components for code splitting
const MyButton = lazy(() => import("./components/MyButton"));
const MyPanel = lazy(() => import("./components/MyPanel"));

export const MyPluginName = "MyPlugin";

export const MyPlugin = createPlugin({
  name: MyPluginName,

  // Components available for use with PluginWrapper
  components: {
    MyButton,
    MyPanel,
  },

  // Lifecycle hooks
  onActivate: () => {
    console.log("MyPlugin activated");
  },
  onDeactivate: () => {
    console.log("MyPlugin deactivated");
  },

  // UI slot attachments
  slots: [
    {
      slot: "layout.headerActions",
      component: MyButton,
      priority: 5, // Higher priority = rendered first
      condition: () => true, // Optional: dynamic visibility
    },
  ],

  // Route definitions
  routes: [
    {
      path: "/my-feature",
      element: <MyFeatureRoute />,
    },
  ],

  // Route wrappers
  routeWrappers: [
    {
      target: "/", // Or "global" for all routes
      wrapper: (children) => <MyWrapper>{children}</MyWrapper>,
    },
  ],

  // Custom metadata
  metadata: {
    version: "1.0.0",
    author: "Your Name",
  },
});
```

### Plugin Interface

```typescript
interface Plugin<T> {
  name: string;
  components: T; // Record of lazy-loaded components
  onActivate?: () => void;
  onDeactivate?: () => void;
  routes?: PluginRoute[];
  routeWrappers?: PluginRouteWrapper[];
  slots?: PluginSlot[];
  metadata?: Record<string, unknown>;
}
```

### Defining and Using Slots

Slots are predefined UI extension points where plugins can inject components.

#### Available Slots

| Slot Name              | Location                   | Props                            |
| ---------------------- | -------------------------- | -------------------------------- |
| `layout.sidebar`       | Left sidebar area          | None                             |
| `layout.headerActions` | Header action buttons      | None                             |
| `message.actions`      | Per-message action buttons | `{ message, content, serverId }` |
| `prompt.beforeSend`    | Before the prompt input    | None                             |

#### Attaching to Slots

```typescript
// In your plugin definition
slots: [
  {
    slot: "message.actions",
    component: FeedbackButton,
    priority: 10, // Higher = rendered first
    condition: () => isFeatureEnabled(), // Optional
  },
];
```

#### Creating Slot Components

Components attached to slots receive props based on the slot type:

```typescript
// For message.actions slot
interface MessageActionsProps {
  message: ChatMessage;
  content: string;
  serverId?: string;
}

const FeedbackButton: FC<MessageActionsProps> = ({ message, content }) => {
  return <Button onClick={() => submitFeedback(message.id)}>Feedback</Button>;
};
```

#### Rendering Slots in Components

Use the `<Slot>` component to render plugin content:

```typescript
import { Slot } from "../core/components/Slot";

function MessageActions({ message, content }: Props) {
  return (
    <div className="flex gap-2">
      <Slot
        name="message.actions"
        props={{ message, content }}
        fallback={<span>No actions</span>}
        skeletonSize={{ width: "32px", height: "32px" }}
      />
    </div>
  );
}
```

#### Checking if Slot Has Content

```typescript
import { useSlotHasFillers } from "../core/utils/slots/useSlotHasFillers";

function Sidebar() {
  const hasSidebarContent = useSlotHasFillers("layout.sidebar");

  if (!hasSidebarContent) {
    return null;
  }

  return (
    <aside>
      <Slot name="layout.sidebar" />
    </aside>
  );
}
```

### Using PluginWrapper

`PluginWrapper` provides type-safe rendering of plugin components with automatic lazy loading and skeleton fallbacks:

```typescript
import { PluginWrapper } from "../core/utils/plugins/PluginWrapper";
import { MyPlugin } from "../plugins/MyPlugin";

function SomeComponent() {
  return (
    <PluginWrapper
      plugin={MyPlugin}
      component="MyButton"
      componentProps={{ onClick: handleClick }}
      skeletonSize={{ width: "100px", height: "40px" }}
    />
  );
}
```

#### PluginWrapper Props

| Prop              | Type                      | Description                    |
| ----------------- | ------------------------- | ------------------------------ |
| `plugin`          | `Plugin`                  | The plugin instance            |
| `component`       | `keyof plugin.components` | Component name to render       |
| `componentProps`  | `ComponentProps`          | Props to pass to the component |
| `skeletonSize`    | `{ width, height }`       | Skeleton size during loading   |
| `disableSkeleton` | `boolean`                 | Disable loading skeleton       |

### Route Definitions

Plugins can add new routes or inject routes into existing route trees.

#### Adding Top-Level Routes

```typescript
routes: [
  {
    path: "/login",
    element: <LoginPage />,
  },
]
```

#### Injecting Nested Routes

```typescript
routes: [
  {
    target: "/", // Parent route to inject into
    path: "conversation/:conversationId",
    element: <ConversationPage />,
  },
]
```

#### Route Wrappers

Wrap existing routes with HOCs for authentication, guards, etc:

```typescript
routeWrappers: [
  // Wrap a specific route
  {
    target: "/",
    wrapper: (children) => <AuthGuard>{children}</AuthGuard>,
  },
  // Wrap all routes globally
  {
    target: "global",
    wrapper: (children) => <ErrorBoundary>{children}</ErrorBoundary>,
  },
]
```

### Registering and Activating Plugins

#### Static Registration (in main.tsx)

```typescript
import { pluginManager } from "./core/utils/plugins/PluginManager";
import { MyPlugin } from "./plugins/MyPlugin";

// Register plugins before rendering
pluginManager.register(MyPlugin);

// Activate immediately or conditionally
pluginManager.activate(MyPlugin.name);
```

#### Dynamic Activation (based on config)

```typescript
// In a component or hook
import { pluginManager } from "./core/utils/plugins/PluginManager";

function usePluginActivation() {
  const { config } = useConfigContext();

  useEffect(() => {
    if (config.myFeatureEnabled) {
      pluginManager.activate(MyPluginName);
    }
  }, [config]);
}
```

#### Dynamic Plugin Creation

```typescript
// Factory function for dynamic plugins
export const createOAuth2LoginPlugin = (
  provider: string,
  displayName: string,
) => {
  return createPlugin({
    name: `OAuth2Login_${provider}`,
    components: {
      OAuth2Login: lazy(() => import("./components/OAuth2Login")),
    },
    metadata: { provider, displayName },
  });
};

// Usage
const googlePlugin = createOAuth2LoginPlugin("google", "Google");
pluginManager.register(googlePlugin);
pluginManager.activate(googlePlugin.name);
```

### React Hooks for Plugins

```typescript
// Get a specific plugin
import { usePlugin } from "./core/utils/plugins/usePlugin";
const myPlugin = usePlugin("MyPlugin");

// Get all active plugins
import { useActivePlugins } from "./core/utils/plugins/useActivePlugins";
const activePlugins = useActivePlugins();

// Check if slot has content
import { useSlotHasFillers } from "./core/utils/slots/useSlotHasFillers";
const hasHeaderActions = useSlotHasFillers("layout.headerActions");
```

### Example Plugin Structure

```
plugins/
└── MyPlugin/
    ├── index.tsx          # Plugin entry point with createPlugin
    ├── components/
    │   ├── MyButton.tsx   # Lazy-loaded component
    │   └── MyPanel.tsx    # Lazy-loaded component
    └── types.ts           # Plugin-specific types
```

## Styling

The UI uses HeroUI components along with TailwindCSS for styling with custom configuration.

## Build Output

The build process outputs to `../../packages/ragbits-chat/src/ragbits/chat/ui-build/` for integration with the main Ragbits package.

## Development Guidelines

### Code Style

- Use TypeScript for all code
- Follow ESLint configuration
- Format code with Prettier
- Use functional components with hooks
- Implement proper error boundaries

### Component Guidelines

- Keep components small and focused
- Use TypeScript interfaces for props
- Implement proper loading states
- Handle edge cases and errors gracefully

### Testing

- Write unit tests for utility functions
- Test component behavior with user interactions
- Ensure accessibility compliance
- Test responsive design across devices

## Contributing

1. Follow the existing code style and patterns
2. Add TypeScript types for new features
3. Update documentation for API changes
4. Test changes across different screen sizes
5. Ensure proper error handling

## License

This project is part of the Ragbits ecosystem. See the main project license for details.
