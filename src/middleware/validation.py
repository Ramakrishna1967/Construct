"""
Input Validation Middleware.

Provides request validation, sanitization, and size limits.
"""

import re
from typing import Optional, Set
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from src.config import get_settings
from src.logging_config import get_logger

logger = get_logger(__name__)
settings = get_settings()


class InputValidationMiddleware(BaseHTTPMiddleware):
    """
    Middleware for validating and sanitizing request inputs.
    
    Features:
    - Request body size limits
    - Content-Type validation
    - Basic input sanitization
    """
    
    # Maximum request body size (10MB default)
    MAX_BODY_SIZE = 10 * 1024 * 1024
    
    # Allowed content types
    ALLOWED_CONTENT_TYPES: Set[str] = {
        "application/json",
        "text/plain",
        "multipart/form-data"
    }
    
    # Paths that skip validation
    SKIP_PATHS: Set[str] = {
        "/health",
        "/health/live",
        "/health/ready",
        "/metrics",
        "/api/docs",
        "/api/redoc",
        "/api/openapi.json"
    }
    
    async def dispatch(self, request: Request, call_next):
        """Process request through validation middleware."""
        path = request.url.path
        
        # Skip validation for certain paths
        if path in self.SKIP_PATHS:
            return await call_next(request)
        
        # Check content length
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                size = int(content_length)
                if size > self.MAX_BODY_SIZE:
                    logger.warning(f"Request body too large: {size} bytes")
                    return JSONResponse(
                        status_code=413,
                        content={
                            "error": "Request body too large",
                            "max_size_bytes": self.MAX_BODY_SIZE
                        }
                    )
            except ValueError:
                pass
        
        # Validate content type for POST/PUT/PATCH
        if request.method in ["POST", "PUT", "PATCH"]:
            content_type = request.headers.get("content-type", "")
            content_type_base = content_type.split(";")[0].strip()
            
            if content_type_base and content_type_base not in self.ALLOWED_CONTENT_TYPES:
                logger.warning(f"Invalid content type: {content_type}")
                return JSONResponse(
                    status_code=415,
                    content={
                        "error": "Unsupported media type",
                        "allowed_types": list(self.ALLOWED_CONTENT_TYPES)
                    }
                )
        
        return await call_next(request)


def sanitize_input(text: str, max_length: int = 50000) -> str:
    """
    Sanitize user input text.
    
    Args:
        text: Input text to sanitize
        max_length: Maximum allowed length
        
    Returns:
        Sanitized text
    """
    if not text:
        return ""
    
    # Truncate to max length
    if len(text) > max_length:
        text = text[:max_length]
        logger.warning(f"Input truncated to {max_length} characters")
    
    # Remove null bytes
    text = text.replace("\x00", "")
    
    # Normalize line endings
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    
    return text


def validate_session_id(session_id: Optional[str]) -> Optional[str]:
    """
    Validate and sanitize session ID.
    
    Args:
        session_id: Session ID to validate
        
    Returns:
        Valid session ID or None
        
    Raises:
        ValueError: If session ID is invalid
    """
    if not session_id:
        return None
    
    # Session ID should be alphanumeric with hyphens/underscores
    pattern = r'^[a-zA-Z0-9_-]{1,64}$'
    
    if not re.match(pattern, session_id):
        raise ValueError(
            "Invalid session_id format. Must be 1-64 alphanumeric characters, "
            "hyphens, or underscores."
        )
    
    return session_id


def validate_message(message: str, min_length: int = 1, max_length: int = 50000) -> str:
    """
    Validate user message.
    
    Args:
        message: Message to validate
        min_length: Minimum required length
        max_length: Maximum allowed length
        
    Returns:
        Validated message
        
    Raises:
        ValueError: If message is invalid
    """
    if not message or len(message.strip()) < min_length:
        raise ValueError(f"Message must be at least {min_length} character(s)")
    
    if len(message) > max_length:
        raise ValueError(f"Message exceeds maximum length of {max_length} characters")
    
    return sanitize_input(message, max_length)


__all__ = [
    "InputValidationMiddleware",
    "sanitize_input",
    "validate_session_id",
    "validate_message"
]
