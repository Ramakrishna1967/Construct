"""
Pytest Configuration and Fixtures.
"""

import pytest
import asyncio
from typing import Generator, AsyncGenerator
from unittest.mock import MagicMock, AsyncMock, patch

# Set test environment variable before importing app
import os
os.environ["GOOGLE_API_KEY"] = "test-api-key-for-testing"
os.environ["REDIS_URL"] = "redis://localhost:6379"


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_llm():
    """Mock LLM for testing without API calls."""
    with patch("src.agent.nodes.llm") as mock:
        mock.invoke = MagicMock(return_value=MagicMock(
            content='{"action": "finish", "summary": "Test completed"}'
        ))
        yield mock


@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    with patch("src.services.redis_store.redis") as mock:
        mock_client = AsyncMock()
        mock_client.ping = AsyncMock(return_value=True)
        mock_client.get = AsyncMock(return_value=None)
        mock_client.set = AsyncMock(return_value=True)
        yield mock_client


@pytest.fixture
def mock_docker():
    """Mock Docker client."""
    with patch("src.services.sandbox.docker") as mock:
        mock_client = MagicMock()
        mock.from_env.return_value = mock_client
        yield mock_client


@pytest.fixture
def sample_code():
    """Sample Python code for testing."""
    return '''
def hello_world():
    """Say hello."""
    print("Hello, World!")
    return True

class Calculator:
    def add(self, a, b):
        return a + b
'''


@pytest.fixture
def sample_state():
    """Sample agent state for testing."""
    from src.agent.state import create_initial_state
    return create_initial_state("Test message")
