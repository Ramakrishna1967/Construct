# Construct AI Code Reviewer - Frontend

The modern, React-based IDE interface for the Construct AI Code Reviewer system. This frontend connects to the robust Python backend to provide real-time, multi-agent code analysis.

## Features

- 🖥️ **IDE-like Interface**: Monaco Editor integration with file tree and tab management.
- 💬 **AI Chat Terminal**: Real-time streaming chat with the 5-agent system.
- ⚡ **Real-time Updates**: WebSocket connection for instant feedback.
- 🎨 **Modern UI**: Clean, responsive design built with React and Vite.

## Architecture

This frontend communicates with the Backend API deployed on Render.

For detailed system architecture diagrams (including Agent Workflows, Request Flow, and Sandbox design), please see the **[Backend Repository Documentation](https://github.com/Ramakrishna1967/Construct/blob/main/ARCHITECTURE.md)**.

## Getting Started

1.  **Install dependencies:**
    ```bash
    npm install
    ```

2.  **Run locally:**
    ```bash
    npm run dev
    ```

3.  **Build for production:**
    ```bash
    npm run build
    ```

## Deployment

This project is optimized for deployment on **Vercel**.
Ensure you set the Production Branch to `master` in your Vercel Git Settings.
