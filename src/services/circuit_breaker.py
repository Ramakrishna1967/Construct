"""
Circuit Breaker and Reliability Patterns.

Provides fault tolerance mechanisms for external service calls.
"""

import asyncio
import time
from typing import Optional, Callable, Any
from enum import Enum
from dataclasses import dataclass, field
from functools import wraps

from src.logging_config import get_logger

logger = get_logger(__name__)


class CircuitState(str, Enum):
    """Circuit breaker states."""
    CLOSED = "closed"       # Normal operation
    OPEN = "open"          # Failing, reject calls
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""
    failure_threshold: int = 5       # Failures before opening
    success_threshold: int = 2       # Successes to close from half-open
    timeout_seconds: float = 30.0    # Time before trying half-open
    call_timeout: float = 10.0       # Timeout for individual calls


@dataclass
class CircuitBreakerState:
    """Current state of a circuit breaker."""
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: float = 0
    last_state_change: float = field(default_factory=time.time)


class CircuitBreaker:
    """
    Circuit breaker implementation for fault tolerance.
    
    Prevents cascading failures by failing fast when a service is unhealthy.
    """
    
    def __init__(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None
    ):
        """
        Initialize circuit breaker.
        
        Args:
            name: Identifier for this circuit breaker
            config: Configuration parameters
        """
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self._state = CircuitBreakerState()
        self._lock = asyncio.Lock()
        
        logger.debug(f"Circuit breaker '{name}' initialized")
    
    @property
    def state(self) -> CircuitState:
        """Get current circuit state."""
        return self._state.state
    
    @property
    def is_closed(self) -> bool:
        """Check if circuit is closed (healthy)."""
        return self._state.state == CircuitState.CLOSED
    
    async def _check_state_transition(self) -> None:
        """Check if state should transition based on timeout."""
        if self._state.state == CircuitState.OPEN:
            time_since_failure = time.time() - self._state.last_failure_time
            if time_since_failure >= self.config.timeout_seconds:
                logger.info(f"Circuit '{self.name}' transitioning to HALF_OPEN")
                self._state.state = CircuitState.HALF_OPEN
                self._state.success_count = 0
                self._state.last_state_change = time.time()
    
    async def _record_success(self) -> None:
        """Record a successful call."""
        async with self._lock:
            if self._state.state == CircuitState.HALF_OPEN:
                self._state.success_count += 1
                if self._state.success_count >= self.config.success_threshold:
                    logger.info(f"Circuit '{self.name}' closing after recovery")
                    self._state.state = CircuitState.CLOSED
                    self._state.failure_count = 0
                    self._state.last_state_change = time.time()
            elif self._state.state == CircuitState.CLOSED:
                # Reset failure count on success
                self._state.failure_count = max(0, self._state.failure_count - 1)
    
    async def _record_failure(self) -> None:
        """Record a failed call."""
        async with self._lock:
            self._state.failure_count += 1
            self._state.last_failure_time = time.time()
            
            if self._state.state == CircuitState.HALF_OPEN:
                logger.warning(f"Circuit '{self.name}' reopening after failure in half-open")
                self._state.state = CircuitState.OPEN
                self._state.last_state_change = time.time()
            elif self._state.state == CircuitState.CLOSED:
                if self._state.failure_count >= self.config.failure_threshold:
                    logger.warning(
                        f"Circuit '{self.name}' opening after {self._state.failure_count} failures"
                    )
                    self._state.state = CircuitState.OPEN
                    self._state.last_state_change = time.time()
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute a function through the circuit breaker.
        
        Args:
            func: Async function to call
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Function result
            
        Raises:
            CircuitOpenError: If circuit is open
            Original exception: If call fails
        """
        await self._check_state_transition()
        
        if self._state.state == CircuitState.OPEN:
            raise CircuitOpenError(
                f"Circuit '{self.name}' is open. Service unavailable."
            )
        
        try:
            # Execute with timeout
            result = await asyncio.wait_for(
                func(*args, **kwargs),
                timeout=self.config.call_timeout
            )
            await self._record_success()
            return result
            
        except asyncio.TimeoutError:
            logger.warning(f"Circuit '{self.name}' call timed out")
            await self._record_failure()
            raise
            
        except Exception as e:
            logger.warning(f"Circuit '{self.name}' call failed: {e}")
            await self._record_failure()
            raise
    
    def get_status(self) -> dict:
        """Get current circuit breaker status."""
        return {
            "name": self.name,
            "state": self._state.state.value,
            "failure_count": self._state.failure_count,
            "success_count": self._state.success_count,
            "last_failure": self._state.last_failure_time,
            "last_state_change": self._state.last_state_change
        }


class CircuitOpenError(Exception):
    """Raised when circuit breaker is open."""
    pass


# Global circuit breakers for services
_circuit_breakers: dict = {}


def get_circuit_breaker(name: str) -> CircuitBreaker:
    """Get or create a circuit breaker by name."""
    if name not in _circuit_breakers:
        _circuit_breakers[name] = CircuitBreaker(name)
    return _circuit_breakers[name]


def circuit_breaker(name: str):
    """
    Decorator to wrap async functions with circuit breaker.
    
    Args:
        name: Circuit breaker name
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cb = get_circuit_breaker(name)
            return await cb.call(func, *args, **kwargs)
        return wrapper
    return decorator


def get_all_circuit_statuses() -> dict:
    """Get status of all circuit breakers."""
    return {name: cb.get_status() for name, cb in _circuit_breakers.items()}


# Pre-register common circuit breakers
def init_circuit_breakers():
    """Initialize circuit breakers for common services."""
    get_circuit_breaker("redis")
    get_circuit_breaker("chromadb")
    get_circuit_breaker("llm")
    get_circuit_breaker("docker")
    logger.info("Circuit breakers initialized for: redis, chromadb, llm, docker")


__all__ = [
    "CircuitBreaker",
    "CircuitBreakerConfig",
    "CircuitOpenError",
    "CircuitState",
    "get_circuit_breaker",
    "circuit_breaker",
    "get_all_circuit_statuses",
    "init_circuit_breakers"
]
