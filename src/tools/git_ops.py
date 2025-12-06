"""
Git Operations Tool for Repository Management.

Provides Git operations for code version control and analysis.
"""

import os
import subprocess
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from src.config import get_settings
from src.logging_config import get_logger

settings = get_settings()
logger = get_logger(__name__)


class GitOperations:
    """
    Git repository operations with error handling.
    
    Provides:
    - Repository status and info
    - Diff analysis
    - Commit history
    - Branch operations
    """
    
    def __init__(self, repo_path: str = "."):
        """
        Initialize Git operations.
        
        Args:
            repo_path: Path to the Git repository
        """
        self.repo_path = os.path.abspath(repo_path)
        self._validate_repo()
    
    def _validate_repo(self) -> bool:
        """Check if path is a valid Git repository."""
        git_dir = os.path.join(self.repo_path, ".git")
        is_valid = os.path.isdir(git_dir)
        if not is_valid:
            logger.warning(f"Not a Git repository: {self.repo_path}")
        return is_valid
    
    def _run_git(
        self,
        args: List[str],
        timeout: int = 30
    ) -> Tuple[str, str, int]:
        """
        Run a Git command.
        
        Args:
            args: Git command arguments
            timeout: Command timeout in seconds
            
        Returns:
            Tuple of (stdout, stderr, return_code)
        """
        try:
            result = subprocess.run(
                ["git"] + args,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return result.stdout, result.stderr, result.returncode
            
        except subprocess.TimeoutExpired:
            return "", "Command timed out", -1
        except FileNotFoundError:
            return "", "Git not installed", -1
        except Exception as e:
            return "", str(e), -1
    
    def status(self) -> Dict[str, Any]:
        """
        Get repository status.
        
        Returns:
            Dictionary with status information
        """
        stdout, stderr, code = self._run_git(["status", "--porcelain", "-b"])
        
        if code != 0:
            return {"error": stderr, "success": False}
        
        lines = stdout.strip().split("\n")
        branch = ""
        modified = []
        untracked = []
        staged = []
        
        for line in lines:
            if not line:
                continue
            if line.startswith("##"):
                branch = line[3:].split("...")[0]
            elif line.startswith("M"):
                modified.append(line[3:])
            elif line.startswith("??"):
                untracked.append(line[3:])
            elif line.startswith("A"):
                staged.append(line[3:])
        
        return {
            "success": True,
            "branch": branch,
            "modified": modified,
            "untracked": untracked,
            "staged": staged,
            "clean": len(modified) == 0 and len(untracked) == 0 and len(staged) == 0
        }
    
    def diff(
        self,
        file_path: Optional[str] = None,
        staged: bool = False
    ) -> Dict[str, Any]:
        """
        Get diff for working directory or specific file.
        
        Args:
            file_path: Optional specific file to diff
            staged: Whether to show staged changes
            
        Returns:
            Dictionary with diff content
        """
        args = ["diff"]
        if staged:
            args.append("--staged")
        if file_path:
            args.append("--")
            args.append(file_path)
        
        stdout, stderr, code = self._run_git(args)
        
        if code != 0:
            return {"error": stderr, "success": False}
        
        return {
            "success": True,
            "diff": stdout,
            "has_changes": len(stdout.strip()) > 0
        }
    
    def log(
        self,
        n: int = 10,
        file_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get commit history.
        
        Args:
            n: Number of commits to retrieve
            file_path: Optional file to filter history
            
        Returns:
            Dictionary with commit history
        """
        args = [
            "log",
            f"-{n}",
            "--pretty=format:%H|%an|%ae|%ad|%s",
            "--date=iso"
        ]
        if file_path:
            args.append("--")
            args.append(file_path)
        
        stdout, stderr, code = self._run_git(args)
        
        if code != 0:
            return {"error": stderr, "success": False}
        
        commits = []
        for line in stdout.strip().split("\n"):
            if not line:
                continue
            parts = line.split("|", 4)
            if len(parts) == 5:
                commits.append({
                    "hash": parts[0],
                    "author": parts[1],
                    "email": parts[2],
                    "date": parts[3],
                    "message": parts[4]
                })
        
        return {
            "success": True,
            "commits": commits,
            "count": len(commits)
        }
    
    def blame(self, file_path: str) -> Dict[str, Any]:
        """
        Get blame information for a file.
        
        Args:
            file_path: Path to file
            
        Returns:
            Dictionary with blame information
        """
        stdout, stderr, code = self._run_git([
            "blame",
            "--line-porcelain",
            file_path
        ])
        
        if code != 0:
            return {"error": stderr, "success": False}
        
        return {
            "success": True,
            "blame": stdout[:5000]  # Truncate for large files
        }
    
    def show_file(
        self,
        file_path: str,
        ref: str = "HEAD"
    ) -> Dict[str, Any]:
        """
        Show file content at specific revision.
        
        Args:
            file_path: Path to file
            ref: Git reference (commit, branch, tag)
            
        Returns:
            Dictionary with file content
        """
        stdout, stderr, code = self._run_git([
            "show",
            f"{ref}:{file_path}"
        ])
        
        if code != 0:
            return {"error": stderr, "success": False}
        
        return {
            "success": True,
            "content": stdout,
            "ref": ref,
            "file": file_path
        }
    
    def get_current_branch(self) -> str:
        """Get the current branch name."""
        stdout, _, code = self._run_git(["branch", "--show-current"])
        return stdout.strip() if code == 0 else ""
    
    def get_remote_url(self) -> str:
        """Get the remote origin URL."""
        stdout, _, code = self._run_git(["remote", "get-url", "origin"])
        return stdout.strip() if code == 0 else ""


# =============================================================================
# TOOL FUNCTIONS
# =============================================================================

def git_status(repo_path: str = ".") -> str:
    """
    Get Git repository status.
    
    Args:
        repo_path: Path to repository
        
    Returns:
        Formatted status string
    """
    logger.info(f"git_status: {repo_path}")
    
    try:
        git = GitOperations(repo_path)
        result = git.status()
        
        if not result.get("success"):
            return f"Error: {result.get('error', 'Unknown error')}"
        
        output = [f"Branch: {result.get('branch', 'unknown')}"]
        
        if result.get("clean"):
            output.append("Working tree clean")
        else:
            if result.get("modified"):
                output.append(f"Modified: {', '.join(result['modified'])}")
            if result.get("staged"):
                output.append(f"Staged: {', '.join(result['staged'])}")
            if result.get("untracked"):
                output.append(f"Untracked: {', '.join(result['untracked'])}")
        
        return "\n".join(output)
        
    except Exception as e:
        logger.error(f"git_status error: {e}", exc_info=True)
        return f"Error: {str(e)}"


def git_diff(
    repo_path: str = ".",
    file_path: Optional[str] = None,
    staged: bool = False
) -> str:
    """
    Get Git diff.
    
    Args:
        repo_path: Path to repository
        file_path: Optional file to diff
        staged: Show staged changes
        
    Returns:
        Diff output
    """
    logger.info(f"git_diff: {repo_path} file={file_path} staged={staged}")
    
    try:
        git = GitOperations(repo_path)
        result = git.diff(file_path, staged)
        
        if not result.get("success"):
            return f"Error: {result.get('error', 'Unknown error')}"
        
        if not result.get("has_changes"):
            return "No changes"
        
        return result.get("diff", "")
        
    except Exception as e:
        logger.error(f"git_diff error: {e}", exc_info=True)
        return f"Error: {str(e)}"


def git_log(
    repo_path: str = ".",
    n: int = 10,
    file_path: Optional[str] = None
) -> str:
    """
    Get Git commit history.
    
    Args:
        repo_path: Path to repository
        n: Number of commits
        file_path: Optional file filter
        
    Returns:
        Formatted commit history
    """
    logger.info(f"git_log: {repo_path} n={n} file={file_path}")
    
    try:
        git = GitOperations(repo_path)
        result = git.log(n, file_path)
        
        if not result.get("success"):
            return f"Error: {result.get('error', 'Unknown error')}"
        
        output = []
        for commit in result.get("commits", []):
            output.append(
                f"{commit['hash'][:7]} - {commit['message']} "
                f"({commit['author']}, {commit['date'][:10]})"
            )
        
        return "\n".join(output) if output else "No commits found"
        
    except Exception as e:
        logger.error(f"git_log error: {e}", exc_info=True)
        return f"Error: {str(e)}"
