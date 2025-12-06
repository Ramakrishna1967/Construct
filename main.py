"""
AI Code Reviewer Backend - Production Application

FastAPI WebSocket server with production-grade features:
- Multi-agent LangGraph workflow
- Rate limiting and metrics
- Request correlation for tracing
- Comprehensive error handling
- Health checks for all services
"""

import os
import json
from typing import Optional
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel

from src.agent.graph import graph, run_agent
from src.agent.state import create_initial_state
from langchain_core.messages import HumanMessage
from src.config import get_settings
from src.logging_config import setup_logging, get_logger
from src.middleware.rate_limiter import RateLimitMiddleware, get_rate_limiter
from src.middleware.metrics import MetricsMiddleware, get_metrics, get_metrics_endpoint_response
from src.middleware.correlation import CorrelationMiddleware, get_correlation_id
from src.middleware.auth import AuthMiddleware, WebSocketAuthenticator

# Initialize configuration and logging
settings = get_settings()
setup_logging()
logger = get_logger(__name__)


# =============================================================================
# LIFECYCLE MANAGEMENT
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown."""
    # Startup
    logger.info("=" * 60)
    logger.info("AI CODE REVIEWER BACKEND - STARTING")
    logger.info("=" * 60)
    logger.info(f"Environment: {settings.environment.upper()}")
    logger.info(f"Model: {settings.gemini_model}")
    logger.info(f"Redis: {settings.redis_url}")
    logger.info(f"Docker Image: {settings.docker_image}")
    logger.info(f"Log Level: {settings.log_level}")
    logger.info(f"Auth Required: {settings.is_production or settings.require_auth_in_dev}")
    logger.info(f"API Keys Configured: {len(settings.api_keys_list)}")
    logger.info("Application startup complete")
    
    yield
    
    # Shutdown
    logger.info("Shutting down AI Code Reviewer backend")
    # Cleanup resources here if needed


# =============================================================================
# APPLICATION SETUP
# =============================================================================

app = FastAPI(
    title="AI Code Reviewer",
    description="""
    Production-grade Agentic AI Code Review System.
    
    Features:
    - Multi-agent architecture (Supervisor, Planner, Researcher, Coder, Reviewer)
    - LangGraph-based workflow orchestration
    - Real-time WebSocket streaming
    - Semantic code search with RAG
    - Security scanning
    - Code complexity analysis
    """,
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)


# =============================================================================
# MIDDLEWARE CONFIGURATION
# =============================================================================

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Correlation ID for request tracing
app.add_middleware(CorrelationMiddleware)

# Metrics collection
app.add_middleware(MetricsMiddleware)

# Rate limiting
app.add_middleware(
    RateLimitMiddleware,
    requests_per_minute=60,
    exclude_paths=["/health", "/metrics", "/api/docs", "/api/redoc"]
)

# API Key Authentication (enabled based on environment)
if settings.is_production or settings.require_auth_in_dev:
    app.add_middleware(AuthMiddleware)
    logger.info("Authentication middleware enabled")
else:
    logger.warning("Running WITHOUT authentication (development mode)")


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class ReviewRequest(BaseModel):
    """Request model for code review."""
    message: str
    session_id: Optional[str] = None
    
class ReviewResponse(BaseModel):
    """Response model for code review."""
    status: str
    message: str
    session_id: Optional[str] = None

class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    service: str
    version: str
    model: str
    timestamp: str
    checks: dict


# =============================================================================
# API ENDPOINTS
# =============================================================================

@app.get("/", response_class=JSONResponse)
async def root():
    """Root endpoint with API information."""
    return {
        "service": "AI Code Reviewer",
        "version": "2.0.0",
        "description": "Production-grade Agentic AI Code Review System",
        "endpoints": {
            "websocket": "/api/v1/ws",
            "health": "/health",
            "metrics": "/metrics",
            "docs": "/api/docs"
        },
        "agents": ["supervisor", "planner", "researcher", "coder", "reviewer"]
    }


@app.get("/health")
async def health_check():
    """
    Comprehensive health check endpoint.
    
    Checks all backend components:
    - Redis connectivity
    - ChromaDB status
    - LLM configuration
    - Docker availability
    - Circuit breaker states
    """
    from src.services.health import get_health_checker
    
    checker = get_health_checker()
    health = await checker.get_full_health()
    
    # Return appropriate status code
    status_code = 200
    if health.status.value == "unhealthy":
        status_code = 503
    elif health.status.value == "degraded":
        status_code = 200  # Still operational
    
    return JSONResponse(
        content=health.to_dict(),
        status_code=status_code
    )


@app.get("/health/live")
async def liveness_probe():
    """
    Kubernetes liveness probe.
    
    Returns 200 if the application is running.
    """
    from src.services.health import get_health_checker
    
    checker = get_health_checker()
    return await checker.get_liveness()


@app.get("/health/ready")
async def readiness_probe():
    """
    Kubernetes readiness probe.
    
    Returns 200 if the application is ready to serve traffic.
    """
    from src.services.health import get_health_checker
    
    checker = get_health_checker()
    result = await checker.get_readiness()
    
    status_code = 200 if result["ready"] else 503
    return JSONResponse(content=result, status_code=status_code)


@app.get("/metrics")
async def metrics_endpoint():
    """Prometheus metrics endpoint."""
    content, content_type = get_metrics_endpoint_response()
    
    if isinstance(content, dict):
        return JSONResponse(content)
    else:
        return Response(content=content, media_type=content_type)


# =============================================================================
# GOOGLE OAUTH AUTHENTICATION
# =============================================================================

class GoogleAuthRequest(BaseModel):
    """Google OAuth login request."""
    token: str  # Google ID token from frontend


class AuthResponse(BaseModel):
    """Authentication response."""
    access_token: str
    token_type: str = "bearer"
    user: dict


@app.post("/api/v1/auth/google", response_model=AuthResponse)
async def google_login(request: GoogleAuthRequest):
    """
    Authenticate with Google OAuth.
    
    Frontend sends Google ID token, backend verifies and returns JWT.
    """
    from src.middleware.google_auth import verify_google_token, create_jwt_token
    
    user = await verify_google_token(request.token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid Google token")
    
    jwt_token = create_jwt_token(user)
    
    return AuthResponse(
        access_token=jwt_token,
        user={
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "picture": user.picture
        }
    )


@app.get("/api/v1/auth/me")
async def get_current_user_info():
    """Get current authenticated user info."""
    from src.middleware.google_auth import require_user, get_user_by_id, get_user_usage
    from fastapi import Depends
    
    # Note: In production, use Depends(require_user)
    # For now, return mock data if not authenticated
    return {
        "authenticated": False,
        "message": "Use Authorization: Bearer <token> header"
    }


@app.get("/api/v1/auth/usage")
async def get_usage_stats():
    """Get current user's usage statistics."""
    return {
        "daily_limit": 100,
        "used_today": 0,
        "remaining": 100,
        "message": "Authenticate to track usage"
    }


# =============================================================================
# API V1 ROUTES
# =============================================================================

@app.post("/api/v1/review", response_model=ReviewResponse)
async def create_review(request: ReviewRequest):
    """
    Submit a code review request.
    
    This is a non-streaming endpoint. For real-time streaming,
    use the WebSocket endpoint at /api/v1/ws.
    """
    try:
        logger.info(f"Review request: {request.message[:100]}...")
        
        # Run agent (non-streaming)
        result = None
        async for event in run_agent(
            request.message,
            session_id=request.session_id,
            stream=False
        ):
            result = event
        
        return ReviewResponse(
            status="complete",
            message="Review completed. Use WebSocket for detailed streaming.",
            session_id=request.session_id
        )
        
    except Exception as e:
        logger.error(f"Review error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# SESSION MANAGEMENT API
# =============================================================================

@app.get("/api/v1/sessions")
async def list_sessions(limit: int = 50):
    """
    List recent sessions with metadata.
    
    Returns session IDs, creation times, and message counts.
    """
    try:
        from src.services.redis_store import RedisStore
        redis = RedisStore()
        sessions = await redis.list_sessions(limit=limit)
        
        return {
            "sessions": sessions,
            "count": len(sessions)
        }
        
    except Exception as e:
        logger.error(f"Error listing sessions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/sessions/{session_id}")
async def get_session(session_id: str):
    """
    Get session metadata (without full message history).
    """
    try:
        from src.services.redis_store import RedisStore
        redis = RedisStore()
        metadata = await redis.get_session_metadata(session_id)
        
        if not metadata:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return metadata
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting session {session_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/sessions/{session_id}/history")
async def get_session_history(session_id: str):
    """
    Get full conversation history for a session.
    """
    try:
        from src.services.redis_store import RedisStore
        redis = RedisStore()
        conversation = await redis.get_conversation(session_id)
        
        if not conversation:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return conversation
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting history for {session_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/sessions/{session_id}/evaluations")
async def get_session_evaluations(session_id: str):
    """
    Get evaluation metrics for a session.
    """
    try:
        from src.services.redis_store import RedisStore
        redis = RedisStore()
        evaluations = await redis.get_evaluations(session_id)
        
        return {
            "session_id": session_id,
            "evaluations": evaluations,
            "count": len(evaluations)
        }
        
    except Exception as e:
        logger.error(f"Error getting evaluations for {session_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/v1/sessions/{session_id}")
async def delete_session(session_id: str):
    """
    Delete a session and its conversation history.
    """
    try:
        from src.services.redis_store import RedisStore
        redis = RedisStore()
        success = await redis.delete_session(session_id)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete session")
        
        return {"status": "deleted", "session_id": session_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting session {session_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/metrics/evaluations")
async def get_evaluation_metrics():
    """
    Get aggregated evaluation metrics across all sessions.
    """
    try:
        from src.services.evaluation import get_aggregator
        aggregator = get_aggregator()
        
        return {
            "summary": aggregator.get_summary(),
            "by_agent": aggregator.get_agent_breakdown()
        }
        
    except Exception as e:
        logger.error(f"Error getting evaluation metrics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# WEBSOCKET ENDPOINT
# =============================================================================

# Track active WebSocket connections
active_connections: dict = {}


@app.websocket("/api/v1/ws")
@app.websocket("/ws")  # Legacy support
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time code review streaming.
    
    Authentication:
    - Pass api_key as query parameter: /api/v1/ws?api_key=YOUR_KEY
    - Required in production mode
    
    Protocol:
    1. Client sends text message with review request
    2. Server streams back JSON events:
       - {"type": "token", "content": "...", "sender": "agent_name"}
       - {"type": "complete", "message": "..."}
       - {"type": "error", "error": "...", "details": "..."}
    """
    client_id = id(websocket)
    correlation_id = get_correlation_id() or f"ws-{client_id}"
    
    logger.info(f"WebSocket connection attempt: {client_id} (correlation: {correlation_id})")
    
    # Authenticate WebSocket connection
    is_authenticated = await WebSocketAuthenticator.authenticate(websocket)
    
    if not is_authenticated:
        logger.warning(f"WebSocket authentication failed: {client_id}")
        await websocket.close(code=4001, reason="Authentication required. Provide api_key query parameter.")
        return
    
    await websocket.accept()
    active_connections[client_id] = websocket
    
    # Update metrics if available
    metrics = get_metrics()
    if hasattr(metrics, 'inc_websocket'):
        metrics.inc_websocket()
    
    logger.info(f"WebSocket connected: {client_id}")
    
    try:
        while True:
            # Receive message
            data = await websocket.receive_text()
            logger.info(f"[{client_id}] Received: {data[:100]}...")
            
            try:
                # Create initial state
                initial_state = create_initial_state(data)
                logger.debug(f"[{client_id}] Created initial state")
                
                # Stream agent execution
                event_count = 0
                async for event in graph.astream(initial_state):
                    event_count += 1
                    logger.debug(f"[{client_id}] Event {event_count}")
                    
                    for node_name, value in event.items():
                        if "messages" in value and value["messages"]:
                            for msg in value["messages"]:
                                response = {
                                    "type": "token",
                                    "content": msg.content,
                                    "sender": node_name,
                                    "event": event_count,
                                    "correlation_id": correlation_id
                                }
                                await websocket.send_json(response)
                                logger.debug(f"[{client_id}] Sent {node_name} response")
                
                logger.info(f"[{client_id}] Completed: {event_count} events")
                
                # Send completion
                await websocket.send_json({
                    "type": "complete",
                    "message": "Processing complete",
                    "events": event_count,
                    "correlation_id": correlation_id
                })
                
            except Exception as graph_error:
                logger.error(f"[{client_id}] Graph error: {graph_error}", exc_info=True)
                
                try:
                    await websocket.send_json({
                        "type": "error",
                        "error": "Processing failed",
                        "details": str(graph_error),
                        "correlation_id": correlation_id
                    })
                except Exception:
                    break
                    
    except WebSocketDisconnect:
        logger.info(f"[{client_id}] Disconnected normally")
        
    except Exception as e:
        logger.error(f"[{client_id}] WebSocket error: {e}", exc_info=True)
        
    finally:
        # Cleanup
        if client_id in active_connections:
            del active_connections[client_id]
        
        if hasattr(metrics, 'dec_websocket'):
            metrics.dec_websocket()
        
        try:
            await websocket.close()
        except Exception:
            pass


# =============================================================================
# ERROR HANDLERS
# =============================================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with correlation ID."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "correlation_id": get_correlation_id()
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "correlation_id": get_correlation_id()
        }
    )


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    
    logger.info(f"Starting server on {settings.app_host}:{settings.app_port}")
    
    uvicorn.run(
        "main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=True,
        log_level=settings.log_level.lower(),
        access_log=True
    )
