"""
Prometheus Metrics Middleware.

Provides request metrics collection for monitoring.
"""

import time
from typing import Dict, Optional
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from src.logging_config import get_logger

logger = get_logger(__name__)

# Lazy import prometheus_client
_prometheus_available = None


def _check_prometheus():
    """Check if prometheus_client is available."""
    global _prometheus_available
    if _prometheus_available is None:
        try:
            import prometheus_client
            _prometheus_available = True
            logger.info("Prometheus client available")
        except ImportError:
            _prometheus_available = False
            logger.warning("Prometheus client not available")
    return _prometheus_available


class SimpleMetrics:
    """Simple in-memory metrics when Prometheus is not available."""
    
    def __init__(self):
        self.request_count: Dict[str, int] = {}
        self.request_latency: Dict[str, list] = {}
        self.error_count: Dict[str, int] = {}
    
    def record_request(self, method: str, path: str, status: int, duration: float):
        """Record a request."""
        key = f"{method}:{path}"
        
        self.request_count[key] = self.request_count.get(key, 0) + 1
        
        if key not in self.request_latency:
            self.request_latency[key] = []
        self.request_latency[key].append(duration)
        # Keep only last 100 samples
        self.request_latency[key] = self.request_latency[key][-100:]
        
        if status >= 400:
            error_key = f"{key}:{status}"
            self.error_count[error_key] = self.error_count.get(error_key, 0) + 1
    
    def get_stats(self) -> Dict:
        """Get current stats."""
        stats = {
            "requests": self.request_count.copy(),
            "errors": self.error_count.copy(),
            "latency": {}
        }
        
        for key, values in self.request_latency.items():
            if values:
                stats["latency"][key] = {
                    "avg_ms": sum(values) / len(values) * 1000,
                    "count": len(values)
                }
        
        return stats


class PrometheusMetrics:
    """Prometheus-based metrics."""
    
    def __init__(self):
        from prometheus_client import Counter, Histogram, Gauge
        
        self.request_count = Counter(
            "http_requests_total",
            "Total HTTP requests",
            ["method", "path", "status"]
        )
        
        self.request_latency = Histogram(
            "http_request_duration_seconds",
            "HTTP request latency",
            ["method", "path"],
            buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
        )
        
        self.active_requests = Gauge(
            "http_requests_active",
            "Currently active HTTP requests"
        )
        
        self.websocket_connections = Gauge(
            "websocket_connections_active",
            "Currently active WebSocket connections"
        )
    
    def record_request(self, method: str, path: str, status: int, duration: float):
        """Record a request."""
        self.request_count.labels(method=method, path=path, status=str(status)).inc()
        self.request_latency.labels(method=method, path=path).observe(duration)
    
    def inc_active(self):
        """Increment active requests."""
        self.active_requests.inc()
    
    def dec_active(self):
        """Decrement active requests."""
        self.active_requests.dec()
    
    def inc_websocket(self):
        """Increment WebSocket connections."""
        self.websocket_connections.inc()
    
    def dec_websocket(self):
        """Decrement WebSocket connections."""
        self.websocket_connections.dec()


class MetricsMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for collecting request metrics."""
    
    def __init__(self, app, metrics=None, exclude_paths: list = None):
        """
        Initialize middleware.
        
        Args:
            app: FastAPI application
            metrics: Optional metrics instance
            exclude_paths: Paths to exclude from metrics
        """
        super().__init__(app)
        
        if metrics:
            self.metrics = metrics
        elif _check_prometheus():
            self.metrics = PrometheusMetrics()
        else:
            self.metrics = SimpleMetrics()
        
        self.exclude_paths = exclude_paths or ["/health", "/metrics"]
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Collect metrics for request."""
        # Skip excluded paths
        if any(request.url.path.startswith(p) for p in self.exclude_paths):
            return await call_next(request)
        
        # Track active requests if using Prometheus
        if hasattr(self.metrics, 'inc_active'):
            self.metrics.inc_active()
        
        start = time.time()
        
        try:
            response = await call_next(request)
            duration = time.time() - start
            
            # Record metrics
            self.metrics.record_request(
                method=request.method,
                path=self._normalize_path(request.url.path),
                status=response.status_code,
                duration=duration
            )
            
            return response
            
        finally:
            if hasattr(self.metrics, 'dec_active'):
                self.metrics.dec_active()
    
    def _normalize_path(self, path: str) -> str:
        """Normalize path for metrics (replace IDs with placeholders)."""
        import re
        # Replace UUIDs
        path = re.sub(
            r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',
            ':id',
            path
        )
        # Replace numeric IDs
        path = re.sub(r'/\d+', '/:id', path)
        return path


# Global metrics instance
_metrics = None


def get_metrics():
    """Get or create global metrics instance."""
    global _metrics
    if _metrics is None:
        if _check_prometheus():
            _metrics = PrometheusMetrics()
        else:
            _metrics = SimpleMetrics()
    return _metrics


def get_metrics_endpoint_response():
    """Generate metrics endpoint response."""
    if _check_prometheus():
        from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
        return generate_latest(), CONTENT_TYPE_LATEST
    else:
        metrics = get_metrics()
        return metrics.get_stats(), "application/json"
