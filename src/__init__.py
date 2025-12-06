"""
AI Code Reviewer Backend - Source Package

Production-grade agentic AI code review system.
"""

from src.config import get_settings
from src.logging_config import setup_logging, get_logger

__version__ = "2.0.0"
__author__ = "AI Code Reviewer Team"

__all__ = [
    "get_settings",
    "setup_logging",
    "get_logger",
    "__version__"
]
