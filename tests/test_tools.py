"""
Tools Tests.
"""

import pytest
import tempfile
import os
from pathlib import Path


class TestFileOps:
    """Tests for file operations tools."""
    
    def test_write_and_read_file(self):
        """Test writing and reading a file."""
        from src.tools.file_ops import write_file, read_file
        
        with tempfile.TemporaryDirectory() as tmpdir:
            test_path = os.path.join(tmpdir, "test.py")
            content = "print('hello')"
            
            # Write
            result = write_file(test_path, content)
            assert "Successfully" in result
            
            # Read
            read_content = read_file(test_path)
            assert read_content == content
            
    def test_list_dir(self):
        """Test listing directory contents."""
        from src.tools.file_ops import list_dir
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create some files
            Path(tmpdir, "file1.py").touch()
            Path(tmpdir, "file2.py").touch()
            os.makedirs(os.path.join(tmpdir, "subdir"))
            
            result = list_dir(tmpdir)
            
            assert "file1.py" in result
            assert "file2.py" in result
            assert "subdir" in result
            
    def test_read_nonexistent_file(self):
        """Reading nonexistent file should return error."""
        from src.tools.file_ops import read_file
        
        result = read_file("/nonexistent/path/file.py")
        
        assert "Error" in result
        
    def test_path_traversal_blocked(self):
        """Path traversal should be blocked."""
        from src.tools.file_ops import read_file
        
        result = read_file("../../../etc/passwd")
        
        assert "Error" in result


class TestSecurityScanner:
    """Tests for security scanner."""
    
    def test_detect_hardcoded_secret(self):
        """Scanner should detect hardcoded secrets."""
        from src.tools.security_scanner import SecurityScanner
        
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = os.path.join(tmpdir, "test.py")
            with open(test_file, "w") as f:
                f.write('API_KEY = "sk-1234567890abcdef"')
            
            scanner = SecurityScanner()
            issues = scanner._pattern_scan(test_file)
            
            assert len(issues) > 0
            assert any("key" in i.message.lower() for i in issues)
            
    def test_clean_code_no_issues(self):
        """Clean code should have no issues."""
        from src.tools.security_scanner import SecurityScanner
        
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = os.path.join(tmpdir, "clean.py")
            with open(test_file, "w") as f:
                f.write('def hello():\n    return "Hello, World!"')
            
            scanner = SecurityScanner()
            issues = scanner._pattern_scan(test_file)
            
            # May still have issues from general patterns
            # but no secret/injection issues
            secret_issues = [
                i for i in issues
                if "key" in i.message.lower() or "secret" in i.message.lower()
            ]
            assert len(secret_issues) == 0


class TestCodeAnalyzer:
    """Tests for code analyzer."""
    
    def test_analyze_simple_function(self):
        """Test analyzing simple function."""
        from src.tools.code_analyzer import CodeAnalyzer
        
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = os.path.join(tmpdir, "test.py")
            with open(test_file, "w") as f:
                f.write('''
def hello():
    """Say hello."""
    print("Hello")
''')
            
            analyzer = CodeAnalyzer()
            result = analyzer.analyze_file(test_file)
            
            assert "error" not in result
            assert result["metrics"]["functions"] == 1
            
    def test_complexity_detection(self):
        """Test complexity detection."""
        from src.tools.code_analyzer import CodeAnalyzer
        
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = os.path.join(tmpdir, "complex.py")
            with open(test_file, "w") as f:
                f.write('''
def complex_function(x):
    if x > 0:
        if x > 10:
            if x > 100:
                return "large"
            return "medium"
        return "small"
    else:
        if x < -10:
            return "negative large"
        return "negative"
''')
            
            analyzer = CodeAnalyzer()
            result = analyzer.analyze_file(test_file)
            
            assert "error" not in result
            # Complex function should have higher complexity
            assert result["metrics"]["max_complexity"] > 1


class TestGitOps:
    """Tests for Git operations."""
    
    def test_git_status_not_repo(self):
        """git_status should handle non-repo directories."""
        from src.tools.git_ops import git_status
        
        with tempfile.TemporaryDirectory() as tmpdir:
            result = git_status(tmpdir)
            
            # Should not crash, might show error or empty
            assert isinstance(result, str)
