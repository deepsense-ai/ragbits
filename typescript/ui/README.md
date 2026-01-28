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

## Standalone Usage (Without Full Backend)

You can use the chat UI components without setting up the full Ragbits backend.

### Basic Setup

```tsx
import { RagbitsContextProvider } from "@ragbits/api-client-react";
import { ThemeContextProvider } from "./core/contexts/ThemeContext";
import { MinimalHistoryStoreProvider } from "./core/stores/HistoryStore";
import Chat from "./core/components/Chat";

function App() {
  return (
    <RagbitsContextProvider baseUrl="https://your-api.com">
      <ThemeContextProvider>
        <MinimalHistoryStoreProvider>
          {/* No ConfigContextProvider needed! */}
          <Chat />
        </MinimalHistoryStoreProvider>
      </ThemeContextProvider>
    </RagbitsContextProvider>
  );
}
```

### With Custom Message Handling

```tsx
<MinimalHistoryStoreProvider
  onSendMessage={async (text, client) => {
    // Call your API
    const response = await fetch("/api/chat", {
      method: "POST",
      body: JSON.stringify({ message: text }),
    });
    // Handle response...
  }}
>
  <Chat />
</MinimalHistoryStoreProvider>
```

### What Works in Standalone Mode

- Chat input and message display
- Theme switching
- Basic conversation flow

### What's Disabled in Standalone Mode

- Plugins (feedback, share, chat history sidebar, auth)
- Conversation persistence (IndexedDB)
- Config-based customization

## Plugin System

The UI supports a plugin architecture for extending functionality. Plugins are located in the `src/plugins/` directory.

### Creating a Plugin

1. Create a new directory in `src/plugins/`
2. Implement the plugin interface
3. Register the plugin in the main application

### Example Plugin Structure

```
plugins/
└── MyPlugin/
    ├── index.ts       # Plugin entry point
    ├── components/    # Plugin-specific components
    └── types.ts       # Plugin type definitions
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
