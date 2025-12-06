"""
Enhanced Logging Configuration with Structured Logging.

Provides:
- Structured JSON logging
- Correlation ID injection
- Performance metrics
- Error context enrichment
"""

import logging
import sys
import os
from typing import Optional
from datetime import datetime

from src.config import get_settings

# Lazy import structlog
_structlog = None


def _get_structlog():
    """Lazily import structlog."""
    global _structlog
    if _structlog is None:
        try:
            import structlog
            _structlog = structlog
        except ImportError:
            _structlog = False
    return _structlog


class CorrelationFilter(logging.Filter):
    """Filter that adds correlation ID to log records."""
    
    def filter(self, record):
        try:
            from src.middleware.correlation import get_correlation_id
            record.correlation_id = get_correlation_id() or "-"
        except (ImportError, Exception):
            record.correlation_id = "-"
        return True


class JsonFormatter(logging.Formatter):
    """JSON log formatter for structured logging."""
    
    def format(self, record):
        import json
        
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": getattr(record, "correlation_id", "-")
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields
        for key in ["duration_ms", "method", "path", "status_code"]:
            if hasattr(record, key):
                log_data[key] = getattr(record, key)
        
        return json.dumps(log_data)


def setup_logging(use_json: bool = None):
    """
    Configure logging for the application.
    
    Args:
        use_json: Whether to use JSON formatting (defaults to non-dev environments)
    """
    settings = get_settings()
    
    # Determine if we should use JSON format
    if use_json is None:
        use_json = os.environ.get("ENV", "development") != "development"
    
    # Get log level
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Clear existing handlers
    root_logger.handlers = []
    
    # Create handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(log_level)
    
    # Add correlation filter
    handler.addFilter(CorrelationFilter())
    
    # Set formatter
    if use_json:
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(logging.Formatter(
            "[%(asctime)s] %(levelname)s [%(correlation_id)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        ))
    
    root_logger.addHandler(handler)
    
    # Configure structlog if available
    structlog = _get_structlog()
    if structlog and structlog is not False:
        structlog.configure(
            processors=[
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                structlog.processors.JSONRenderer() if use_json else structlog.dev.ConsoleRenderer()
            ],
            wrapper_class=structlog.stdlib.BoundLogger,
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True
        )
    
    # Set log levels for noisy libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
    
    return root_logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance.
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        Configured logger instance
    """
    structlog = _get_structlog()
    
    if structlog and structlog is not False:
        return structlog.get_logger(name)
    
    return logging.getLogger(name)


class LogContext:
    """
    Context manager for adding temporary context to logs.
    
    Usage:
        with LogContext(user_id="123", action="login"):
            logger.info("User action")
    """
    
    def __init__(self, **kwargs):
        self.context = kwargs
        self._old_factory = None
    
    def __enter__(self):
        self._old_factory = logging.getLogRecordFactory()
        context = self.context
        
        def record_factory(*args, **kwargs):
            record = self._old_factory(*args, **kwargs)
            for key, value in context.items():
                setattr(record, key, value)
            return record
        
        logging.setLogRecordFactory(record_factory)
        return self
    
    def __exit__(self, *args):
        logging.setLogRecordFactory(self._old_factory)
