"""
Production LangGraph Multi-Agent Workflow.

Advanced agent orchestration with conditional routing,
iteration limits, and state persistence.
"""

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from src.agent.state import AgentState, create_initial_state, should_continue
from src.agent.nodes import (
    supervisor_node,
    planner_node,
    researcher_node,
    coder_node,
    reviewer_node
)
from src.logging_config import get_logger

logger = get_logger(__name__)


# =============================================================================
# ROUTING FUNCTIONS
# =============================================================================

def route_supervisor(state: AgentState) -> str:
    """
    Route from supervisor to next agent.
    
    Args:
        state: Current agent state
        
    Returns:
        Next node name or END
    """
    next_step = state.get("next_step", "FINISH")
    
    # Check if we should stop
    if not should_continue(state):
        logger.info("Routing to END (should_continue=False)")
        return END
    
    if next_step == "FINISH":
        logger.info("Routing to END (FINISH)")
        return END
    
    valid_agents = ["planner", "researcher", "coder", "reviewer"]
    
    if next_step in valid_agents:
        logger.info(f"Routing to: {next_step}")
        return next_step
    
    # Default to coder if unknown
    logger.warning(f"Unknown next_step: {next_step}, defaulting to coder")
    return "coder"


# =============================================================================
# GRAPH CONSTRUCTION
# =============================================================================

def build_graph() -> StateGraph:
    """
    Build the multi-agent workflow graph.
    
    Returns:
        Compiled StateGraph ready for execution
    """
    logger.info("Building LangGraph multi-agent workflow")
    
    # Create workflow
    workflow = StateGraph(AgentState)
    
    # Add agent nodes
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("planner", planner_node)
    workflow.add_node("researcher", researcher_node)
    workflow.add_node("coder", coder_node)
    workflow.add_node("reviewer", reviewer_node)
    
    logger.debug("Added 5 agent nodes to graph")
    
    # Set entry point
    workflow.set_entry_point("supervisor")
    
    # Add conditional routing from supervisor
    workflow.add_conditional_edges(
        "supervisor",
        route_supervisor,
        {
            "planner": "planner",
            "researcher": "researcher",
            "coder": "coder",
            "reviewer": "reviewer",
            END: END
        }
    )
    
    # All agents return to supervisor
    workflow.add_edge("planner", "supervisor")
    workflow.add_edge("researcher", "supervisor")
    workflow.add_edge("coder", "supervisor")
    workflow.add_edge("reviewer", "supervisor")
    
    logger.debug("Added conditional and return edges")
    
    return workflow


def compile_graph(checkpointer=None):
    """
    Compile the workflow graph.
    
    Args:
        checkpointer: Optional checkpointer for state persistence
        
    Returns:
        Compiled graph ready for execution
    """
    workflow = build_graph()
    
    try:
        if checkpointer:
            graph = workflow.compile(checkpointer=checkpointer)
            logger.info("Graph compiled with checkpointing enabled")
        else:
            graph = workflow.compile()
            logger.info("Graph compiled without checkpointing")
        
        return graph
        
    except Exception as e:
        logger.error(f"Failed to compile graph: {e}", exc_info=True)
        raise


# =============================================================================
# GLOBAL GRAPH INSTANCE
# =============================================================================

# Create memory-based checkpointer for state persistence
try:
    memory_saver = MemorySaver()
    logger.info("Created MemorySaver for state persistence")
except Exception as e:
    logger.warning(f"Could not create MemorySaver: {e}. Continuing without persistence.")
    memory_saver = None

# Compile the graph
try:
    graph = compile_graph(checkpointer=memory_saver)
    logger.info("=" * 50)
    logger.info("LANGGRAPH WORKFLOW READY")
    logger.info("Agents: supervisor, planner, researcher, coder, reviewer")
    logger.info("=" * 50)
except Exception as e:
    logger.error(f"CRITICAL: Failed to initialize graph: {e}", exc_info=True)
    raise


# =============================================================================
# EXECUTION HELPERS
# =============================================================================

async def run_agent(
    user_message: str,
    session_id: str = None,
    stream: bool = True
):
    """
    Run the agent workflow.
    
    Args:
        user_message: User's input message
        session_id: Optional session ID for persistence
        stream: Whether to stream results
        
    Yields:
        Agent events during execution
    """
    initial_state = create_initial_state(user_message)
    
    if session_id:
        initial_state["metadata"]["session_id"] = session_id
    
    config = {}
    if session_id and memory_saver:
        config["configurable"] = {"thread_id": session_id}
    
    logger.info(f"Starting agent run for: {user_message[:100]}...")
    
    if stream:
        async for event in graph.astream(initial_state, config):
            yield event
    else:
        result = await graph.ainvoke(initial_state, config)
        yield result


# Export for backward compatibility
__all__ = [
    "graph",
    "create_initial_state",
    "run_agent",
    "build_graph",
    "compile_graph"
]
