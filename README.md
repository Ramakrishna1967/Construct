# AI Code Reviewer Backend

Production-ready backend for an AI code review system using LangGraph, Tree-Sitter, Docker sandbox, and Redis.

## Features

- **🤖 LangGraph Agent System**: Supervisor pattern with specialized worker nodes
- **🔍 Code Indexing**: Tree-Sitter based Python code parsing and analysis
- **🐳 Docker Sandbox**: Safe, isolated code execution with resource limits
- **💾 Redis State Management**: Persistent state storage with connection pooling
- **🔒 Security**: Path validation, file size limits, command timeouts
- **📊 Logging**: Structured JSON logging with multiple log levels
- **⚙️ Configuration**: Type-safe settings with environment variable validation
- **🔄 Retry Logic**: Automatic retries for LLM calls and Redis connections
- **🌐 WebSocket API**: Real-time code review interactions

## Architecture

### 1. High-Level Architecture Overview

This diagram shows how the User interacts with the Frontend (deployed on Vercel) and how requests flow to the Backend (deployed on Render), which orchestrates the AI Agents and services.

```mermaid
graph TD
    User["User / Developer"] -->|HTTPS / WSS| Frontend["Frontend (Vercel)"]
    Frontend -->|REST API| LoadBalancer["Render Load Balancer"]
    LoadBalancer -->|Traffic| Backend["Backend API (FastAPI)"]
    
    subgraph "Backend Services (Render)"
        Backend -->|Orchestrates| Supervisor["Supervisor Agent"]
        Supervisor -->|Delegates| Planner["Planner Agent"]
        Supervisor -->|Delegates| Researcher["Researcher Agent"]
        Supervisor -->|Delegates| Coder["Coder Agent"]
        Supervisor -->|Delegates| Reviewer["Reviewer Agent"]
        
        Backend -->|Stores/Retrieves| Redis[("Redis Cache & Session Store")]
        Backend -->|Embeddings| VectorStore["ChromaDB / Vector Store"]
        Backend -->|LLM Calls| Gemini["Google Gemini 1.5 Pro"]
        Backend -->|Sandboxed Exec| Docker["Docker Sandbox"]
    end
```

### 2. Multi-Agent Workflow (LangGraph)

The core intelligent engine of Construct is built on **LangGraph**. A **Supervisor Node** acts as the router, deciding which specialist agent should handle the next step based on the conversation state.

```mermaid
stateDiagram-v2
    [*] --> Supervisor
    
    state Supervisor {
        [*] --> AnalyzeState
        AnalyzeState --> Route: Decision
    }
    
    Route --> Planner: Needs Plan
    Route --> Researcher: Needs Context
    Route --> Coder: Needs Code
    Route --> Reviewer: Needs Review
    Route --> FINISH: Task Complete
    
    state Planner {
        GeneratePlan --> UpdateState
    }
    
    state Researcher {
        SearchCode --> AnalyzeFile
        AnalyzeFile --> UpdateState
    }
    
    state Coder {
        WriteCode --> ExecuteTool
        ExecuteTool --> UpdateState
    }
    
    state Reviewer {
        SecurityScan --> CodeCritique
        CodeCritique --> UpdateState
    }
    
    Planner --> Supervisor: Return Plan
    Researcher --> Supervisor: Return Findings
    Coder --> Supervisor: Return Code/Result
    Reviewer --> Supervisor: Return Critique
    
    FINISH --> [*]
```

### 3. Request Processing Flow (WebSocket)

This sequence diagram illustrates the real-time communication flow when a user sends a message (e.g., "Fix this bug") via the WebSocket connection.

```mermaid
sequenceDiagram
    participant U as User
    participant FE as Frontend
    participant WS as WebSocket Endpoint
    participant G as Graph Orchestrator
    participant A as Agents
    participant LLM as Gemini API
    participant R as Redis

    U->>FE: Sends "Fix bug in main.py"
    FE->>WS: Send JSON Message
    WS->>R: Save User Message
    WS->>G: Invoke Graph(state)
    
    loop Agent Loop
        G->>A: Evaluate Current Node
        A->>LLM: Generate Response/Action
        LLM-->>A: Tool Call / Text
        
        alt Tool Execution
            A->>A: Execute Tool (e.g. read_file)
            A-->>G: Update State with Result
        else Final Answer
            A-->>G: Return Answer
        end
        
        G-->>WS: Stream Partial Token / Update
        WS-->>FE: Stream to UI
    end
    
    G->>R: Save Conversation State
    WS-->>FE: "Complete" Signal
    FE-->>U: Display Final Response
```

### 4. Frontend Component Structure

The React frontend handles the IDE-like interface, managing editor state, file trees, and the chat terminal.

```mermaid
classDiagram
    class App {
        +AppContextProvider
        +Layout
    }
    
    class AppContext {
        +activeFile
        +openFiles
        +messages[]
        +sendMessage()
        +connectWebSocket()
    }
    
    class Sidebar {
        +FileExplorer
        +ChatHistory
    }
    
    class EditorArea {
        +MonacoEditor
        +Tabs
    }
    
    class ChatPanel {
        +MessageList
        +InputArea
        +StreamingRenderer
    }
    
    class TerminalPanel {
        +OutputLogs
        +SystemStatus
    }

    App --> AppContext : Provides State
    App --> Sidebar
    App --> EditorArea
    App --> ChatPanel
    EditorArea --> MonacoEditor : Wraps
    ChatPanel ..> AppContext : Consumes
    Sidebar ..> AppContext : Consumes
```

### 5. Security & Sandbox Architecture

Code execution is isolated to prevent malicious or accidental damage to the backend server.

```mermaid
flowchart LR
    subgraph "Host (Render)"
        API["FastAPI Server"]
        Request["User Request"]
    end
    
    subgraph "Docker Container (Sandbox)"
        Exec["Python Agent Executor"]
        FS["Isolated File System"]
        Network["Restricted Network"]
    end
    
    Request --> API
    API -->|1. Spin up| Docker
    Docker -->|2. Mount Code| FS
    API -->|3. Send Command| Exec
    Exec -->|4. Run Code| FS
    FS -->|5. Output/Error| Exec
    Exec -->|6. Return Result| API
    
    style Docker fill:#f9f,stroke:#333,stroke-width:2px
```

### Project Structure

```
backend/
├── main.py                 # FastAPI application with WebSocket
├── src/
│   ├── config.py          # Centralized configuration management
│   ├── logging_config.py  # Logging setup
│   ├── agent/             # LangGraph agent system
│   │   ├── graph.py       # Graph definition with state initialization
│   │   ├── nodes.py       # Supervisor, coder, and planner nodes
│   │   ├── prompts.py     # System prompts
│   │   └── state.py       # Agent state definition
│   ├── services/          # Infrastructure services
│   │   ├── indexer.py     # Tree-Sitter code indexing
│   │   ├── redis_store.py # Redis operations
│   │   └── sandbox.py     # Docker container execution
│   └── tools/             # Agent tools
│       ├── file_ops.py    # File read/write/list with validation
│       └── terminal.py    # Command execution with timeout
├── requirements.txt       # Python dependencies
├── Dockerfile            # Container configuration
└── .env.example          # Environment variables template
