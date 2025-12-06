"""
Docker sandbox for isolated code execution.

Provides safe code execution in isolated Docker containers with resource limits.
"""

import docker
import asyncio
from typing import Tuple, Optional, Dict
from src.config import get_settings
from src.logging_config import get_logger

settings = get_settings()
logger = get_logger(__name__)


class DockerSandbox:
    """Docker-based sandbox for safe code execution."""
    
    def __init__(self):
        """Initialize Docker sandbox."""
        try:
            self.client = docker.from_env()
            logger.info("Docker client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Docker client: {e}", exc_info=True)
            raise

    async def run_command(
        self,
        image: str,
        command: str,
        work_dir: str = "/app",
        volumes: Optional[Dict[str, dict]] = None,
        timeout: Optional[int] = None
    ) -> Tuple[str, str, int]:
        """
        Run a command in a Docker container with resource limits.
        
        Args:
            image: Docker image to use
            command: Command to execute
            work_dir: Working directory in container
            volumes: Volume mounts (e.g., {'/host/path': {'bind': '/container/path', 'mode': 'rw'}})
            timeout: Command timeout in seconds (defaults to config value)
            
        Returns:
            Tuple of (stdout, stderr, exit_code)
        """
        timeout = timeout or settings.docker_timeout
        logger.info(f"Running command in Docker: {image} - {command[:100]}")
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self._run_sync,
            image,
            command,
            work_dir,
            volumes,
            timeout
        )

    def _run_sync(
        self,
        image: str,
        command: str,
        work_dir: str,
        volumes: Optional[Dict[str, dict]],
        timeout: int
    ) -> Tuple[str, str, int]:
        """
        Synchronous Docker execution (called from executor).
        
        Args:
            image: Docker image
            command: Command to run
            work_dir: Working directory
            volumes: Volume mounts
            timeout: Timeout in seconds
            
        Returns:
            Tuple of (stdout, stderr, exit_code)
        """
        container = None
        
        try:
            # Pull image if not available
            try:
                self.client.images.get(image)
                logger.debug(f"Docker image {image} already available")
            except docker.errors.ImageNotFound:
                logger.info(f"Pulling Docker image: {image}")
                self.client.images.pull(image)
                logger.info(f"Successfully pulled image: {image}")
            
            # Parse resource limits
            mem_limit = settings.docker_memory_limit
            cpu_limit = int(settings.docker_cpu_limit * 1e9)  # Convert to nanocpus
            
            logger.debug(f"Resource limits: memory={mem_limit}, cpu={cpu_limit}")
            
            # Run container
            container = self.client.containers.run(
                image,
                command,
                working_dir=work_dir,
                detach=True,
                volumes=volumes,
                mem_limit=mem_limit,
                nano_cpus=cpu_limit,
                network_disabled=False,  # Enable if network access is needed
                remove=False  # We'll manually remove after getting logs
            )
            
            logger.debug(f"Container {container.id[:12]} started")
            
            # Wait for container with timeout
            try:
                result = container.wait(timeout=timeout)
                exit_code = result.get('StatusCode', -1)
                logger.debug(f"Container {container.id[:12]} exited with code {exit_code}")
            except Exception as timeout_error:
                logger.error(f"Container execution timeout after {timeout}s")
                container.stop(timeout=5)
                return "", f"Execution timeout after {timeout} seconds", -1
            
            # Get logs
            stdout = container.logs(stdout=True, stderr=False).decode('utf-8', errors='replace')
            stderr = container.logs(stdout=False, stderr=True).decode('utf-8', errors='replace')
            
            logger.debug(f"Container {container.id[:12]} stdout: {len(stdout)} bytes")
            logger.debug(f"Container {container.id[:12]} stderr: {len(stderr)} bytes")
            
            # Cleanup
            container.remove()
            logger.debug(f"Container {container.id[:12]} removed")
            
            return stdout, stderr, exit_code
            
        except docker.errors.ImageNotFound as e:
            error_msg = f"Docker image not found: {image}"
            logger.error(error_msg)
            return "", error_msg, -1
            
        except docker.errors.APIError as e:
            error_msg = f"Docker API error: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return "", error_msg, -1
            
        except Exception as e:
            error_msg = f"Docker execution error: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return "", error_msg, -1
            
        finally:
            # Ensure container is cleaned up
            if container:
                try:
                    container.reload()
                    if container.status != 'exited':
                        logger.warning(f"Forcing stop of container {container.id[:12]}")
                        container.stop(timeout=5)
                    container.remove()
                except Exception as cleanup_error:
                    logger.error(f"Error during container cleanup: {cleanup_error}")

    def __del__(self):
        """Cleanup Docker client on deletion."""
        try:
            if hasattr(self, 'client'):
                self.client.close()
                logger.debug("Docker client closed")
        except Exception:
            pass
