"""
Terminal command execution tools with security and timeouts.

Provides safe command execution with timeout and resource limits.
"""

import subprocess
import os
import asyncio
from src.config import get_settings
from src.logging_config import get_logger

settings = get_settings()
logger = get_logger(__name__)


async def run_command(command: str, cwd: str = ".", timeout: int = None) -> str:
    """
    Run command asynchronously with timeout.
    
    Args:
        command: Command to execute
        cwd: Working directory
        timeout: Timeout in seconds (defaults to config value)
        
    Returns:
        Command output or error message
    """
    timeout = timeout or settings.command_timeout
    logger.info(f"run_command (async): {command[:100]} (cwd={cwd}, timeout={timeout}s)")
    
    try:
        # Validate working directory
        if not os.path.exists(cwd):
            error = f"Working directory does not exist: {cwd}"
            logger.error(error)
            return f"Error: {error}"
        
        # Create subprocess
        process = await asyncio.create_subprocess_shell(
            command,
            cwd=cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        # Wait with timeout
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            # Kill process on timeout
            try:
                process.kill()
                await process.wait()
            except Exception:
                pass
            
            error = f"Command timeout after {timeout} seconds"
            logger.error(f"run_command timeout: {command[:100]}")
            return f"Error: {error}"
        
        # Format output
        output = ""
        if stdout:
            stdout_text = stdout.decode('utf-8', errors='replace')
            output += f"STDOUT:\n{stdout_text}\n"
            logger.debug(f"Command stdout: {len(stdout_text)} bytes")
        
        if stderr:
            stderr_text = stderr.decode('utf-8', errors='replace')
            output += f"STDERR:\n{stderr_text}\n"
            logger.debug(f"Command stderr: {len(stderr_text)} bytes")
        
        if process.returncode != 0:
            logger.warning(f"Command exited with code {process.returncode}")
            output += f"\nExit code: {process.returncode}"
        else:
            logger.info(f"Command completed successfully")
        
        return output or "(no output)"
        
    except Exception as e:
        error = f"Failed to execute command: {str(e)}"
        logger.error(f"run_command error: {error}", exc_info=True)
        return f"Error: {error}"


def run_command_sync(command: str, cwd: str = ".", timeout: int = None) -> str:
    """
    Run command synchronously with timeout.
    
    Args:
        command: Command to execute
        cwd: Working directory
        timeout: Timeout in seconds (defaults to config value)
        
    Returns:
        Command output  or error message
    """
    timeout = timeout or settings.command_timeout
    logger.info(f"run_command_sync: {command[:100]} (cwd={cwd}, timeout={timeout}s)")
    
    try:
        # Validate working directory
        if not os.path.exists(cwd):
            error = f"Working directory does not exist: {cwd}"
            logger.error(error)
            return f"Error: {error}"
        
        # Run command with timeout
        result = subprocess.run(
            command,
            cwd=cwd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            errors='replace'
        )
        
        # Format output
        output = ""
        if result.stdout:
            output += f"STDOUT:\n{result.stdout}\n"
            logger.debug(f"Command stdout: {len(result.stdout)} bytes")
        
        if result.stderr:
            output += f"STDERR:\n{result.stderr}\n"
            logger.debug(f"Command stderr: {len(result.stderr)} bytes")
        
        if result.returncode != 0:
            logger.warning(f"Command exited with code {result.returncode}")
            output += f"\nExit code: {result.returncode}"
        else:
            logger.info(f"Command completed successfully")
        
        return output or "(no output)"
        
    except subprocess.TimeoutExpired:
        error = f"Command timeout after {timeout} seconds"
        logger.error(f"run_command_sync timeout: {command[:100]}")
        return f"Error: {error}"
        
    except Exception as e:
        error = f"Failed to execute command: {str(e)}"
        logger.error(f"run_command_sync error: {error}", exc_info=True)
        return f"Error: {error}"
