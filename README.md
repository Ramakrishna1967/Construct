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

```

## Prerequisites

- Python 3.11+
- Docker Desktop (for sandbox execution)
- Redis server
- Google Gemini API key

## Installation

### 1. Clone the Repository

```bash
cd backend
```

### 2. Create Virtual Environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Set Up Environment

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

Edit `.env` and set your Google API key:

```env
GOOGLE_API_KEY=your_api_key_here
```

### 5. Start Redis

```bash
# Using Docker
docker run -d -p 6379:6379 --name redis redis:latest

# Or install Redis locally and start it
redis-server
```

### 6. Verify Docker

Ensure Docker Desktop is running:

```bash
docker ps
```

## Running the Application

### Development Mode

```bash
# Using uvicorn directly
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Or using Python
python main.py
```

### Production Mode

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Using Docker

```bash
# Build image
docker build -t ai-code-reviewer .

# Run container
docker run -d \
  -p 8000:8000 \
  --env-file .env \
  --name ai-code-reviewer \
  ai-code-reviewer
```

## API Endpoints

### Health Check

```bash
GET /health
```

Response:
```json
{
  "status": "healthy",
  "service": "ai-code-reviewer",
  "version": "1.0.0",
  "model": "gemini-1.5-flash"
}
```

### WebSocket

```
WS /ws
```

Connect and send text messages for code review:

```javascript
const ws = new WebSocket('ws://localhost:8000/ws');

ws.onopen = () => {
  ws.send('Create a Python hello world script');
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(`[${data.sender}]: ${data.content}`);
};
```

## Testing

### Test Client

Run the included test client:

```bash
python test_client.py
```

### Manual Testing

```bash
# Check health
curl http://localhost:8000/health

# WebSocket test (using websocat)
echo "Write a Python function to calculate fibonacci" | websocat ws://localhost:8000/ws
```

## Configuration

All settings can be configured via environment variables. See `.env.example` for full list.

### Key Settings

| Variable | Description | Default |
|----------|-------------|---------|
| `GOOGLE_API_KEY` | Google Gemini API key | **Required** |
| `GEMINI_MODEL` | Model to use | `gemini-1.5-flash` |
| `REDIS_URL` | Redis connection URL | `redis://localhost:6379` |
| `DOCKER_IMAGE` | Docker image for sandbox | `python:3.11-slim` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `APP_PORT` | Application port | `8000` |

## Security Features

- **Path Validation**: Prevents directory traversal attacks
- **File Extension Filtering**: Only allowed extensions can be read/written
- **File Size Limits**: Prevents memory exhaustion
- **Command Timeouts**: Prevents hanging processes
- **Docker Resource Limits**: CPU and memory constraints
- **Error Sanitization**: Safe error messages to clients

## Logging

Logs are output to stdout in JSON format (production) or human-readable format (development).

### Log Levels

```bash
# Development - detailed logs
LOG_LEVEL=DEBUG

# Production - essential logs
LOG_LEVEL=INFO
```

### Viewing Logs

```bash
# Follow logs
python main.py 2>&1 | jq

# Filter by level
python main.py 2>&1 | jq 'select(.levelname == "ERROR")'
```

## Troubleshooting

### Google API Key Errors

```
google.auth.exceptions.DefaultCredentialsError
```

**Solution**: Ensure `GOOGLE_API_KEY` is set in `.env`

### Redis Connection Failed

```
Failed to connect to Redis
```

**Solution**: Start Redis server:
```bash
docker run -d -p 6379:6379 redis
```

### Docker Not Available

```
Failed to initialize Docker client
```

**Solution**: Start Docker Desktop and verify:
```bash
docker ps
```

### Module Import Errors

```
ModuleNotFoundError: No module named 'X'
```

**Solution**: Install dependencies:
```bash
pip install -r requirements.txt
```

## Development

### Code Style

Follow PEP 8. Use type hints and docstrings.

### Adding New Tools

1. Create tool function in `src/tools/`
2. Add to `src/tools/__init__.py`
3. Import in `src/agent/nodes.py`
4. Update prompts to include tool usage

### Extending the Agent

1. Add new node function in `src/agent/nodes.py`
2. Register node in `src/agent/graph.py`
3. Update supervisor logic
4. Add to workflow edges

## Production Deployment

### Environment Variables

- Set all required variables
- Use strong Redis passwords
- Configure CORS origins appropriately
- Enable HTTPS/WSS

### Scaling

- Use multiple uvicorn workers
- Deploy behind load balancer
- Use managed Redis service
- Monitor resource usage

### Monitoring

- Check `/health` endpoint regularly
- Monitor logs for errors
- Track Redis connection pool
- Monitor Docker container metrics

## License

[Your License Here]

## Support

For issues and questions, please open an issue on GitHub.
