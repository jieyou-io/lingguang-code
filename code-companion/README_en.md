<div align="center">
  <img src="public/logo.svg" alt="Ling Guang Logo" width="128" height="128">
  <h1>Ling Guang (灵光)</h1>
</div>

<div align="center">
  <p>
    <b>English</b> | <a href="README.md">中文</a>
  </p>
</div>

A mobile-friendly web client for interacting with multiple AI models, including Claude, Codex, and Gemini. It provides a chat interface to manage different chat sessions, projects, and view usage statistics.

## Features

- **Multi-Model Support**: Seamlessly switch between AI models like Claude, Codex, and Gemini.
- **Mobile-First Design**: Fully responsive interface for a great experience on both desktop and mobile devices.
- **Real-time Chat**: Interactive chat interface with markdown rendering and code syntax highlighting.
- **Session & Project Management**: Organize your chats by sessions and link them to different projects.
- **Usage Statistics**: Monitor token usage and check the real-time status of AI engines.
- **Plugin System**: Extend core functionality with custom plugins.
- **Prompt Management**: Create, edit, and manage system prompts to customize the AI's behavior.

## Tech Stack

- [Vue.js](https://vuejs.org/)
- [Vite](https://vitejs.dev/)
- [TypeScript](https://www.typescriptlang.org/)
- [Vue Router](https://router.vuejs.org/)
- [Tailwind CSS](https://tailwindcss.com/)
- [shadcn/ui](https://ui.shadcn.com/)

## Getting Started

### Prerequisites

- [Node.js](https://nodejs.org/) (version 18 or higher recommended)
- [npm](https://www.npmjs.com/)

### Installation

1.  **Clone the repository:**
    ```sh
    git clone <your-repository-url>
    cd lingguang
    ```

2.  **Install dependencies:**
    ```sh
    npm install
    ```

3.  **Set up environment variables:**

    Create a `.env` file in the root of the project and add the necessary environment variables for your backend API.

    ```env
    # Example for your backend API endpoint
    VITE_API_BASE_URL=http://localhost:8000
    ```

4.  **Run the development server:**
    ```sh
    npm run dev
    ```

    The application will be available at `http://localhost:5173` (or another port if 5173 is in use).

## Available Scripts

- `npm run dev`: Starts the development server with hot-reloading.
- `npm run build`: Compiles and minifies the application for production.
- `npm run lint`: Lints the codebase using ESLint to find and fix problems.
- `npm run preview`: Starts a local server to preview the production build.
