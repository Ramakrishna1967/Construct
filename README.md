
🤖 Construct – Autonomous AI Software Engineer
Construct Version Python Live

An Autonomous AI that doesn't just answer questions — it builds software.

Construct maps your repository, plans architectural changes, and writes verified code inside a secure sandbox using a coordinated team of 5 specialized AI agents.

Live Backend • Frontend IDE • Landing Page

🎯 What is Construct?
Construct is a production-grade autonomous coding agent built on LangGraph. Unlike simple chatbots, Construct employs a multi-agent architecture where specialized AI agents collaborate to understand, plan, write, and review code autonomously.

The 5 AI Agents
Agent	Role	Technology
🧠 Supervisor	Orchestrates the workflow, delegates tasks	LangGraph StateGraph
🧭 Planner	Designs implementation strategy	Gemini 2.0 Flash
🔍 Researcher	Searches codebase context & best practices	ChromaDB Vector Search
💻 Coder	Writes production-quality code	Gemini 2.0 Flash + Tree-Sitter
🛡️ Reviewer	Finds bugs, suggests improvements	Static Analysis + LLM
🏗️ Architecture
┌─────────────────────────────────────────────────────────────┐
│                      FRONTEND (React)                       │
│                   construct-ide.vercel.app                   │
└────────────────────────────┬────────────────────────────────┘
                             │ WebSocket
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                    BACKEND (FastAPI)                        │
│                construct-eb7w.onrender.com                   │
│  ┌─────────────────────────────────────────────────────────┐│
│  │                   LangGraph Engine                      ││
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─────────┐ ││
│  │  │Supervisor│─▶│ Planner  │─▶│Researcher│─▶│  Coder  │ ││
│  │  └──────────┘  └──────────┘  └──────────┘  └────┬────┘ ││
│  │                                                  │      ││
│  │                              ┌──────────┐        │      ││
│  │                              │ Reviewer │◀───────┘      ││
│  │                              └──────────┘               ││
│  └─────────────────────────────────────────────────────────┘│
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │    Redis    │  │  ChromaDB   │  │   Docker Sandbox    │ │
│  │  Sessions   │  │  Vectors    │  │   Code Execution    │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
🛠️ Tech Stack
Core
Technology	Purpose
Python 3.11+	Runtime
FastAPI	Async Web Framework
LangGraph	Multi-Agent Orchestration
Gemini 2.0 Flash	LLM (Google AI)
Infrastructure
Technology	Purpose
Redis	Session Storage & Rate Limiting
ChromaDB	Vector Database for Code Context
Docker	Secure Code Execution Sandbox
Tree-Sitter	Code Parsing & Indexing
Resilience
Technology	Purpose
Circuit Breakers	Fault Tolerance
WebSocket Streaming	Real-Time Token Streaming
Health Checks	Component Monitoring
📁 Project Structure
construct-backend/
├── app/
│   ├── main.py                 # FastAPI application entry
│   ├── api/
│   │   ├── routes/
│   │   │   ├── websocket.py    # WebSocket endpoint (/api/v1/ws)
│   │   │   ├── health.py       # Health check endpoint
│   │   │   └── auth.py         # Authentication routes
│   │   └── middleware/
│   │       ├── rate_limit.py   # Rate limiting
│   │       └── cors.py         # CORS configuration
│   │
│   ├── agents/
│   │   ├── supervisor.py       # Orchestrator agent
│   │   ├── planner.py          # Strategy planning agent
│   │   ├── researcher.py       # Context gathering agent
│   │   ├── coder.py            # Code generation agent
│   │   └── reviewer.py         # Code review agent
│   │
│   ├── graph/
│   │   ├── state.py            # LangGraph state definition
│   │   └── workflow.py         # Agent workflow graph
│   │
│   ├── services/
│   │   ├── redis_service.py    # Redis connection pool
│   │   ├── chromadb_service.py # Vector store operations
│   │   ├── docker_service.py   # Sandbox execution
│   │   └── llm_service.py      # Gemini API wrapper
│   │
│   └── utils/
│       ├── tree_sitter.py      # Code parsing utilities
│       └── circuit_breaker.py  # Fault tolerance
│
├── Dockerfile                  # Container configuration
├── docker-compose.yml          # Local development setup
├── requirements.txt            # Python dependencies
├── .env.example                # Environment variables template
└── README.md
🚀 Quick Start
Prerequisites
Python 3.11+
Docker (for code execution sandbox)
Redis (for sessions)
Environment Variables
# Required
GOOGLE_API_KEY=your_gemini_api_key
REDIS_URL=redis://localhost:6379
# Optional
ENVIRONMENT=development
API_KEYS=key1,key2,key3
Installation
# Clone the repository
git clone https://github.com/Ramakrishna1967/Construct-Backend.git
cd Construct-Backend
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
# Install dependencies
pip install -r requirements.txt
# Run the server
uvicorn app.main:app --reload --port 8000
Docker Deployment
docker-compose up -d
🔌 API Endpoints
Health Check
GET /health
Returns component status for Redis, ChromaDB, LLM, Docker, and Circuit Breakers.

WebSocket (Code Review)
WS /api/v1/ws
Real-time bidirectional communication for code review sessions.

Message Format:

{
  "type": "review",
  "code": "def hello(): print('world')",
  "language": "python"
}
📊 System Components
Component	Status Indicator	Description
Redis	✅ Healthy	Session persistence, rate limiting
ChromaDB	✅ Healthy	Vector embeddings for code context
LLM	✅ Healthy	Gemini 2.0 Flash for reasoning
Docker	⚠️ Degraded*	Sandboxed code execution
Circuit Breakers	✅ Healthy	Fault tolerance mechanisms
*Docker is unavailable on Render.com free tier. Code execution works locally.

🌐 Deployment
Render.com (Current)
URL: https://construct-eb7w.onrender.com
Free Tier: Sleeps after 15 min inactivity
Wake Time: ~30-60 seconds on first request
Production Recommendations
Use Render Starter ($7/mo) or Railway for always-on
Configure Redis via Upstash for persistence
Set ENVIRONMENT=production
🔗 Related Projects
Project	Description
Construct IDE	React frontend with Monaco Editor
Construct Landing	Marketing landing page
👨‍💻 Author
Ramakrishna
Building autonomous AI systems.

📄 License
MIT License
