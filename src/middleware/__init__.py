"""
Middleware package for production features.
"""

from src.middleware.rate_limiter import RateLimiter, rate_limit_middleware
from src.middleware.metrics import MetricsMiddleware, get_metrics
from src.middleware.correlation import CorrelationMiddleware, get_correlation_id
from src.middleware.auth import AuthMiddleware, WebSocketAuthenticator, get_api_key

__all__ = [
    "RateLimiter",
    "rate_limit_middleware",
    "MetricsMiddleware",
    "get_metrics",
    "CorrelationMiddleware",
    "get_correlation_id",
    "AuthMiddleware",
    "WebSocketAuthenticator",
    "get_api_key"
]
