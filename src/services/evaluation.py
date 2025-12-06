"""
AI Output Evaluation Metrics Service.

Provides automated quality scoring for agent responses with
multiple evaluation dimensions and metrics persistence.
"""

import time
import json
import re
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum

from src.config import get_settings
from src.logging_config import get_logger

logger = get_logger(__name__)
settings = get_settings()


class EvaluationDimension(str, Enum):
    """Evaluation scoring dimensions."""
    RELEVANCE = "relevance"
    COMPLETENESS = "completeness"
    CODE_QUALITY = "code_quality"
    HELPFULNESS = "helpfulness"


@dataclass
class EvaluationResult:
    """Result of evaluating an agent response."""
    session_id: str
    agent_name: str
    timestamp: str
    
    # Scores (0.0 - 1.0)
    relevance_score: float
    completeness_score: float
    code_quality_score: float
    helpfulness_score: float
    overall_score: float
    
    # Timing metrics (milliseconds)
    response_time_ms: float
    time_to_first_token_ms: Optional[float] = None
    
    # Metadata
    input_length: int = 0
    output_length: int = 0
    has_code_output: bool = False
    tool_calls_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict())


class ResponseEvaluator:
    """
    Evaluates AI agent responses for quality metrics.
    
    Provides scoring across multiple dimensions:
    - Relevance: Does the response address the user's request?
    - Completeness: Is the response thorough and detailed?
    - Code Quality: For code outputs, syntax/style evaluation
    - Helpfulness: Overall usefulness of the response
    """
    
    def __init__(self):
        self.logger = get_logger(f"{__name__}.ResponseEvaluator")
    
    def evaluate(
        self,
        user_input: str,
        agent_response: str,
        agent_name: str,
        session_id: str,
        response_time_ms: float,
        time_to_first_token_ms: Optional[float] = None,
        tool_calls: Optional[List[Dict]] = None
    ) -> EvaluationResult:
        """
        Evaluate an agent response.
        
        Args:
            user_input: The user's input/request
            agent_response: The agent's response text
            agent_name: Name of the responding agent
            session_id: Session ID for correlation
            response_time_ms: Total response time
            time_to_first_token_ms: Time to first token (streaming)
            tool_calls: List of tool calls made
            
        Returns:
            EvaluationResult with scores and metrics
        """
        start_time = time.time()
        
        # Calculate individual scores
        relevance = self._score_relevance(user_input, agent_response)
        completeness = self._score_completeness(agent_response)
        code_quality = self._score_code_quality(agent_response)
        helpfulness = self._score_helpfulness(user_input, agent_response)
        
        # Calculate overall score (weighted average)
        overall = (
            relevance * 0.30 +
            completeness * 0.25 +
            code_quality * 0.20 +
            helpfulness * 0.25
        )
        
        # Detect if response contains code
        has_code = self._contains_code(agent_response)
        
        result = EvaluationResult(
            session_id=session_id,
            agent_name=agent_name,
            timestamp=datetime.utcnow().isoformat(),
            relevance_score=round(relevance, 3),
            completeness_score=round(completeness, 3),
            code_quality_score=round(code_quality, 3),
            helpfulness_score=round(helpfulness, 3),
            overall_score=round(overall, 3),
            response_time_ms=round(response_time_ms, 2),
            time_to_first_token_ms=round(time_to_first_token_ms, 2) if time_to_first_token_ms else None,
            input_length=len(user_input),
            output_length=len(agent_response),
            has_code_output=has_code,
            tool_calls_count=len(tool_calls) if tool_calls else 0
        )
        
        eval_time_ms = (time.time() - start_time) * 1000
        self.logger.debug(
            f"Evaluated response for {agent_name}: overall={overall:.2f} "
            f"(relevance={relevance:.2f}, completeness={completeness:.2f}, "
            f"code_quality={code_quality:.2f}, helpfulness={helpfulness:.2f}) "
            f"in {eval_time_ms:.1f}ms"
        )
        
        return result
    
    def _score_relevance(self, user_input: str, response: str) -> float:
        """
        Score how relevant the response is to the user's input.
        
        Uses keyword overlap and semantic indicators.
        """
        if not response or not user_input:
            return 0.0
        
        # Normalize texts
        input_lower = user_input.lower()
        response_lower = response.lower()
        
        # Extract keywords from input (simple approach)
        input_words = set(re.findall(r'\b[a-z]{3,}\b', input_lower))
        response_words = set(re.findall(r'\b[a-z]{3,}\b', response_lower))
        
        if not input_words:
            return 0.5  # Neutral if no keywords
        
        # Calculate overlap
        overlap = len(input_words & response_words)
        overlap_ratio = overlap / len(input_words)
        
        # Bonus for addressing specific patterns
        score = min(overlap_ratio * 1.5, 1.0)
        
        # Check for question-answer patterns
        if "?" in user_input:
            # User asked a question
            answer_indicators = ["because", "since", "therefore", "this means", "the answer"]
            if any(ind in response_lower for ind in answer_indicators):
                score = min(score + 0.1, 1.0)
        
        # Check for code request patterns
        code_requests = ["write", "create", "implement", "code", "function", "class"]
        if any(req in input_lower for req in code_requests):
            if self._contains_code(response):
                score = min(score + 0.2, 1.0)
        
        return max(0.0, min(1.0, score))
    
    def _score_completeness(self, response: str) -> float:
        """
        Score how complete and thorough the response is.
        """
        if not response:
            return 0.0
        
        score = 0.0
        
        # Length-based scoring (diminishing returns)
        length = len(response)
        if length > 100:
            score += 0.2
        if length > 300:
            score += 0.2
        if length > 600:
            score += 0.1
        if length > 1000:
            score += 0.1
        
        # Structure indicators
        if "\n" in response:
            score += 0.1  # Has line breaks (structured)
        
        # Lists (numbered or bulleted)
        if re.search(r'^\s*[-*•]\s+', response, re.MULTILINE):
            score += 0.1
        if re.search(r'^\s*\d+[.)]\s+', response, re.MULTILINE):
            score += 0.1
        
        # Code blocks
        if "```" in response:
            score += 0.1
        
        # Explanations
        explanation_words = ["because", "therefore", "this", "note", "important"]
        explanation_count = sum(1 for word in explanation_words if word in response.lower())
        score += min(explanation_count * 0.03, 0.1)
        
        return max(0.0, min(1.0, score))
    
    def _score_code_quality(self, response: str) -> float:
        """
        Score the quality of code in the response.
        
        If no code present, returns neutral score.
        """
        # Extract code blocks
        code_blocks = re.findall(r'```[\w]*\n(.*?)```', response, re.DOTALL)
        
        if not code_blocks:
            # No code blocks - check for inline code
            if '`' in response:
                return 0.6  # Has inline code references
            return 0.5  # Neutral - no code expected
        
        score = 0.5  # Base score for having code
        
        for code in code_blocks:
            # Check for common quality indicators
            
            # Has comments
            if '#' in code or '//' in code or '/*' in code:
                score += 0.1
            
            # Has docstrings
            if '"""' in code or "'''" in code:
                score += 0.1
            
            # Has type hints (Python)
            if re.search(r'def \w+\([^)]*:\s*\w+', code):
                score += 0.1
            
            # Has error handling
            if 'try:' in code or 'except' in code or 'catch' in code:
                score += 0.1
            
            # Has function/class definitions
            if 'def ' in code or 'class ' in code or 'function ' in code:
                score += 0.05
            
            # Reasonable line length (not just one long line)
            lines = code.strip().split('\n')
            if len(lines) > 1:
                avg_line_length = sum(len(l) for l in lines) / len(lines)
                if avg_line_length < 100:
                    score += 0.05
        
        return max(0.0, min(1.0, score))
    
    def _score_helpfulness(self, user_input: str, response: str) -> float:
        """
        Score overall helpfulness of the response.
        """
        if not response:
            return 0.0
        
        score = 0.3  # Base score
        
        response_lower = response.lower()
        
        # Positive indicators
        helpful_phrases = [
            "here's", "here is", "you can", "to do this",
            "the solution", "this will", "this should",
            "i recommend", "consider", "make sure"
        ]
        for phrase in helpful_phrases:
            if phrase in response_lower:
                score += 0.05
        
        # Action-oriented language
        action_words = ["run", "execute", "install", "create", "add", "modify", "change"]
        for word in action_words:
            if word in response_lower:
                score += 0.03
        
        # Has examples
        if "example" in response_lower or "for instance" in response_lower:
            score += 0.1
        
        # Addresses potential issues
        caution_words = ["note:", "warning:", "important:", "be careful", "make sure"]
        for word in caution_words:
            if word in response_lower:
                score += 0.05
        
        # Negative indicators
        unhelpful_phrases = [
            "i can't", "i cannot", "i'm not able",
            "i don't know", "i'm not sure", "i apologize"
        ]
        for phrase in unhelpful_phrases:
            if phrase in response_lower:
                score -= 0.1
        
        return max(0.0, min(1.0, score))
    
    def _contains_code(self, text: str) -> bool:
        """Check if text contains code."""
        if "```" in text:
            return True
        
        # Check for common code patterns
        code_patterns = [
            r'def\s+\w+\s*\(',
            r'class\s+\w+',
            r'function\s+\w+\s*\(',
            r'import\s+\w+',
            r'from\s+\w+\s+import'
        ]
        
        for pattern in code_patterns:
            if re.search(pattern, text):
                return True
        
        return False


class MetricsAggregator:
    """
    Aggregates evaluation metrics over time.
    
    Provides summary statistics and trend analysis.
    """
    
    def __init__(self):
        self.evaluations: List[EvaluationResult] = []
        self.logger = get_logger(f"{__name__}.MetricsAggregator")
    
    def add_evaluation(self, result: EvaluationResult) -> None:
        """Add an evaluation result."""
        self.evaluations.append(result)
        
        # Keep only last 1000 evaluations in memory
        if len(self.evaluations) > 1000:
            self.evaluations = self.evaluations[-1000:]
    
    def get_summary(self, agent_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get summary statistics.
        
        Args:
            agent_name: Filter by agent name (optional)
            
        Returns:
            Summary statistics dict
        """
        evals = self.evaluations
        
        if agent_name:
            evals = [e for e in evals if e.agent_name == agent_name]
        
        if not evals:
            return {"count": 0}
        
        def avg(values):
            return sum(values) / len(values) if values else 0
        
        return {
            "count": len(evals),
            "avg_overall_score": round(avg([e.overall_score for e in evals]), 3),
            "avg_relevance": round(avg([e.relevance_score for e in evals]), 3),
            "avg_completeness": round(avg([e.completeness_score for e in evals]), 3),
            "avg_code_quality": round(avg([e.code_quality_score for e in evals]), 3),
            "avg_helpfulness": round(avg([e.helpfulness_score for e in evals]), 3),
            "avg_response_time_ms": round(avg([e.response_time_ms for e in evals]), 2),
            "code_output_rate": round(sum(1 for e in evals if e.has_code_output) / len(evals), 3),
            "avg_tool_calls": round(avg([e.tool_calls_count for e in evals]), 2)
        }
    
    def get_agent_breakdown(self) -> Dict[str, Dict[str, Any]]:
        """Get summary broken down by agent."""
        agents = set(e.agent_name for e in self.evaluations)
        return {agent: self.get_summary(agent) for agent in agents}


# Global instances
_evaluator: Optional[ResponseEvaluator] = None
_aggregator: Optional[MetricsAggregator] = None


def get_evaluator() -> ResponseEvaluator:
    """Get global evaluator instance."""
    global _evaluator
    if _evaluator is None:
        _evaluator = ResponseEvaluator()
    return _evaluator


def get_aggregator() -> MetricsAggregator:
    """Get global aggregator instance."""
    global _aggregator
    if _aggregator is None:
        _aggregator = MetricsAggregator()
    return _aggregator


def evaluate_response(
    user_input: str,
    agent_response: str,
    agent_name: str,
    session_id: str,
    response_time_ms: float,
    **kwargs
) -> EvaluationResult:
    """
    Convenience function to evaluate and aggregate.
    
    Returns:
        EvaluationResult
    """
    evaluator = get_evaluator()
    aggregator = get_aggregator()
    
    result = evaluator.evaluate(
        user_input=user_input,
        agent_response=agent_response,
        agent_name=agent_name,
        session_id=session_id,
        response_time_ms=response_time_ms,
        **kwargs
    )
    
    aggregator.add_evaluation(result)
    
    return result
