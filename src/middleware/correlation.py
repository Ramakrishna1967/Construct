"""
Correlation ID Middleware for Request Tracing.

Provides request correlation IDs for distributed tracing.
"""

import uuid
from contextvars import ContextVar
from typing import Optional

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from src.logging_config import get_logger

logger = get_logger(__name__)

# Context variable for correlation ID
_correlation_id: ContextVar[Optional[str]] = ContextVar('correlation_id', default=None)


def get_correlation_id() -> Optional[str]:
    """Get the current correlation ID."""
    return _correlation_id.get()


def set_correlation_id(correlation_id: str) -> None:
    """Set the current correlation ID."""
    _correlation_id.set(correlation_id)


def generate_correlation_id() -> str:
    """Generate a new correlation ID."""
    return str(uuid.uuid4())


class CorrelationMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add correlation IDs to requests.
    
    Features:
    - Generates or propagates correlation IDs
    - Adds to response headers
    - Sets context variable for logging
    """
    
    HEADER_NAME = "X-Correlation-ID"
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Add correlation ID to request context."""
        # Get or generate correlation ID
        correlation_id = request.headers.get(self.HEADER_NAME)
        
        if not correlation_id:
            correlation_id = generate_correlation_id()
        
        # Set in context
        set_correlation_id(correlation_id)
        
        # Store in request state for access in route handlers
        request.state.correlation_id = correlation_id
        
        # Process request
        response = await call_next(request)
        
        # Add to response headers
        response.headers[self.HEADER_NAME] = correlation_id
        
        return response


class CorrelationLogFilter:
    """
    Logging filter that adds correlation ID to log records.
    
    Usage:
        handler.addFilter(CorrelationLogFilter())
    """
    
    def filter(self, record):
        """Add correlation_id to log record."""
        record.correlation_id = get_correlation_id() or "none"
        return True


def correlation_context(correlation_id: str = None):
    """
    Context manager for setting correlation ID.
    
    Usage:
        with correlation_context("my-id"):
            # Code within this context has correlation ID set
            pass
    """
    class CorrelationContext:
        def __init__(self, cid):
            self.cid = cid or generate_correlation_id()
            self.token = None
        
        def __enter__(self):
            self.token = _correlation_id.set(self.cid)
            return self.cid
        
        def __exit__(self, *args):
            _correlation_id.reset(self.token)
    
    return CorrelationContext(correlation_id)
