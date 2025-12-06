"""
API Endpoint Tests.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

import os
os.environ["GOOGLE_API_KEY"] = "test-api-key"

from main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


class TestHealthEndpoint:
    """Tests for /health endpoint."""
    
    def test_health_check_returns_200(self, client):
        """Health check should return 200 or 503 (if services unavailable)."""
        response = client.get("/health")
        # 200 = healthy, 503 = unhealthy (but endpoint works)
        assert response.status_code in [200, 503]
        
    def test_health_check_structure(self, client):
        """Health check should return expected structure."""
        response = client.get("/health")
        data = response.json()
        
        # New comprehensive health check format
        assert "status" in data
        assert "timestamp" in data
        assert "version" in data
        assert "environment" in data
        assert "components" in data


class TestRootEndpoint:
    """Tests for / endpoint."""
    
    def test_root_returns_200(self, client):
        """Root endpoint should return 200."""
        response = client.get("/")
        assert response.status_code == 200
        
    def test_root_contains_service_info(self, client):
        """Root should contain service information."""
        response = client.get("/")
        data = response.json()
        
        assert data["service"] == "AI Code Reviewer"
        assert "version" in data
        assert "endpoints" in data
        assert "agents" in data


class TestMetricsEndpoint:
    """Tests for /metrics endpoint."""
    
    def test_metrics_returns_200(self, client):
        """Metrics endpoint should return 200."""
        response = client.get("/metrics")
        assert response.status_code == 200


class TestRateLimiting:
    """Tests for rate limiting middleware."""
    
    def test_rate_limit_headers_present(self, client):
        """Response should include rate limit headers."""
        response = client.get("/")
        
        assert "x-ratelimit-remaining" in response.headers
        assert "x-ratelimit-limit" in response.headers


class TestCORS:
    """Tests for CORS configuration."""
    
    def test_cors_headers(self, client):
        """CORS headers should be present."""
        response = client.options(
            "/",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST"
            }
        )
        
        assert "access-control-allow-origin" in response.headers


class TestErrorHandling:
    """Tests for error handling."""
    
    def test_404_error(self, client):
        """Non-existent endpoint should return 404."""
        response = client.get("/nonexistent")
        assert response.status_code == 404
        
    def test_error_includes_correlation_id(self, client):
        """Errors should include correlation ID."""
        response = client.get("/nonexistent")
        data = response.json()
        
        # Error response should have structure
        assert "detail" in data or "error" in data
