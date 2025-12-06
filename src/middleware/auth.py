"""
API Key Authentication Middleware.

Provides secure API key validation for production endpoints.
"""

from typing import Optional
from fastapi import Request, HTTPException, Security
from fastapi.security import APIKeyHeader, APIKeyQuery
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from src.config import get_settings
from src.logging_config import get_logger

logger = get_logger(__name__)
settings = get_settings()


# API Key extraction from header or query parameter
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
api_key_query = APIKeyQuery(name="api_key", auto_error=False)


async def get_api_key(
    header_key: Optional[str] = Security(api_key_header),
    query_key: Optional[str] = Security(api_key_query)
) -> str:
    """
    Extract and validate API key from request.
    
    Checks header first, then query parameter.
    
    Args:
        header_key: API key from X-API-Key header
        query_key: API key from ?api_key= query param
        
    Returns:
        Valid API key
        
    Raises:
        HTTPException: If no valid key provided
    """
    api_key = header_key or query_key
    
    if not api_key:
        logger.warning("API request without authentication")
        raise HTTPException(
            status_code=401,
            detail="Missing API key. Provide via X-API-Key header or api_key query parameter"
        )
    
    if not validate_api_key(api_key):
        logger.warning(f"Invalid API key attempt: {api_key[:8]}...")
        raise HTTPException(
            status_code=403,
            detail="Invalid API key"
        )
    
    return api_key


def validate_api_key(api_key: str) -> bool:
    """
    Validate API key against configured keys.
    
    Args:
        api_key: The key to validate
        
    Returns:
        True if valid, False otherwise
    """
    valid_keys = settings.api_keys_list
    
    if not valid_keys:
        # If no API keys configured, allow in development mode
        if settings.environment == "development":
            logger.debug("No API keys configured, allowing in development mode")
            return True
        else:
            logger.error("No API keys configured in production!")
            return False
    
    return api_key in valid_keys


class AuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware to enforce API key authentication.
    
    Allows certain paths to bypass authentication (health, docs, etc.)
    """
    
    # Paths that don't require authentication
    PUBLIC_PATHS = {
        "/",
        "/health",
        "/metrics",
        "/api/docs",
        "/api/redoc",
        "/api/openapi.json",
        "/openapi.json",
        "/docs",
        "/redoc",
        "/favicon.ico"
    }
    
    # Path prefixes that don't require auth
    PUBLIC_PREFIXES = (
        "/api/docs",
        "/api/redoc",
    )
    
    async def dispatch(self, request: Request, call_next):
        """Process request through auth middleware."""
        path = request.url.path
        
        # Allow public paths
        if path in self.PUBLIC_PATHS or path.startswith(self.PUBLIC_PREFIXES):
            return await call_next(request)
        
        # Skip auth in development if disabled
        if settings.environment == "development" and not settings.require_auth_in_dev:
            return await call_next(request)
        
        # Check for API key
        api_key = request.headers.get("X-API-Key") or request.query_params.get("api_key")
        
        if not api_key:
            return JSONResponse(
                status_code=401,
                content={
                    "error": "Authentication required",
                    "detail": "Provide API key via X-API-Key header or api_key query parameter"
                }
            )
        
        if not validate_api_key(api_key):
            return JSONResponse(
                status_code=403,
                content={
                    "error": "Access denied",
                    "detail": "Invalid API key"
                }
            )
        
        # Add user info to request state
        request.state.api_key = api_key
        request.state.authenticated = True
        
        return await call_next(request)


class WebSocketAuthenticator:
    """
    WebSocket authentication helper.
    
    Use at the start of WebSocket handlers to validate connections.
    """
    
    @staticmethod
    async def authenticate(websocket) -> bool:
        """
        Authenticate a WebSocket connection.
        
        Checks for API key in:
        1. Query parameters (?api_key=xxx)
        2. First message (JSON with api_key field)
        
        Args:
            websocket: The WebSocket connection
            
        Returns:
            True if authenticated, False otherwise
        """
        # Check query params first
        api_key = websocket.query_params.get("api_key")
        
        if api_key and validate_api_key(api_key):
            logger.debug("WebSocket authenticated via query parameter")
            return True
        
        # In development without auth requirement, allow
        if settings.environment == "development" and not settings.require_auth_in_dev:
            return True
        
        return False
    
    @staticmethod
    async def authenticate_message(message: dict) -> bool:
        """
        Authenticate via message payload.
        
        Args:
            message: Parsed JSON message with potential api_key field
            
        Returns:
            True if authenticated
        """
        api_key = message.get("api_key")
        if api_key and validate_api_key(api_key):
            return True
        return False


# Export for easy import
__all__ = [
    "get_api_key",
    "validate_api_key",
    "AuthMiddleware",
    "WebSocketAuthenticator",
    "api_key_header",
    "api_key_query"
]
