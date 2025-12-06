"""
Production Agent Nodes for AI Code Reviewer.

Implements specialized agents with ReAct pattern, tool execution,
comprehensive error handling, and structured logging.
"""

import json
import time
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, BaseMessage

from src.agent.state import (
    AgentState, 
    add_tool_result, 
    add_memory,
    ToolResult
)
from src.agent.prompts import (
    SUPERVISOR_PROMPT,
    PLANNER_PROMPT,
    RESEARCHER_PROMPT,
    CODER_PROMPT,
    REVIEWER_PROMPT
)
from src.tools.file_ops import read_file, write_file, list_dir
from src.tools.terminal import run_command_sync
from src.config import get_settings
from src.logging_config import get_logger

settings = get_settings()
logger = get_logger(__name__)

# =============================================================================
# LLM INITIALIZATION
# =============================================================================

def create_llm(temperature: float = None) -> ChatGoogleGenerativeAI:
    """
    Create a configured LLM instance.
    
    Args:
        temperature: Override default temperature
        
    Returns:
        Configured ChatGoogleGenerativeAI instance
    """
    return ChatGoogleGenerativeAI(
        model=settings.gemini_model,
        temperature=temperature or settings.gemini_temperature,
        google_api_key=settings.google_api_key,
        max_retries=3,
        timeout=60
    )


# Global LLM instance
try:
    llm = create_llm()
    logger.info(f"Initialized LLM with model: {settings.gemini_model}")
except Exception as e:
    logger.error(f"Failed to initialize LLM: {e}", exc_info=True)
    raise


# =============================================================================
# RETRY LOGIC
# =============================================================================

def retry_with_backoff(
    func: Callable,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0
) -> Any:
    """
    Execute function with exponential backoff retry.
    
    Args:
        func: Function to execute
        max_retries: Maximum retry attempts
        base_delay: Initial delay between retries
        max_delay: Maximum delay cap
        
    Returns:
        Function result
        
    Raises:
        Last exception if all retries fail
    """
    last_exception = None
    
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            last_exception = e
            if attempt == max_retries - 1:
                logger.error(f"All {max_retries} attempts failed: {e}")
                raise
            
            delay = min(base_delay * (2 ** attempt), max_delay)
            logger.warning(
                f"Attempt {attempt + 1}/{max_retries} failed: {e}. "
                f"Retrying in {delay:.1f}s"
            )
            time.sleep(delay)
    
    raise last_exception


# =============================================================================
# TOOL EXECUTION ENGINE
# =============================================================================

class ToolExecutor:
    """Executes tools with logging, timing, and error handling."""
    
    AVAILABLE_TOOLS = {
        "write_file": lambda args: write_file(args["path"], args["content"]),
        "read_file": lambda args: read_file(args["path"]),
        "list_dir": lambda args: list_dir(args["path"]),
        "run_command": lambda args: run_command_sync(
            args["command"], 
            args.get("cwd", ".")
        ),
    }
    
    @classmethod
    def execute(
        cls,
        tool_name: str,
        tool_input: Dict[str, Any],
        state: AgentState
    ) -> tuple[str, bool, List[ToolResult]]:
        """
        Execute a tool and return results.
        
        Args:
            tool_name: Name of tool to execute
            tool_input: Tool input parameters
            state: Current agent state
            
        Returns:
            Tuple of (output, success, updated_tool_results)
        """
        start_time = time.time()
        logger.info(f"Executing tool: {tool_name} with input: {tool_input}")
        
        try:
            if tool_name not in cls.AVAILABLE_TOOLS:
                output = f"Unknown tool: {tool_name}"
                success = False
            else:
                output = cls.AVAILABLE_TOOLS[tool_name](tool_input)
                success = not output.startswith("Error:")
                
            execution_time_ms = (time.time() - start_time) * 1000
            
            logger.info(
                f"Tool {tool_name} completed in {execution_time_ms:.2f}ms. "
                f"Success: {success}"
            )
            
            # Add to tool results
            updated_results = add_tool_result(
                state,
                tool_name,
                tool_input,
                output[:1000],  # Truncate for storage
                success,
                execution_time_ms
            )
            
            return output, success, updated_results
            
        except Exception as e:
            execution_time_ms = (time.time() - start_time) * 1000
            error_msg = f"Tool execution error: {str(e)}"
            logger.error(error_msg, exc_info=True)
            
            updated_results = add_tool_result(
                state,
                tool_name,
                tool_input,
                error_msg,
                False,
                execution_time_ms
            )
            
            return error_msg, False, updated_results


# =============================================================================
# RESPONSE PARSER
# =============================================================================

def parse_json_action(content: str) -> Optional[Dict[str, Any]]:
    """
    Parse JSON action from LLM response.
    
    Handles various formats including markdown code blocks.
    
    Args:
        content: LLM response content
        
    Returns:
        Parsed JSON dict or None if not valid JSON
    """
    # Try direct JSON parse first
    try:
        if content.strip().startswith("{"):
            return json.loads(content.strip())
    except json.JSONDecodeError:
        pass
    
    # Try extracting from markdown code blocks
    json_str = content
    
    if "```json" in content:
        try:
            json_str = content.split("```json")[1].split("```")[0].strip()
            return json.loads(json_str)
        except (IndexError, json.JSONDecodeError):
            pass
    
    if "```" in content:
        try:
            json_str = content.split("```")[1].split("```")[0].strip()
            if json_str.startswith("{"):
                return json.loads(json_str)
        except (IndexError, json.JSONDecodeError):
            pass
    
    # Try finding JSON object in text
    try:
        start = content.find("{")
        end = content.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(content[start:end])
    except json.JSONDecodeError:
        pass
    
    return None


# =============================================================================
# SUPERVISOR NODE
# =============================================================================

def supervisor_node(state: AgentState) -> Dict[str, Any]:
    """
    Supervisor node - orchestrates agent routing.
    
    Analyzes conversation state and routes to appropriate specialist agent.
    
    Args:
        state: Current agent state
        
    Returns:
        State update with next_step decision
    """
    logger.info("=" * 50)
    logger.info("SUPERVISOR NODE - Analyzing and routing")
    logger.info("=" * 50)
    
    messages = state["messages"]
    iteration = state.get("iteration_count", 0)
    
    # Check iteration limit
    if iteration >= state.get("max_iterations", 25):
        logger.warning(f"Max iterations ({iteration}) reached. Forcing FINISH.")
        return {
            "next_step": "FINISH",
            "iteration_count": iteration + 1
        }
    
    try:
        # Build context message
        context_parts = []
        
        if state.get("plan"):
            context_parts.append(f"Current Plan:\n{state['plan']}")
        
        if state.get("tool_results"):
            recent_tools = state["tool_results"][-3:]
            tools_summary = "\n".join([
                f"- {t['tool_name']}: {'✓' if t['success'] else '✗'}"
                for t in recent_tools
            ])
            context_parts.append(f"Recent Tool Results:\n{tools_summary}")
        
        context = "\n\n".join(context_parts) if context_parts else ""
        
        # Invoke LLM
        system_msg = SystemMessage(content=SUPERVISOR_PROMPT)
        context_msg = HumanMessage(content=f"Context:\n{context}") if context else None
        
        invoke_messages = [system_msg]
        if context_msg:
            invoke_messages.append(context_msg)
        invoke_messages.extend(messages)
        
        response = retry_with_backoff(
            lambda: llm.invoke(invoke_messages)
        )
        
        decision = response.content.strip().lower()
        logger.info(f"Supervisor raw decision: {decision}")
        
        # Parse decision
        agents = ["planner", "researcher", "coder", "reviewer"]
        next_step = "coder"  # Default
        
        for agent in agents:
            if agent in decision:
                next_step = agent
                break
        
        if "finish" in decision:
            next_step = "FINISH"
        
        logger.info(f"Supervisor routing to: {next_step}")
        
        return {
            "next_step": next_step,
            "current_agent": "supervisor",
            "iteration_count": iteration + 1
        }
        
    except Exception as e:
        logger.error(f"Supervisor error: {e}", exc_info=True)
        return {
            "next_step": "FINISH",
            "iteration_count": iteration + 1,
            "error_context": {
                "agent": "supervisor",
                "error": str(e),
                "fatal": False
            }
        }


# =============================================================================
# PLANNER NODE
# =============================================================================

def planner_node(state: AgentState) -> Dict[str, Any]:
    """
    Planner node - strategic task decomposition and planning.
    
    Creates implementation plans for complex tasks.
    
    Args:
        state: Current agent state
        
    Returns:
        State update with plan and messages
    """
    logger.info("=" * 50)
    logger.info("PLANNER NODE - Strategic Planning")
    logger.info("=" * 50)
    
    messages = state["messages"]
    
    try:
        # Invoke LLM with planner prompt
        response = retry_with_backoff(
            lambda: llm.invoke([SystemMessage(content=PLANNER_PROMPT)] + messages)
        )
        
        plan_content = response.content
        logger.info(f"Planner created plan: {plan_content[:200]}...")
        
        # Add to memory
        updated_memory = add_memory(
            state,
            "assistant",
            plan_content,
            "planner"
        )
        
        return {
            "messages": [response],
            "plan": plan_content,
            "memory": updated_memory,
            "current_agent": "planner",
            "next_step": "supervisor"
        }
        
    except Exception as e:
        logger.error(f"Planner error: {e}", exc_info=True)
        error_msg = AIMessage(content=f"Planning error: {str(e)}")
        return {
            "messages": [error_msg],
            "current_agent": "planner",
            "next_step": "supervisor"
        }


# =============================================================================
# RESEARCHER NODE
# =============================================================================

def researcher_node(state: AgentState) -> Dict[str, Any]:
    """
    Researcher node - semantic search and codebase understanding.
    
    Gathers context and analyzes code structure.
    
    Args:
        state: Current agent state
        
    Returns:
        State update with research findings
    """
    logger.info("=" * 50)
    logger.info("RESEARCHER NODE - Gathering Context")
    logger.info("=" * 50)
    
    messages = state["messages"]
    
    try:
        # Add repo map context if available
        context_messages = list(messages)
        if state.get("repo_map"):
            context_messages.insert(0, HumanMessage(
                content=f"Repository Structure:\n{state['repo_map']}"
            ))
        
        # Invoke LLM
        response = retry_with_backoff(
            lambda: llm.invoke([SystemMessage(content=RESEARCHER_PROMPT)] + context_messages)
        )
        
        content = response.content
        logger.info(f"Researcher response: {content[:200]}...")
        
        # Parse action if present
        action_data = parse_json_action(content)
        tool_results = state.get("tool_results", [])
        output_messages = [response]
        
        if action_data:
            action = action_data.get("action", "")
            
            if action == "analyze_file":
                path = action_data.get("path", "")
                result = read_file(path)
                tool_output = HumanMessage(content=f"File Analysis Result:\n{result}")
                output_messages.append(tool_output)
                
            elif action == "search_code":
                # Placeholder for semantic search
                query = action_data.get("query", "")
                result = f"[Semantic search for: {query}]\n(Vector store integration pending)"
                tool_output = HumanMessage(content=f"Search Result:\n{result}")
                output_messages.append(tool_output)
                
            elif action == "finish":
                logger.info("Researcher finished with findings")
        
        # Update memory
        updated_memory = add_memory(
            state,
            "assistant",
            content[:500],
            "researcher"
        )
        
        return {
            "messages": output_messages,
            "memory": updated_memory,
            "tool_results": tool_results,
            "current_agent": "researcher",
            "next_step": "supervisor"
        }
        
    except Exception as e:
        logger.error(f"Researcher error: {e}", exc_info=True)
        error_msg = AIMessage(content=f"Research error: {str(e)}")
        return {
            "messages": [error_msg],
            "current_agent": "researcher",
            "next_step": "supervisor"
        }


# =============================================================================
# CODER NODE
# =============================================================================

def coder_node(state: AgentState) -> Dict[str, Any]:
    """
    Coder node - code implementation with ReAct pattern.
    
    Executes file operations, commands, and code modifications.
    
    Args:
        state: Current agent state
        
    Returns:
        State update with implementation results
    """
    logger.info("=" * 50)
    logger.info("CODER NODE - Implementation")
    logger.info("=" * 50)
    
    messages = state["messages"]
    tool_results = state.get("tool_results", [])
    
    try:
        # Add context
        context_messages = list(messages)
        
        if state.get("plan"):
            context_messages.insert(0, HumanMessage(
                content=f"Implementation Plan:\n{state['plan']}"
            ))
        
        # Invoke LLM
        response = retry_with_backoff(
            lambda: llm.invoke([SystemMessage(content=CODER_PROMPT)] + context_messages)
        )
        
        content = response.content
        logger.info(f"Coder response: {content[:300]}...")
        
        output_messages = [response]
        
        # Parse and execute action
        action_data = parse_json_action(content)
        
        if action_data:
            action = action_data.get("action", "")
            logger.info(f"Coder action: {action}")
            
            if action == "finish":
                logger.info("Coder signaled completion")
                updated_memory = add_memory(state, "assistant", content[:500], "coder")
                return {
                    "messages": output_messages,
                    "memory": updated_memory,
                    "tool_results": tool_results,
                    "current_agent": "coder",
                    "next_step": "supervisor"
                }
            
            # Execute tool
            if action in ToolExecutor.AVAILABLE_TOOLS:
                tool_output, success, tool_results = ToolExecutor.execute(
                    action,
                    action_data,
                    state
                )
                
                # Add tool result to messages
                result_msg = HumanMessage(
                    content=f"Tool Result ({action}):\n{tool_output}"
                )
                output_messages.append(result_msg)
                
        # Update memory
        updated_memory = add_memory(state, "assistant", content[:500], "coder")
        
        return {
            "messages": output_messages,
            "memory": updated_memory,
            "tool_results": tool_results,
            "current_agent": "coder",
            "next_step": "supervisor"
        }
        
    except Exception as e:
        logger.error(f"Coder error: {e}", exc_info=True)
        error_msg = AIMessage(content=f"Implementation error: {str(e)}")
        return {
            "messages": [error_msg],
            "current_agent": "coder",
            "next_step": "supervisor",
            "error_context": {
                "agent": "coder",
                "error": str(e),
                "fatal": False
            }
        }


# =============================================================================
# REVIEWER NODE
# =============================================================================

def reviewer_node(state: AgentState) -> Dict[str, Any]:
    """
    Reviewer node - code review and security analysis.
    
    Analyzes code for quality, security, and best practices.
    
    Args:
        state: Current agent state
        
    Returns:
        State update with review findings
    """
    logger.info("=" * 50)
    logger.info("REVIEWER NODE - Code Review")
    logger.info("=" * 50)
    
    messages = state["messages"]
    
    try:
        # Build context with recent tool results
        context_messages = list(messages)
        
        if state.get("tool_results"):
            # Get files that were modified
            modified_files = [
                r["input"].get("path", "")
                for r in state["tool_results"]
                if r["tool_name"] == "write_file" and r["success"]
            ]
            
            if modified_files:
                context_messages.insert(0, HumanMessage(
                    content=f"Files modified in this session:\n" + 
                            "\n".join(f"- {f}" for f in modified_files)
                ))
        
        # Invoke LLM
        response = retry_with_backoff(
            lambda: llm.invoke([SystemMessage(content=REVIEWER_PROMPT)] + context_messages)
        )
        
        content = response.content
        logger.info(f"Reviewer response: {content[:300]}...")
        
        output_messages = [response]
        reflection = ""
        
        # Parse action
        action_data = parse_json_action(content)
        
        if action_data:
            action = action_data.get("action", "")
            
            if action == "finish":
                verdict = action_data.get("verdict", "UNKNOWN")
                summary = action_data.get("summary", "")
                reflection = f"Review Verdict: {verdict}\n{summary}"
                logger.info(f"Review verdict: {verdict}")
            
            elif action == "review_file":
                path = action_data.get("path", "")
                file_content = read_file(path)
                result_msg = HumanMessage(
                    content=f"File for review ({path}):\n{file_content[:2000]}"
                )
                output_messages.append(result_msg)
        
        # Update memory
        updated_memory = add_memory(state, "assistant", content[:500], "reviewer")
        
        return {
            "messages": output_messages,
            "memory": updated_memory,
            "reflection": reflection or state.get("reflection", ""),
            "current_agent": "reviewer",
            "next_step": "supervisor"
        }
        
    except Exception as e:
        logger.error(f"Reviewer error: {e}", exc_info=True)
        error_msg = AIMessage(content=f"Review error: {str(e)}")
        return {
            "messages": [error_msg],
            "current_agent": "reviewer",
            "next_step": "supervisor"
        }


# =============================================================================
# NODE REGISTRY
# =============================================================================

AGENT_NODES = {
    "supervisor": supervisor_node,
    "planner": planner_node,
    "researcher": researcher_node,
    "coder": coder_node,
    "reviewer": reviewer_node
}

def get_node(name: str) -> Callable:
    """Get node function by name."""
    return AGENT_NODES.get(name)
