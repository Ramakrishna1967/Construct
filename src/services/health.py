"""
Comprehensive Health Check Service.

Provides detailed health status for all backend components.
"""

import asyncio
import time
from typing import Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum

from src.config import get_settings
from src.logging_config import get_logger

logger = get_logger(__name__)
settings = get_settings()


class HealthStatus(str, Enum):
    """Health check status values."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class ComponentHealth:
    """Health status of a single component."""
    name: str
    status: HealthStatus
    latency_ms: Optional[float] = None
    message: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            "name": self.name,
            "status": self.status.value,
        }
        if self.latency_ms is not None:
            result["latency_ms"] = round(self.latency_ms, 2)
        if self.message:
            result["message"] = self.message
        if self.details:
            result["details"] = self.details
        return result


@dataclass
class SystemHealth:
    """Overall system health status."""
    status: HealthStatus
    timestamp: str
    version: str
    environment: str
    uptime_seconds: float
    components: Dict[str, ComponentHealth]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status.value,
            "timestamp": self.timestamp,
            "version": self.version,
            "environment": self.environment,
            "uptime_seconds": round(self.uptime_seconds, 2),
            "components": {
                name: comp.to_dict() 
                for name, comp in self.components.items()
            }
        }


class HealthChecker:
    """
    Comprehensive health checker for all backend components.
    
    Checks:
    - Redis connectivity and latency
    - ChromaDB status
    - LLM/Model configuration
    - Docker availability
    - Memory and resource usage
    """
    
    _start_time: float = time.time()
    
    def __init__(self):
        self.logger = get_logger(f"{__name__}.HealthChecker")
    
    async def check_redis(self) -> ComponentHealth:
        """Check Redis health and latency."""
        start = time.time()
        try:
            from src.services.redis_store import RedisStore
            
            redis = RedisStore()
            is_healthy = await redis.health_check()
            latency = (time.time() - start) * 1000
            
            if is_healthy:
                return ComponentHealth(
                    name="redis",
                    status=HealthStatus.HEALTHY,
                    latency_ms=latency,
                    message="Connected and responsive"
                )
            else:
                return ComponentHealth(
                    name="redis",
                    status=HealthStatus.UNHEALTHY,
                    latency_ms=latency,
                    message="Health check failed"
                )
                
        except Exception as e:
            latency = (time.time() - start) * 1000
            self.logger.error(f"Redis health check error: {e}")
            return ComponentHealth(
                name="redis",
                status=HealthStatus.UNHEALTHY,
                latency_ms=latency,
                message=f"Connection error: {str(e)[:100]}"
            )
    
    async def check_chromadb(self) -> ComponentHealth:
        """Check ChromaDB/vector store health."""
        start = time.time()
        try:
            from src.services.vector_store import get_vector_store
            
            vector_store = get_vector_store()
            stats = vector_store.get_stats()
            latency = (time.time() - start) * 1000
            
            if stats.get("status") == "initialized":
                return ComponentHealth(
                    name="chromadb",
                    status=HealthStatus.HEALTHY,
                    latency_ms=latency,
                    message="Vector store operational",
                    details={
                        "collection": stats.get("collection"),
                        "document_count": stats.get("document_count", 0),
                        "persistent": stats.get("persistent", False)
                    }
                )
            elif stats.get("status") == "not_initialized":
                return ComponentHealth(
                    name="chromadb",
                    status=HealthStatus.DEGRADED,
                    latency_ms=latency,
                    message="Not initialized (will initialize on first use)"
                )
            else:
                return ComponentHealth(
                    name="chromadb",
                    status=HealthStatus.UNHEALTHY,
                    latency_ms=latency,
                    message=stats.get("error", "Unknown error")
                )
                
        except ImportError:
            return ComponentHealth(
                name="chromadb",
                status=HealthStatus.DEGRADED,
                message="ChromaDB not installed (semantic search disabled)"
            )
        except Exception as e:
            latency = (time.time() - start) * 1000
            self.logger.error(f"ChromaDB health check error: {e}")
            return ComponentHealth(
                name="chromadb",
                status=HealthStatus.UNHEALTHY,
                latency_ms=latency,
                message=f"Error: {str(e)[:100]}"
            )
    
    async def check_llm(self) -> ComponentHealth:
        """Check LLM configuration and availability."""
        start = time.time()
        try:
            # Check if API key is configured
            if not settings.google_api_key:
                return ComponentHealth(
                    name="llm",
                    status=HealthStatus.UNHEALTHY,
                    message="GOOGLE_API_KEY not configured"
                )
            
            # Verify key format (basic check)
            if len(settings.google_api_key) < 10:
                return ComponentHealth(
                    name="llm",
                    status=HealthStatus.UNHEALTHY,
                    message="Invalid API key format"
                )
            
            latency = (time.time() - start) * 1000
            
            return ComponentHealth(
                name="llm",
                status=HealthStatus.HEALTHY,
                latency_ms=latency,
                message="API key configured",
                details={
                    "model": settings.gemini_model,
                    "temperature": settings.gemini_temperature
                }
            )
            
        except Exception as e:
            latency = (time.time() - start) * 1000
            return ComponentHealth(
                name="llm",
                status=HealthStatus.UNHEALTHY,
                latency_ms=latency,
                message=f"Error: {str(e)[:100]}"
            )
    
    async def check_docker(self) -> ComponentHealth:
        """Check Docker availability."""
        start = time.time()
        try:
            import docker
            
            client = docker.from_env()
            client.ping()
            latency = (time.time() - start) * 1000
            
            return ComponentHealth(
                name="docker",
                status=HealthStatus.HEALTHY,
                latency_ms=latency,
                message="Docker daemon accessible",
                details={
                    "image": settings.docker_image
                }
            )
            
        except ImportError:
            return ComponentHealth(
                name="docker",
                status=HealthStatus.DEGRADED,
                message="Docker SDK not installed (sandbox disabled)"
            )
        except Exception as e:
            latency = (time.time() - start) * 1000
            # Docker not available is common in cloud deployments
            return ComponentHealth(
                name="docker",
                status=HealthStatus.DEGRADED,
                latency_ms=latency,
                message=f"Docker not available: {str(e)[:50]}"
            )
    
    async def check_circuit_breakers(self) -> ComponentHealth:
        """Check circuit breaker statuses."""
        try:
            from src.services.circuit_breaker import get_all_circuit_statuses
            
            statuses = get_all_circuit_statuses()
            
            # Check if any circuits are open
            open_circuits = [
                name for name, status in statuses.items()
                if status.get("state") == "open"
            ]
            
            if open_circuits:
                return ComponentHealth(
                    name="circuit_breakers",
                    status=HealthStatus.DEGRADED,
                    message=f"Open circuits: {', '.join(open_circuits)}",
                    details=statuses
                )
            
            return ComponentHealth(
                name="circuit_breakers",
                status=HealthStatus.HEALTHY,
                message="All circuits closed",
                details=statuses
            )
            
        except Exception as e:
            return ComponentHealth(
                name="circuit_breakers",
                status=HealthStatus.UNKNOWN,
                message=f"Error checking: {str(e)[:50]}"
            )
    
    async def get_full_health(self) -> SystemHealth:
        """
        Get comprehensive health status of all components.
        
        Returns:
            SystemHealth with all component statuses
        """
        # Run all health checks concurrently
        redis_task = asyncio.create_task(self.check_redis())
        chromadb_task = asyncio.create_task(self.check_chromadb())
        llm_task = asyncio.create_task(self.check_llm())
        docker_task = asyncio.create_task(self.check_docker())
        cb_task = asyncio.create_task(self.check_circuit_breakers())
        
        # Wait for all checks with timeout
        try:
            results = await asyncio.wait_for(
                asyncio.gather(
                    redis_task, chromadb_task, llm_task, 
                    docker_task, cb_task,
                    return_exceptions=True
                ),
                timeout=10.0
            )
        except asyncio.TimeoutError:
            self.logger.error("Health check timeout")
            results = [
                ComponentHealth(name="timeout", status=HealthStatus.UNHEALTHY, 
                              message="Health checks timed out")
            ]
        
        # Build components dict
        components = {}
        for result in results:
            if isinstance(result, ComponentHealth):
                components[result.name] = result
            elif isinstance(result, Exception):
                self.logger.error(f"Health check error: {result}")
        
        # Determine overall status
        statuses = [c.status for c in components.values()]
        
        if HealthStatus.UNHEALTHY in statuses:
            overall = HealthStatus.UNHEALTHY
        elif HealthStatus.DEGRADED in statuses:
            overall = HealthStatus.DEGRADED
        elif all(s == HealthStatus.HEALTHY for s in statuses):
            overall = HealthStatus.HEALTHY
        else:
            overall = HealthStatus.DEGRADED
        
        return SystemHealth(
            status=overall,
            timestamp=datetime.utcnow().isoformat(),
            version="2.0.0",
            environment=settings.environment,
            uptime_seconds=time.time() - self._start_time,
            components=components
        )
    
    async def get_liveness(self) -> Dict[str, Any]:
        """Simple liveness probe (is the app running?)."""
        return {
            "status": "alive",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def get_readiness(self) -> Dict[str, Any]:
        """
        Readiness probe (is the app ready to serve traffic?).
        
        Checks critical components only.
        """
        redis_health = await self.check_redis()
        llm_health = await self.check_llm()
        
        is_ready = (
            redis_health.status != HealthStatus.UNHEALTHY and
            llm_health.status == HealthStatus.HEALTHY
        )
        
        return {
            "ready": is_ready,
            "timestamp": datetime.utcnow().isoformat(),
            "checks": {
                "redis": redis_health.status.value,
                "llm": llm_health.status.value
            }
        }


# Global health checker instance
_health_checker: Optional[HealthChecker] = None


def get_health_checker() -> HealthChecker:
    """Get or create the global health checker instance."""
    global _health_checker
    if _health_checker is None:
        _health_checker = HealthChecker()
    return _health_checker


__all__ = [
    "HealthChecker",
    "HealthStatus",
    "ComponentHealth",
    "SystemHealth",
    "get_health_checker"
]
