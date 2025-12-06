"""
LangSmith Tracing Service for AI Code Reviewer.

Provides observability and tracing for LLM calls with automatic
callback configuration and run metadata tagging.
"""

import os
import functools
from typing import Optional, Dict, Any, Callable
from datetime import datetime

from langchain_core.tracers import LangChainTracer
from langchain_core.callbacks import CallbackManager

from src.config import get_settings
from src.logging_config import get_logger

logger = get_logger(__name__)
settings = get_settings()


class TracingService:
    """
    LangSmith tracing service with automatic configuration.
    
    Provides tracing callbacks for LLM calls and custom span annotations.
    """
    
    _instance: Optional['TracingService'] = None
    _initialized: bool = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self.enabled = settings.langchain_tracing_enabled
        self.project_name = settings.langchain_project
        self.tracer: Optional[LangChainTracer] = None
        
        if self.enabled:
            self._setup_tracing()
        else:
            logger.info("LangSmith tracing is disabled")
        
        self._initialized = True
    
    def _setup_tracing(self) -> None:
        """Initialize LangSmith tracing if API key is available."""
        api_key = settings.langchain_api_key
        
        if not api_key or api_key == "":
            logger.warning(
                "LANGCHAIN_API_KEY not set. Tracing disabled. "
                "Get a free key at: https://smith.langchain.com"
            )
            self.enabled = False
            return
        
        try:
            # Set environment variables for LangChain
            os.environ["LANGCHAIN_TRACING_V2"] = "true"
            os.environ["LANGCHAIN_API_KEY"] = api_key
            os.environ["LANGCHAIN_PROJECT"] = self.project_name
            
            # Create tracer
            self.tracer = LangChainTracer(project_name=self.project_name)
            
            logger.info(f"LangSmith tracing enabled for project: {self.project_name}")
            logger.info("View traces at: https://smith.langchain.com")
            
        except Exception as e:
            logger.error(f"Failed to initialize LangSmith tracing: {e}")
            self.enabled = False
    
    def get_callback_manager(
        self,
        session_id: Optional[str] = None,
        agent_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[CallbackManager]:
        """
        Get callback manager with tracing configured.
        
        Args:
            session_id: Optional session ID for correlation
            agent_name: Name of the agent making the call
            metadata: Additional metadata to attach to traces
            
        Returns:
            CallbackManager if tracing enabled, None otherwise
        """
        if not self.enabled or not self.tracer:
            return None
        
        # Build run metadata
        run_metadata = {
            "session_id": session_id or "unknown",
            "agent_name": agent_name or "unknown",
            "timestamp": datetime.utcnow().isoformat(),
            **(metadata or {})
        }
        
        # Create callback manager with tracer
        return CallbackManager(handlers=[self.tracer])
    
    def get_run_config(
        self,
        session_id: Optional[str] = None,
        agent_name: Optional[str] = None,
        tags: Optional[list] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Get configuration dict for LLM invoke calls.
        
        Args:
            session_id: Session ID for correlation
            agent_name: Name of the calling agent
            tags: List of tags for filtering traces
            metadata: Additional metadata
            
        Returns:
            Config dict to pass to LLM.invoke()
        """
        if not self.enabled:
            return {}
        
        config = {
            "tags": tags or [],
            "metadata": {
                "session_id": session_id or "unknown",
                "agent_name": agent_name or "unknown",
                "timestamp": datetime.utcnow().isoformat(),
                **(metadata or {})
            }
        }
        
        if agent_name:
            config["tags"].append(f"agent:{agent_name}")
        
        if self.tracer:
            config["callbacks"] = [self.tracer]
        
        return config
    
    def trace_agent(self, agent_name: str) -> Callable:
        """
        Decorator to add tracing context to agent nodes.
        
        Args:
            agent_name: Name of the agent being traced
            
        Returns:
            Decorator function
        """
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(state: Dict[str, Any]) -> Dict[str, Any]:
                # Add tracing context to state
                if self.enabled:
                    state["_tracing"] = {
                        "agent_name": agent_name,
                        "start_time": datetime.utcnow().isoformat()
                    }
                
                try:
                    result = func(state)
                    
                    # Log completion
                    if self.enabled:
                        logger.debug(f"Traced agent '{agent_name}' completed successfully")
                    
                    return result
                    
                except Exception as e:
                    if self.enabled:
                        logger.error(f"Traced agent '{agent_name}' failed: {e}")
                    raise
                    
            return wrapper
        return decorator


# Global tracing service instance
_tracing_service: Optional[TracingService] = None


def get_tracing_service() -> TracingService:
    """Get or create the global tracing service instance."""
    global _tracing_service
    if _tracing_service is None:
        _tracing_service = TracingService()
    return _tracing_service


def get_llm_config(
    session_id: Optional[str] = None,
    agent_name: Optional[str] = None,
    **metadata
) -> Dict[str, Any]:
    """
    Convenience function to get LLM config with tracing.
    
    Args:
        session_id: Session ID for correlation
        agent_name: Name of the calling agent
        **metadata: Additional metadata
        
    Returns:
        Config dict for LLM invoke calls
    """
    service = get_tracing_service()
    return service.get_run_config(
        session_id=session_id,
        agent_name=agent_name,
        metadata=metadata
    )
