"""
Agent System Tests.
"""

import pytest
from unittest.mock import MagicMock, patch

import os
os.environ["GOOGLE_API_KEY"] = "test-api-key"


class TestAgentState:
    """Tests for agent state management."""
    
    def test_create_initial_state(self):
        """Test initial state creation."""
        from src.agent.state import create_initial_state
        
        state = create_initial_state("Test message")
        
        assert "messages" in state
        assert len(state["messages"]) == 1
        assert state["task"] == "Test message"
        assert state["next_step"] == "supervisor"
        assert state["iteration_count"] == 0
        assert state["max_iterations"] == 25
        
    def test_initial_state_has_memory(self):
        """Initial state should have memory initialized."""
        from src.agent.state import create_initial_state
        
        state = create_initial_state("Test")
        
        assert "memory" in state
        assert len(state["memory"]) == 1
        assert state["memory"][0]["role"] == "user"
        
    def test_add_tool_result(self):
        """Test adding tool results."""
        from src.agent.state import create_initial_state, add_tool_result
        
        state = create_initial_state("Test")
        results = add_tool_result(
            state,
            tool_name="write_file",
            tool_input={"path": "/test.py"},
            output="Success",
            success=True,
            execution_time_ms=100.0
        )
        
        assert len(results) == 1
        assert results[0]["tool_name"] == "write_file"
        assert results[0]["success"] is True
        
    def test_should_continue_normal(self):
        """should_continue should return True for normal state."""
        from src.agent.state import create_initial_state, should_continue
        
        state = create_initial_state("Test")
        
        assert should_continue(state) is True
        
    def test_should_continue_max_iterations(self):
        """should_continue should return False at max iterations."""
        from src.agent.state import create_initial_state, should_continue
        
        state = create_initial_state("Test")
        state["iteration_count"] = 25
        
        assert should_continue(state) is False
        
    def test_should_continue_finish(self):
        """should_continue should return False when FINISH."""
        from src.agent.state import create_initial_state, should_continue
        
        state = create_initial_state("Test")
        state["next_step"] = "FINISH"
        
        assert should_continue(state) is False


class TestResponseParsing:
    """Tests for LLM response parsing."""
    
    def test_parse_json_action_simple(self):
        """Test parsing simple JSON action."""
        from src.agent.nodes import parse_json_action
        
        result = parse_json_action('{"action": "finish"}')
        
        assert result is not None
        assert result["action"] == "finish"
        
    def test_parse_json_action_markdown(self):
        """Test parsing JSON from markdown block."""
        from src.agent.nodes import parse_json_action
        
        content = '''```json
{"action": "write_file", "path": "/test.py"}
```'''
        
        result = parse_json_action(content)
        
        assert result is not None
        assert result["action"] == "write_file"
        
    def test_parse_json_action_embedded(self):
        """Test parsing JSON embedded in text."""
        from src.agent.nodes import parse_json_action
        
        content = 'I will write a file: {"action": "write_file"}'
        
        result = parse_json_action(content)
        
        assert result is not None
        assert result["action"] == "write_file"
        
    def test_parse_json_action_invalid(self):
        """Test parsing invalid JSON returns None."""
        from src.agent.nodes import parse_json_action
        
        result = parse_json_action("This is not JSON")
        
        assert result is None


class TestToolExecutor:
    """Tests for tool execution."""
    
    def test_available_tools(self):
        """Tool executor should have expected tools."""
        from src.agent.nodes import ToolExecutor
        
        expected = ["write_file", "read_file", "list_dir", "run_command"]
        
        for tool in expected:
            assert tool in ToolExecutor.AVAILABLE_TOOLS
