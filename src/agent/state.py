"""
Enhanced Agent State for production multi-agent system.

Provides comprehensive state management with memory, tool results,
iteration tracking, and reflection capabilities.
"""

from typing import TypedDict, Annotated, List, Optional, Dict, Any
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage
from datetime import datetime


class ToolResult(TypedDict):
    """Result from a tool execution."""
    tool_name: str
    input: Dict[str, Any]
    output: str
    success: bool
    execution_time_ms: float
    timestamp: str


class AgentContext(TypedDict):
    """Context for the current agent."""
    agent_name: str
    started_at: str
    iteration: int


class MemoryItem(TypedDict):
    """A memory item for conversation history."""
    role: str
    content: str
    timestamp: str
    agent: Optional[str]


class AgentState(TypedDict):
    """
    Enhanced agent state with full production capabilities.
    
    Attributes:
        messages: Conversation messages with automatic aggregation
        next_step: Next node to execute in the graph
        task: Current user task/request
        repo_map: Repository structure map from indexer
        current_agent: Currently active agent name
        iteration_count: Number of iterations (for loop prevention)
        max_iterations: Maximum allowed iterations
        tool_results: History of tool execution results
        memory: Long-term conversation memory
        reflection: Agent's self-reflection/reasoning
        error_context: Error information if any occurred
        metadata: Additional metadata for tracking
    """
    # Core state
    messages: Annotated[List[BaseMessage], add_messages]
    next_step: str
    task: str
    
    # Repository context
    repo_map: str
    file_context: Optional[Dict[str, str]]  # filename -> content cache
    
    # Agent tracking
    current_agent: str
    iteration_count: int
    max_iterations: int
    
    # Tool execution history
    tool_results: List[ToolResult]
    
    # Memory and reasoning
    memory: List[MemoryItem]
    reflection: str
    plan: Optional[str]
    
    # Error handling
    error_context: Optional[Dict[str, Any]]
    
    # Metadata
    metadata: Dict[str, Any]


def create_initial_state(user_message: str, task: str = None) -> AgentState:
    """
    Create a properly initialized agent state.
    
    Args:
        user_message: The user's input message
        task: Optional task description (defaults to user_message)
        
    Returns:
        Initialized AgentState with all fields set
    """
    from langchain_core.messages import HumanMessage
    
    return {
        "messages": [HumanMessage(content=user_message)],
        "next_step": "supervisor",
        "task": task or user_message,
        "repo_map": "",
        "file_context": {},
        "current_agent": "supervisor",
        "iteration_count": 0,
        "max_iterations": 25,  # Prevent infinite loops
        "tool_results": [],
        "memory": [{
            "role": "user",
            "content": user_message,
            "timestamp": datetime.now().isoformat(),
            "agent": None
        }],
        "reflection": "",
        "plan": None,
        "error_context": None,
        "metadata": {
            "created_at": datetime.now().isoformat(),
            "session_id": None,
            "version": "2.0.0"
        }
    }


def add_tool_result(
    state: AgentState,
    tool_name: str,
    tool_input: Dict[str, Any],
    output: str,
    success: bool,
    execution_time_ms: float
) -> List[ToolResult]:
    """
    Add a tool result to the state.
    
    Args:
        state: Current agent state
        tool_name: Name of the executed tool
        tool_input: Input parameters to the tool
        output: Tool output
        success: Whether execution was successful
        execution_time_ms: Execution time in milliseconds
        
    Returns:
        Updated tool_results list
    """
    result: ToolResult = {
        "tool_name": tool_name,
        "input": tool_input,
        "output": output,
        "success": success,
        "execution_time_ms": execution_time_ms,
        "timestamp": datetime.now().isoformat()
    }
    
    return state.get("tool_results", []) + [result]


def add_memory(
    state: AgentState,
    role: str,
    content: str,
    agent: Optional[str] = None
) -> List[MemoryItem]:
    """
    Add a memory item to the state.
    
    Args:
        state: Current agent state
        role: Role (user, assistant, system, tool)
        content: Content of the memory
        agent: Optional agent name
        
    Returns:
        Updated memory list
    """
    item: MemoryItem = {
        "role": role,
        "content": content,
        "timestamp": datetime.now().isoformat(),
        "agent": agent
    }
    
    return state.get("memory", []) + [item]


def should_continue(state: AgentState) -> bool:
    """
    Check if the agent should continue processing.
    
    Args:
        state: Current agent state
        
    Returns:
        True if should continue, False if should stop
    """
    # Check iteration limit
    if state.get("iteration_count", 0) >= state.get("max_iterations", 25):
        return False
    
    # Check for FINISH state
    if state.get("next_step") == "FINISH":
        return False
    
    # Check for error state
    if state.get("error_context") and state["error_context"].get("fatal", False):
        return False
    
    return True
