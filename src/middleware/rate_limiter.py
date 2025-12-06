"""
Rate Limiting Middleware using Token Bucket algorithm.

Provides configurable rate limiting per client IP.
"""

import time
import asyncio
from typing import Dict, Optional
from dataclasses import dataclass, field
from collections import defaultdict

from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from src.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class TokenBucket:
    """Token bucket for rate limiting."""
    capacity: int
    tokens: float = field(default=0)
    refill_rate: float = 1.0  # tokens per second
    last_update: float = field(default_factory=time.time)
    
    def consume(self, tokens: int = 1) -> bool:
        """
        Try to consume tokens.
        
        Args:
            tokens: Number of tokens to consume
            
        Returns:
            True if tokens were consumed, False if not enough tokens
        """
        now = time.time()
        time_passed = now - self.last_update
        self.last_update = now
        
        # Refill tokens
        self.tokens = min(
            self.capacity,
            self.tokens + time_passed * self.refill_rate
        )
        
        # Try to consume
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False
    
    @property
    def remaining(self) -> int:
        """Get remaining tokens."""
        return int(self.tokens)


class RateLimiter:
    """
    Rate limiter using token bucket algorithm.
    
    Features:
    - Per-client rate limiting
    - Configurable limits
    - Automatic cleanup of old buckets
    """
    
    def __init__(
        self,
        requests_per_minute: int = 60,
        burst_size: int = 10,
        cleanup_interval: int = 300
    ):
        """
        Initialize rate limiter.
        
        Args:
            requests_per_minute: Maximum sustained requests per minute
            burst_size: Maximum burst size
            cleanup_interval: Interval for cleaning up old buckets (seconds)
        """
        self.requests_per_minute = requests_per_minute
        self.burst_size = burst_size
        self.cleanup_interval = cleanup_interval
        
        self.buckets: Dict[str, TokenBucket] = {}
        self._lock = asyncio.Lock()
        self._last_cleanup = time.time()
        
        logger.info(
            f"RateLimiter initialized: {requests_per_minute}/min, burst={burst_size}"
        )
    
    async def is_allowed(self, client_id: str) -> tuple[bool, int]:
        """
        Check if request is allowed.
        
        Args:
            client_id: Client identifier (usually IP)
            
        Returns:
            Tuple of (allowed, remaining_tokens)
        """
        async with self._lock:
            # Cleanup old buckets periodically
            now = time.time()
            if now - self._last_cleanup > self.cleanup_interval:
                await self._cleanup()
                self._last_cleanup = now
            
            # Get or create bucket
            if client_id not in self.buckets:
                self.buckets[client_id] = TokenBucket(
                    capacity=self.burst_size,
                    tokens=self.burst_size,
                    refill_rate=self.requests_per_minute / 60.0
                )
            
            bucket = self.buckets[client_id]
            allowed = bucket.consume(1)
            
            if not allowed:
                logger.warning(f"Rate limit exceeded for {client_id}")
            
            return allowed, bucket.remaining
    
    async def _cleanup(self):
        """Remove inactive buckets."""
        now = time.time()
        inactive_threshold = 300  # 5 minutes
        
        to_remove = [
            client_id
            for client_id, bucket in self.buckets.items()
            if now - bucket.last_update > inactive_threshold
        ]
        
        for client_id in to_remove:
            del self.buckets[client_id]
        
        if to_remove:
            logger.debug(f"Cleaned up {len(to_remove)} inactive rate limit buckets")


class RateLimitMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for rate limiting."""
    
    def __init__(
        self,
        app,
        limiter: Optional[RateLimiter] = None,
        requests_per_minute: int = 60,
        exclude_paths: list = None
    ):
        """
        Initialize middleware.
        
        Args:
            app: FastAPI application
            limiter: Optional existing RateLimiter instance
            requests_per_minute: Rate limit if creating new limiter
            exclude_paths: Paths to exclude from rate limiting
        """
        super().__init__(app)
        self.limiter = limiter or RateLimiter(requests_per_minute=requests_per_minute)
        self.exclude_paths = exclude_paths or ["/health", "/metrics"]
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request through rate limiter."""
        # Skip excluded paths
        if any(request.url.path.startswith(p) for p in self.exclude_paths):
            return await call_next(request)
        
        # Get client identifier
        client_id = self._get_client_id(request)
        
        # Check rate limit
        allowed, remaining = await self.limiter.is_allowed(client_id)
        
        if not allowed:
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded. Please try again later.",
                headers={
                    "X-RateLimit-Remaining": "0",
                    "Retry-After": "60"
                }
            )
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Limit"] = str(self.limiter.requests_per_minute)
        
        return response
    
    def _get_client_id(self, request: Request) -> str:
        """Get client identifier from request."""
        # Check for forwarded IP
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        
        # Fall back to direct client IP
        return request.client.host if request.client else "unknown"


# Global rate limiter instance
_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """Get or create global rate limiter."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter


async def rate_limit_middleware(request: Request, call_next):
    """Simple rate limit middleware function."""
    limiter = get_rate_limiter()
    client_id = request.client.host if request.client else "unknown"
    
    allowed, _ = await limiter.is_allowed(client_id)
    if not allowed:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    return await call_next(request)
