"""
Security Scanner Tool for Code Review.

Provides security analysis using Bandit and custom checks.
"""

import os
import subprocess
import json
import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

from src.config import get_settings
from src.logging_config import get_logger

settings = get_settings()
logger = get_logger(__name__)


class Severity(Enum):
    """Security issue severity levels."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass
class SecurityIssue:
    """Represents a security issue found in code."""
    severity: Severity
    confidence: str
    issue_type: str
    message: str
    file_path: str
    line_number: int
    code_snippet: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "severity": self.severity.value,
            "confidence": self.confidence,
            "type": self.issue_type,
            "message": self.message,
            "file": self.file_path,
            "line": self.line_number,
            "code": self.code_snippet
        }


class SecurityScanner:
    """
    Security scanner with multiple detection methods.
    
    Provides:
    - Bandit analysis for Python
    - Custom pattern matching
    - Hardcoded secret detection
    - SQL injection patterns
    """
    
    # Patterns for common security issues
    SECRET_PATTERNS = [
        (r'(?i)(api[_-]?key|apikey)\s*[=:]\s*["\'][^"\']{10,}["\']', "Possible API key"),
        (r'(?i)(password|passwd|pwd)\s*[=:]\s*["\'][^"\']+["\']', "Hardcoded password"),
        (r'(?i)(secret|token)\s*[=:]\s*["\'][^"\']{10,}["\']', "Hardcoded secret"),
        (r'(?i)(aws_access_key_id|aws_secret_access_key)\s*[=:]\s*["\'][^"\']+["\']', "AWS credentials"),
        (r'(?i)-----BEGIN (RSA |DSA |EC )?PRIVATE KEY-----', "Private key"),
    ]
    
    INJECTION_PATTERNS = [
        (r'execute\s*\(\s*["\'].*%', "Possible SQL injection"),
        (r'subprocess\.(call|run|Popen)\s*\(\s*[^,\]]*\+', "Command injection risk"),
        (r'os\.system\s*\(\s*[^,)]*\+', "Command injection via os.system"),
        (r'eval\s*\(\s*[^,)]*\+', "Dangerous eval with string concatenation"),
        (r'exec\s*\(\s*[^,)]*\+', "Dangerous exec with string concatenation"),
    ]
    
    UNSAFE_PATTERNS = [
        (r'pickle\.loads?\s*\(', "Unsafe pickle deserialization"),
        (r'yaml\.load\s*\([^,)]*\)', "Unsafe YAML load (use safe_load)"),
        (r'assert\s+', "Assert used (disabled with -O flag)"),
        (r'input\s*\(\s*\)', "Raw input in Python 2 (use raw_input)"),
    ]
    
    def __init__(self):
        """Initialize security scanner."""
        self._bandit_available = self._check_bandit()
    
    def _check_bandit(self) -> bool:
        """Check if Bandit is available."""
        try:
            result = subprocess.run(
                ["bandit", "--version"],
                capture_output=True,
                timeout=5
            )
            if result.returncode == 0:
                logger.info("Bandit security scanner available")
                return True
        except Exception:
            pass
        
        logger.warning("Bandit not available, using pattern matching only")
        return False
    
    def scan_file(self, file_path: str) -> List[SecurityIssue]:
        """
        Scan a single file for security issues.
        
        Args:
            file_path: Path to file to scan
            
        Returns:
            List of security issues found
        """
        issues = []
        
        if not os.path.exists(file_path):
            logger.warning(f"File not found: {file_path}")
            return issues
        
        # Run Bandit if available
        if self._bandit_available and file_path.endswith(".py"):
            issues.extend(self._run_bandit(file_path))
        
        # Run pattern matching
        issues.extend(self._pattern_scan(file_path))
        
        return issues
    
    def scan_directory(
        self,
        directory: str,
        extensions: List[str] = None
    ) -> List[SecurityIssue]:
        """
        Scan a directory for security issues.
        
        Args:
            directory: Directory to scan
            extensions: File extensions to include
            
        Returns:
            List of security issues found
        """
        extensions = extensions or [".py"]
        issues = []
        
        if not os.path.isdir(directory):
            logger.warning(f"Directory not found: {directory}")
            return issues
        
        # Run Bandit on directory
        if self._bandit_available:
            issues.extend(self._run_bandit(directory))
        
        # Pattern scan all matching files
        for root, _, files in os.walk(directory):
            for file in files:
                if any(file.endswith(ext) for ext in extensions):
                    file_path = os.path.join(root, file)
                    issues.extend(self._pattern_scan(file_path))
        
        return issues
    
    def _run_bandit(self, target: str) -> List[SecurityIssue]:
        """
        Run Bandit security scanner.
        
        Args:
            target: File or directory to scan
            
        Returns:
            List of issues from Bandit
        """
        issues = []
        
        try:
            result = subprocess.run(
                [
                    "bandit",
                    "-r",
                    "-f", "json",
                    "-q",
                    target
                ],
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.stdout:
                data = json.loads(result.stdout)
                for item in data.get("results", []):
                    severity = Severity[item.get("issue_severity", "LOW").upper()]
                    issues.append(SecurityIssue(
                        severity=severity,
                        confidence=item.get("issue_confidence", "MEDIUM"),
                        issue_type=item.get("test_id", "unknown"),
                        message=item.get("issue_text", ""),
                        file_path=item.get("filename", ""),
                        line_number=item.get("line_number", 0),
                        code_snippet=item.get("code", "")[:200]
                    ))
                    
        except subprocess.TimeoutExpired:
            logger.error("Bandit scan timed out")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Bandit output: {e}")
        except Exception as e:
            logger.error(f"Bandit scan error: {e}", exc_info=True)
        
        return issues
    
    def _pattern_scan(self, file_path: str) -> List[SecurityIssue]:
        """
        Scan file using pattern matching.
        
        Args:
            file_path: Path to file
            
        Returns:
            List of pattern-matched issues
        """
        issues = []
        
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
            
            all_patterns = [
                (self.SECRET_PATTERNS, Severity.HIGH),
                (self.INJECTION_PATTERNS, Severity.HIGH),
                (self.UNSAFE_PATTERNS, Severity.MEDIUM),
            ]
            
            for patterns, severity in all_patterns:
                for pattern, message in patterns:
                    for i, line in enumerate(lines, 1):
                        if re.search(pattern, line):
                            issues.append(SecurityIssue(
                                severity=severity,
                                confidence="MEDIUM",
                                issue_type="pattern_match",
                                message=message,
                                file_path=file_path,
                                line_number=i,
                                code_snippet=line.strip()[:100]
                            ))
                            
        except Exception as e:
            logger.error(f"Pattern scan error for {file_path}: {e}")
        
        return issues


# =============================================================================
# TOOL FUNCTIONS
# =============================================================================

_scanner: Optional[SecurityScanner] = None


def get_scanner() -> SecurityScanner:
    """Get or create the security scanner instance."""
    global _scanner
    if _scanner is None:
        _scanner = SecurityScanner()
    return _scanner


def security_scan(path: str) -> str:
    """
    Scan file or directory for security issues.
    
    Args:
        path: Path to scan
        
    Returns:
        Formatted security report
    """
    logger.info(f"security_scan: {path}")
    
    try:
        scanner = get_scanner()
        
        if os.path.isfile(path):
            issues = scanner.scan_file(path)
        elif os.path.isdir(path):
            issues = scanner.scan_directory(path)
        else:
            return f"Error: Path not found: {path}"
        
        if not issues:
            return "✓ No security issues found"
        
        # Group by severity
        by_severity = {"CRITICAL": [], "HIGH": [], "MEDIUM": [], "LOW": []}
        for issue in issues:
            by_severity[issue.severity.value].append(issue)
        
        output = [f"Found {len(issues)} security issue(s):\n"]
        
        for severity in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
            if by_severity[severity]:
                output.append(f"\n{severity} ({len(by_severity[severity])}):")
                for issue in by_severity[severity][:5]:  # Limit per severity
                    output.append(
                        f"  • {issue.message}\n"
                        f"    {issue.file_path}:{issue.line_number}"
                    )
        
        return "\n".join(output)
        
    except Exception as e:
        logger.error(f"security_scan error: {e}", exc_info=True)
        return f"Error: {str(e)}"


def check_secrets(path: str) -> str:
    """
    Check for hardcoded secrets in code.
    
    Args:
        path: Path to check
        
    Returns:
        Report of found secrets
    """
    logger.info(f"check_secrets: {path}")
    
    try:
        scanner = get_scanner()
        issues = []
        
        if os.path.isfile(path):
            issues = scanner._pattern_scan(path)
        elif os.path.isdir(path):
            for root, _, files in os.walk(path):
                for file in files:
                    if file.endswith((".py", ".js", ".ts", ".env", ".yaml", ".yml")):
                        file_path = os.path.join(root, file)
                        issues.extend(scanner._pattern_scan(file_path))
        
        # Filter to secrets only
        secret_issues = [
            i for i in issues 
            if any(kw in i.message.lower() for kw in ["key", "secret", "password", "token", "credential"])
        ]
        
        if not secret_issues:
            return "✓ No hardcoded secrets detected"
        
        output = [f"⚠ Found {len(secret_issues)} potential secret(s):\n"]
        for issue in secret_issues[:10]:
            output.append(
                f"  • {issue.message}\n"
                f"    {issue.file_path}:{issue.line_number}"
            )
        
        return "\n".join(output)
        
    except Exception as e:
        logger.error(f"check_secrets error: {e}", exc_info=True)
        return f"Error: {str(e)}"
