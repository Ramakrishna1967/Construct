"""
Code Analyzer Tool for Quality Metrics.

Provides code complexity analysis, quality metrics, and style checking.
"""

import os
import ast
import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from pathlib import Path

from src.config import get_settings
from src.logging_config import get_logger

settings = get_settings()
logger = get_logger(__name__)


@dataclass
class ComplexityMetric:
    """Code complexity metrics for a function."""
    name: str
    complexity: int
    line_number: int
    risk: str  # low, medium, high, very-high
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "complexity": self.complexity,
            "line": self.line_number,
            "risk": self.risk
        }


@dataclass
class QualityMetrics:
    """Overall code quality metrics."""
    lines_of_code: int
    blank_lines: int
    comment_lines: int
    functions: int
    classes: int
    avg_complexity: float
    max_complexity: int
    maintainability_index: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "loc": self.lines_of_code,
            "blank_lines": self.blank_lines,
            "comment_lines": self.comment_lines,
            "functions": self.functions,
            "classes": self.classes,
            "avg_complexity": round(self.avg_complexity, 2),
            "max_complexity": self.max_complexity,
            "maintainability": round(self.maintainability_index, 2)
        }


class CodeAnalyzer:
    """
    Advanced code analysis for quality metrics.
    
    Provides:
    - Cyclomatic complexity calculation
    - Lines of code metrics
    - Maintainability index
    - Function/class analysis
    """
    
    # Complexity threshold classification
    COMPLEXITY_THRESHOLDS = {
        "low": 10,
        "medium": 20,
        "high": 40
    }
    
    def __init__(self):
        """Initialize code analyzer."""
        self._radon_available = self._check_radon()
    
    def _check_radon(self) -> bool:
        """Check if Radon is available."""
        try:
            import radon
            logger.info("Radon code analysis library available")
            return True
        except ImportError:
            logger.warning("Radon not available, using built-in analysis")
            return False
    
    def analyze_file(self, file_path: str) -> Dict[str, Any]:
        """
        Analyze a Python file for quality metrics.
        
        Args:
            file_path: Path to Python file
            
        Returns:
            Dictionary with analysis results
        """
        if not os.path.exists(file_path):
            return {"error": f"File not found: {file_path}"}
        
        if not file_path.endswith(".py"):
            return {"error": "Only Python files supported"}
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            # Get basic metrics
            metrics = self._analyze_content(content)
            
            # Get complexity metrics
            complexity = self._calculate_complexity(content)
            
            return {
                "file": file_path,
                "metrics": metrics.to_dict(),
                "complexity": [c.to_dict() for c in complexity],
                "summary": self._generate_summary(metrics, complexity)
            }
            
        except Exception as e:
            logger.error(f"Analysis error for {file_path}: {e}", exc_info=True)
            return {"error": str(e)}
    
    def _analyze_content(self, content: str) -> QualityMetrics:
        """
        Analyze code content for metrics.
        
        Args:
            content: Python source code
            
        Returns:
            QualityMetrics instance
        """
        lines = content.split('\n')
        total_lines = len(lines)
        blank_lines = sum(1 for line in lines if not line.strip())
        comment_lines = sum(1 for line in lines if line.strip().startswith('#'))
        
        # Parse AST for structure analysis
        functions = 0
        classes = 0
        
        try:
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                    functions += 1
                elif isinstance(node, ast.ClassDef):
                    classes += 1
        except SyntaxError:
            pass
        
        # Get complexity metrics
        complexity_list = self._calculate_complexity(content)
        complexities = [c.complexity for c in complexity_list] or [0]
        avg_complexity = sum(complexities) / len(complexities)
        max_complexity = max(complexities)
        
        # Calculate maintainability index (simplified)
        # MI = 171 - 5.2*ln(HV) - 0.23*CC - 16.2*ln(LOC)
        loc = total_lines - blank_lines
        mi = max(0, min(100, 171 - 5.2 * _safe_log(loc) - 0.23 * avg_complexity - 16.2 * _safe_log(loc)))
        
        return QualityMetrics(
            lines_of_code=total_lines,
            blank_lines=blank_lines,
            comment_lines=comment_lines,
            functions=functions,
            classes=classes,
            avg_complexity=avg_complexity,
            max_complexity=max_complexity,
            maintainability_index=mi
        )
    
    def _calculate_complexity(self, content: str) -> List[ComplexityMetric]:
        """
        Calculate cyclomatic complexity for all functions.
        
        Uses Radon if available, otherwise falls back to AST analysis.
        
        Args:
            content: Python source code
            
        Returns:
            List of complexity metrics
        """
        if self._radon_available:
            try:
                from radon.complexity import cc_visit
                
                results = []
                for block in cc_visit(content):
                    risk = self._classify_risk(block.complexity)
                    results.append(ComplexityMetric(
                        name=block.name,
                        complexity=block.complexity,
                        line_number=block.lineno,
                        risk=risk
                    ))
                return results
                
            except Exception as e:
                logger.warning(f"Radon analysis failed, using fallback: {e}")
        
        # Fallback to AST-based analysis
        return self._ast_complexity(content)
    
    def _ast_complexity(self, content: str) -> List[ComplexityMetric]:
        """
        Calculate complexity using AST analysis.
        
        Args:
            content: Python source code
            
        Returns:
            List of complexity metrics
        """
        results = []
        
        try:
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    complexity = self._count_complexity(node)
                    risk = self._classify_risk(complexity)
                    results.append(ComplexityMetric(
                        name=node.name,
                        complexity=complexity,
                        line_number=node.lineno,
                        risk=risk
                    ))
                    
        except SyntaxError as e:
            logger.warning(f"AST parse error: {e}")
        
        return results
    
    def _count_complexity(self, node: ast.AST) -> int:
        """
        Count cyclomatic complexity of an AST node.
        
        Complexity = 1 + number of decision points
        
        Args:
            node: AST node to analyze
            
        Returns:
            Complexity score
        """
        complexity = 1  # Base complexity
        
        for child in ast.walk(node):
            # Decision points
            if isinstance(child, (ast.If, ast.While, ast.For, ast.AsyncFor)):
                complexity += 1
            elif isinstance(child, ast.ExceptHandler):
                complexity += 1
            elif isinstance(child, ast.Assert):
                complexity += 1
            elif isinstance(child, ast.comprehension):
                complexity += 1
            elif isinstance(child, (ast.And, ast.Or)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
        
        return complexity
    
    def _classify_risk(self, complexity: int) -> str:
        """Classify complexity into risk category."""
        if complexity <= self.COMPLEXITY_THRESHOLDS["low"]:
            return "low"
        elif complexity <= self.COMPLEXITY_THRESHOLDS["medium"]:
            return "medium"
        elif complexity <= self.COMPLEXITY_THRESHOLDS["high"]:
            return "high"
        return "very-high"
    
    def _generate_summary(
        self,
        metrics: QualityMetrics,
        complexity: List[ComplexityMetric]
    ) -> str:
        """Generate human-readable summary."""
        parts = []
        
        # Overall quality
        if metrics.maintainability_index >= 80:
            parts.append("✓ Good maintainability")
        elif metrics.maintainability_index >= 60:
            parts.append("◐ Moderate maintainability")
        else:
            parts.append("✗ Low maintainability")
        
        # Complexity
        high_complexity = [c for c in complexity if c.risk in ["high", "very-high"]]
        if high_complexity:
            parts.append(f"⚠ {len(high_complexity)} function(s) with high complexity")
        
        # Code ratio
        code_lines = metrics.lines_of_code - metrics.blank_lines - metrics.comment_lines
        comment_ratio = metrics.comment_lines / max(code_lines, 1)
        if comment_ratio < 0.1:
            parts.append("! Low comment ratio")
        
        return " | ".join(parts)


def _safe_log(n: float) -> float:
    """Safe natural logarithm that handles 0."""
    import math
    return math.log(max(n, 1))


# =============================================================================
# TOOL FUNCTIONS
# =============================================================================

_analyzer: Optional[CodeAnalyzer] = None


def get_analyzer() -> CodeAnalyzer:
    """Get or create code analyzer instance."""
    global _analyzer
    if _analyzer is None:
        _analyzer = CodeAnalyzer()
    return _analyzer


def analyze_complexity(path: str) -> str:
    """
    Analyze code complexity of file or directory.
    
    Args:
        path: Path to analyze
        
    Returns:
        Formatted complexity report
    """
    logger.info(f"analyze_complexity: {path}")
    
    try:
        analyzer = get_analyzer()
        
        if os.path.isfile(path):
            result = analyzer.analyze_file(path)
            if "error" in result:
                return f"Error: {result['error']}"
            
            output = [
                f"File: {path}",
                f"Summary: {result.get('summary', 'N/A')}",
                "",
                "Metrics:",
                f"  Lines of Code: {result['metrics']['loc']}",
                f"  Functions: {result['metrics']['functions']}",
                f"  Classes: {result['metrics']['classes']}",
                f"  Avg Complexity: {result['metrics']['avg_complexity']}",
                f"  Maintainability: {result['metrics']['maintainability']}"
            ]
            
            if result.get('complexity'):
                output.append("\nFunction Complexity:")
                for c in sorted(result['complexity'], key=lambda x: -x['complexity'])[:10]:
                    risk_icon = {"low": "✓", "medium": "◐", "high": "⚠", "very-high": "✗"}.get(c['risk'], "?")
                    output.append(f"  {risk_icon} {c['name']}: {c['complexity']} ({c['risk']})")
            
            return "\n".join(output)
            
        elif os.path.isdir(path):
            total_files = 0
            total_loc = 0
            high_complexity_files = []
            
            for root, _, files in os.walk(path):
                for file in files:
                    if file.endswith(".py"):
                        file_path = os.path.join(root, file)
                        result = analyzer.analyze_file(file_path)
                        if "error" not in result:
                            total_files += 1
                            total_loc += result['metrics']['loc']
                            if result['metrics']['max_complexity'] > 20:
                                high_complexity_files.append((file_path, result['metrics']['max_complexity']))
            
            output = [
                f"Directory: {path}",
                f"Total Python Files: {total_files}",
                f"Total Lines of Code: {total_loc}"
            ]
            
            if high_complexity_files:
                output.append(f"\n⚠ High Complexity Files ({len(high_complexity_files)}):")
                for fp, cc in sorted(high_complexity_files, key=lambda x: -x[1])[:5]:
                    output.append(f"  • {os.path.basename(fp)}: {cc}")
            
            return "\n".join(output)
        else:
            return f"Error: Path not found: {path}"
            
    except Exception as e:
        logger.error(f"analyze_complexity error: {e}", exc_info=True)
        return f"Error: {str(e)}"


def get_metrics(path: str) -> str:
    """
    Get code quality metrics for a file.
    
    Args:
        path: Path to file
        
    Returns:
        Formatted metrics
    """
    logger.info(f"get_metrics: {path}")
    
    try:
        analyzer = get_analyzer()
        result = analyzer.analyze_file(path)
        
        if "error" in result:
            return f"Error: {result['error']}"
        
        m = result['metrics']
        return (
            f"Lines of Code: {m['loc']}\n"
            f"Blank Lines: {m['blank_lines']}\n"
            f"Comment Lines: {m['comment_lines']}\n"
            f"Functions: {m['functions']}\n"
            f"Classes: {m['classes']}\n"
            f"Avg Complexity: {m['avg_complexity']}\n"
            f"Max Complexity: {m['max_complexity']}\n"
            f"Maintainability Index: {m['maintainability']}/100"
        )
        
    except Exception as e:
        logger.error(f"get_metrics error: {e}", exc_info=True)
        return f"Error: {str(e)}"
