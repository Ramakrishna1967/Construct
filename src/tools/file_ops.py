"""
File operations tools with security and validation.

Provides safe file read/write/list operations with path validation.
"""

import os
from pathlib import Path
from src.config import get_settings
from src.logging_config import get_logger

settings = get_settings()
logger = get_logger(__name__)


def _validate_path(path: str, operation: str) -> tuple[bool, str]:
    """
    Validate file path for security.
    
    Args:
        path: Path to validate
        operation: Operation being performed (for logging)
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        # Convert to absolute path
        abs_path = os.path.abspath(path)
        
        # Check for directory traversal
        if ".." in path:
            error = f"Path traversal not allowed: {path}"
            logger.warning(f"{operation} blocked: {error}")
            return False, error
        
        # Check file extension for read/write operations
        if operation in ["read", "write"]:
            ext = os.path.splitext(path)[1]
            if ext and ext not in settings.allowed_file_extensions:
                error = f"File extension not allowed: {ext}"
                logger.warning(f"{operation} blocked: {error}")
                return False, error
        
        return True, ""
    except Exception as e:
        error = f"Path validation error: {str(e)}"
        logger.error(error)
        return False, error


def read_file(path: str) -> str:
    """
    Read file contents with security checks.
    
    Args:
        path: Path to file
        
    Returns:
        File contents or error message
    """
    logger.info(f"read_file: {path}")
    
    # Validate path
    valid, error = _validate_path(path, "read")
    if not valid:
        return f"Error: {error}"
    
    if not os.path.exists(path):
        error = f"File {path} does not exist"
        logger.warning(error)
        return f"Error: {error}"
    
    try:
        # Check file size
        file_size = os.path.getsize(path)
        max_size = settings.max_file_size_mb * 1024 * 1024
        
        if file_size > max_size:
            error = f"File too large ({file_size} bytes, max {max_size})"
            logger.warning(f"read_file blocked: {error}")
            return f"Error: {error}"
        
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        
        logger.debug(f"read_file success: {path} ({file_size} bytes)")
        return content
        
    except UnicodeDecodeError as e:
        error = f"Unable to decode file as UTF-8: {str(e)}"
        logger.error(f"read_file error: {error}")
        return f"Error: {error}"
        
    except PermissionError as e:
        error = f"Permission denied: {str(e)}"
        logger.error(f"read_file error: {error}")
        return f"Error: {error}"
        
    except Exception as e:
        error = f"Failed to read file: {str(e)}"
        logger.error(f"read_file error: {error}", exc_info=True)
        return f"Error: {error}"


def write_file(path: str, content: str) -> str:
    """
    Write content to file with security checks.
    
    Args:
        path: Path to file
        content: Content to write
        
    Returns:
        Success or error message
    """
    logger.info(f"write_file: {path} ({len(content)} bytes)")
    
    # Validate path
    valid, error = _validate_path(path, "write")
    if not valid:
        return f"Error: {error}"
    
    try:
        # Ensure directory exists
        dir_path = os.path.dirname(path)
        if dir_path:
            os.makedirs(dir_path, exist_ok=True)
            logger.debug(f"Created directory: {dir_path}")
        
        # Write file
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        
        logger.info(f"write_file success: {path}")
        return f"Successfully wrote to {path}"
        
    except PermissionError as e:
        error = f"Permission denied: {str(e)}"
        logger.error(f"write_file error: {error}")
        return f"Error: {error}"
        
    except Exception as e:
        error = f"Failed to write file: {str(e)}"
        logger.error(f"write_file error: {error}", exc_info=True)
        return f"Error: {error}"


def list_dir(path: str) -> str:
    """
    List directory contents.
    
    Args:
        path: Directory path
        
    Returns:
        Directory listing or error message
    """
    logger.info(f"list_dir: {path}")
    
    # Validate path
    valid, error = _validate_path(path, "list")
    if not valid:
        return f"Error: {error}"
    
    if not os.path.exists(path):
        error = f"Directory {path} does not exist"
        logger.warning(error)
        return f"Error: {error}"
    
    if not os.path.isdir(path):
        error = f"Path is not a directory: {path}"
        logger.warning(error)
        return f"Error: {error}"
    
    try:
        entries = os.listdir(path)
        
        # Format output with file/dir indicator
        result = []
        for entry in sorted(entries):
            full_path = os.path.join(path, entry)
            if os.path.isdir(full_path):
                result.append(f"[DIR]  {entry}")
            else:
                size = os.path.getsize(full_path)
                result.append(f"[FILE] {entry} ({size} bytes)")
        
        logger.debug(f"list_dir success: {path} ({len(entries)} entries)")
        return "\n".join(result) if result else "(empty directory)"
        
    except PermissionError as e:
        error = f"Permission denied: {str(e)}"
        logger.error(f"list_dir error: {error}")
        return f"Error: {error}"
        
    except Exception as e:
        error = f"Failed to list directory: {str(e)}"
        logger.error(f"list_dir error: {error}", exc_info=True)
        return f"Error: {error}"
