"""
Evaluation Service Tests.

Tests for AI output quality scoring and metrics aggregation.
"""

import pytest
from datetime import datetime

import os
os.environ["GOOGLE_API_KEY"] = "test-api-key"


class TestResponseEvaluator:
    """Tests for ResponseEvaluator scoring."""
    
    def test_evaluator_creation(self):
        """Test evaluator can be created."""
        from src.services.evaluation import ResponseEvaluator
        
        evaluator = ResponseEvaluator()
        assert evaluator is not None
    
    def test_evaluate_basic_response(self):
        """Test evaluation of a basic response."""
        from src.services.evaluation import ResponseEvaluator
        
        evaluator = ResponseEvaluator()
        result = evaluator.evaluate(
            user_input="How do I write a Python function?",
            agent_response="You can write a Python function using the def keyword. Here's an example:\n\n```python\ndef hello():\n    print('Hello!')\n```",
            agent_name="coder",
            session_id="test-session-1",
            response_time_ms=150.0
        )
        
        assert result.session_id == "test-session-1"
        assert result.agent_name == "coder"
        assert 0.0 <= result.overall_score <= 1.0
        assert 0.0 <= result.relevance_score <= 1.0
        assert 0.0 <= result.completeness_score <= 1.0
        assert 0.0 <= result.code_quality_score <= 1.0
        assert 0.0 <= result.helpfulness_score <= 1.0
    
    def test_evaluate_code_response(self):
        """Test evaluation favors code responses for code questions."""
        from src.services.evaluation import ResponseEvaluator
        
        evaluator = ResponseEvaluator()
        
        # Response with code
        result_with_code = evaluator.evaluate(
            user_input="Write a function to add two numbers",
            agent_response="Here's a function to add two numbers:\n\n```python\ndef add(a: int, b: int) -> int:\n    \"\"\"Add two numbers.\"\"\"\n    return a + b\n```",
            agent_name="coder",
            session_id="test-1",
            response_time_ms=100.0
        )
        
        # Response without code
        result_without_code = evaluator.evaluate(
            user_input="Write a function to add two numbers",
            agent_response="To add two numbers, you need to use the plus operator.",
            agent_name="coder",
            session_id="test-2",
            response_time_ms=100.0
        )
        
        # Code response should score higher on code quality
        assert result_with_code.code_quality_score > result_without_code.code_quality_score
        assert result_with_code.has_code_output is True
        assert result_without_code.has_code_output is False
    
    def test_evaluate_empty_response(self):
        """Test evaluation handles empty responses."""
        from src.services.evaluation import ResponseEvaluator
        
        evaluator = ResponseEvaluator()
        result = evaluator.evaluate(
            user_input="Hello",
            agent_response="",
            agent_name="test",
            session_id="test-empty",
            response_time_ms=50.0
        )
        
        # Empty response should have very low scores
        assert result.overall_score < 0.15
        assert result.output_length == 0
    
    def test_evaluation_result_to_dict(self):
        """Test EvaluationResult serialization."""
        from src.services.evaluation import EvaluationResult
        
        result = EvaluationResult(
            session_id="test",
            agent_name="coder",
            timestamp=datetime.utcnow().isoformat(),
            relevance_score=0.8,
            completeness_score=0.7,
            code_quality_score=0.9,
            helpfulness_score=0.75,
            overall_score=0.79,
            response_time_ms=100.0
        )
        
        data = result.to_dict()
        
        assert data["session_id"] == "test"
        assert data["overall_score"] == 0.79
        assert isinstance(data, dict)
    
    def test_evaluation_result_to_json(self):
        """Test EvaluationResult JSON serialization."""
        from src.services.evaluation import EvaluationResult
        import json
        
        result = EvaluationResult(
            session_id="test",
            agent_name="coder",
            timestamp=datetime.utcnow().isoformat(),
            relevance_score=0.8,
            completeness_score=0.7,
            code_quality_score=0.9,
            helpfulness_score=0.75,
            overall_score=0.79,
            response_time_ms=100.0
        )
        
        json_str = result.to_json()
        parsed = json.loads(json_str)
        
        assert parsed["agent_name"] == "coder"


class TestMetricsAggregator:
    """Tests for MetricsAggregator."""
    
    def test_aggregator_creation(self):
        """Test aggregator can be created."""
        from src.services.evaluation import MetricsAggregator
        
        aggregator = MetricsAggregator()
        assert aggregator is not None
        assert aggregator.evaluations == []
    
    def test_add_evaluation(self):
        """Test adding evaluations."""
        from src.services.evaluation import MetricsAggregator, EvaluationResult
        from datetime import datetime
        
        aggregator = MetricsAggregator()
        
        result = EvaluationResult(
            session_id="test",
            agent_name="coder",
            timestamp=datetime.utcnow().isoformat(),
            relevance_score=0.8,
            completeness_score=0.7,
            code_quality_score=0.9,
            helpfulness_score=0.75,
            overall_score=0.79,
            response_time_ms=100.0
        )
        
        aggregator.add_evaluation(result)
        
        assert len(aggregator.evaluations) == 1
    
    def test_get_summary(self):
        """Test summary statistics."""
        from src.services.evaluation import MetricsAggregator, EvaluationResult
        from datetime import datetime
        
        aggregator = MetricsAggregator()
        
        # Add multiple evaluations
        for i in range(5):
            result = EvaluationResult(
                session_id=f"test-{i}",
                agent_name="coder",
                timestamp=datetime.utcnow().isoformat(),
                relevance_score=0.8,
                completeness_score=0.7,
                code_quality_score=0.9,
                helpfulness_score=0.75,
                overall_score=0.79,
                response_time_ms=100.0 + i * 10
            )
            aggregator.add_evaluation(result)
        
        summary = aggregator.get_summary()
        
        assert summary["count"] == 5
        assert "avg_overall_score" in summary
        assert "avg_response_time_ms" in summary
    
    def test_get_summary_empty(self):
        """Test summary with no evaluations."""
        from src.services.evaluation import MetricsAggregator
        
        aggregator = MetricsAggregator()
        summary = aggregator.get_summary()
        
        assert summary["count"] == 0
    
    def test_get_agent_breakdown(self):
        """Test breakdown by agent."""
        from src.services.evaluation import MetricsAggregator, EvaluationResult
        from datetime import datetime
        
        aggregator = MetricsAggregator()
        
        # Add evaluations for different agents
        for agent in ["coder", "reviewer", "planner"]:
            result = EvaluationResult(
                session_id=f"test-{agent}",
                agent_name=agent,
                timestamp=datetime.utcnow().isoformat(),
                relevance_score=0.8,
                completeness_score=0.7,
                code_quality_score=0.9,
                helpfulness_score=0.75,
                overall_score=0.79,
                response_time_ms=100.0
            )
            aggregator.add_evaluation(result)
        
        breakdown = aggregator.get_agent_breakdown()
        
        assert "coder" in breakdown
        assert "reviewer" in breakdown
        assert "planner" in breakdown


class TestConvenienceFunctions:
    """Tests for module-level convenience functions."""
    
    def test_get_evaluator(self):
        """Test global evaluator getter."""
        from src.services.evaluation import get_evaluator
        
        evaluator1 = get_evaluator()
        evaluator2 = get_evaluator()
        
        # Should return same instance
        assert evaluator1 is evaluator2
    
    def test_get_aggregator(self):
        """Test global aggregator getter."""
        from src.services.evaluation import get_aggregator
        
        aggregator1 = get_aggregator()
        aggregator2 = get_aggregator()
        
        # Should return same instance
        assert aggregator1 is aggregator2
    
    def test_evaluate_response_function(self):
        """Test convenience evaluate_response function."""
        from src.services.evaluation import evaluate_response
        
        result = evaluate_response(
            user_input="Test question",
            agent_response="Test answer with some helpful content.",
            agent_name="test-agent",
            session_id="test-session",
            response_time_ms=50.0
        )
        
        assert result is not None
        assert result.agent_name == "test-agent"
