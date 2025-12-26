# Construct IDE - AI Code Review Frontend

A premium, Cursor-style AI Code Review IDE built with React, Vite, and Monaco Editor.

![Construct IDE](https://img.shields.io/badge/Construct-IDE-7c3aed?style=for-the-badge)
![React](https://img.shields.io/badge/React-18-61dafb?style=flat-square)
![TypeScript](https://img.shields.io/badge/TypeScript-5-3178c6?style=flat-square)
![Vite](https://img.shields.io/badge/Vite-6-646cff?style=flat-square)

## ✨ Features

- 🤖 **5 AI Agents**: Supervisor, Planner, Researcher, Coder, Reviewer
- ⚡ **Real-time Code Review**: WebSocket streaming with your backend
- 🖥️ **Monaco Editor**: VS Code's editor with syntax highlighting
- 🔧 **Code Compiler**: Execute Python, JavaScript, Java, C++, Go, Rust, and more
- 📁 **File Management**: Create, edit, delete files
- 🌙 **Dark Theme**: Cursor-inspired premium design

## 🚀 Quick Start

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build
```

## 🔗 Backend Integration

This frontend connects to the AI Code Reviewer backend:

| Component | URL |
|-----------|-----|
| **Backend API** | https://construct-eb7w.onrender.com |
| **WebSocket** | wss://construct-eb7w.onrender.com/api/v1/ws |
| **Health Check** | https://construct-eb7w.onrender.com/health |

## 📦 Deployment

### Deploy to Netlify (Recommended)

1. **Option A: Drag & Drop**
   - Run `npm run build`
   - Drag the `dist` folder to [Netlify Drop](https://app.netlify.com/drop)

2. **Option B: GitHub Integration**
   - Push code to GitHub
   - Connect repo to Netlify
   - Auto-deploys on every push

### Deploy to Vercel

```bash
npm i -g vercel
vercel --prod
```

## 🏗️ Architecture

```
Frontend (React + Vite)
        │
        ├── Monaco Editor (Code editing)
        ├── WebSocket (Real-time AI chat)
        ├── Piston API (Code execution)
        │
        ▼
Backend (FastAPI + LangGraph)
        │
        ├── 5 AI Agents (Multi-agent review)
        ├── Redis (Session/memory)
        ├── ChromaDB (Vector store)
        └── Gemini 2.0 (LLM)
```

## 📄 License

MIT License
