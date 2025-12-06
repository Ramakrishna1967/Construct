"""
Redis store for state and memory management.

Provides async Redis operations with connection pooling and retry logic.
"""

import redis.asyncio as redis
import asyncio
import os
from typing import Optional
from src.config import get_settings
from src.logging_config import get_logger

settings = get_settings()
logger = get_logger(__name__)


class RedisStore:
    """Async Redis store with connection pooling and retry logic."""
    
    def __init__(self, url: str = None):
        """
        Initialize Redis store.
        
        Args:
            url: Redis connection URL (defaults to config value)
        """
        self.url = url or settings.redis_url
        self.client: Optional[redis.Redis] = None
        self._connection_pool: Optional[redis.ConnectionPool] = None
        logger.info(f"RedisStore initialized with URL: {self.url}")

    async def connect(self, retry: bool = True) -> None:
        """
        Connect to Redis with optional retry logic.
        
        Args:
            retry: Whether to retry on connection failure
        """
        if self.client:
            logger.debug("Redis client already connected")
            return
        
        max_retries = settings.redis_max_retries if retry else 1
        delay = settings.redis_retry_delay
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Connecting to Redis (attempt {attempt + 1}/{max_retries})")
                
                # Create connection pool with socket timeout for production
                self._connection_pool = redis.ConnectionPool.from_url(
                    self.url,
                    decode_responses=True,
                    max_connections=10,
                    socket_timeout=settings.redis_socket_timeout,
                    socket_connect_timeout=settings.redis_socket_timeout,
                    retry_on_timeout=True
                )
                
                self.client = redis.Redis(connection_pool=self._connection_pool)
                
                # Test connection
                await self.client.ping()
                logger.info("Successfully connected to Redis")
                return
                
            except (redis.ConnectionError, redis.TimeoutError) as e:
                if attempt == max_retries - 1:
                    logger.error(f"Failed to connect to Redis after {max_retries} attempts: {e}")
                    raise
                
                wait_time = delay * (2 ** attempt)
                logger.warning(f"Redis connection failed (attempt {attempt + 1}/{max_retries}), retrying in {wait_time}s: {e}")
                await asyncio.sleep(wait_time)

    async def health_check(self) -> bool:
        """
        Check if Redis connection is healthy.
        
        Returns:
            True if connected and responsive, False otherwise
        """
        try:
            if not self.client:
                await self.connect(retry=False)
            if not self.client:
                return False
            # Ping with timeout
            await asyncio.wait_for(self.client.ping(), timeout=2.0)
            return True
        except asyncio.TimeoutError:
            logger.error("Redis health check timed out")
            return False
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return False

    async def get(self, key: str) -> Optional[str]:
        """
        Get value from Redis.
        
        Args:
            key: Key to retrieve
            
        Returns:
            Value if found, None otherwise
        """
        try:
            await self.connect()
            value = await self.client.get(key)
            logger.debug(f"Redis GET {key}: {'found' if value else 'not found'}")
            return value
        except Exception as e:
            logger.error(f"Redis GET error for key {key}: {e}", exc_info=True)
            return None

    async def set(self, key: str, value: str, expire: int = None) -> bool:
        """
        Set value in Redis.
        
        Args:
            key: Key to set
            value: Value to store
            expire: Optional expiration time in seconds
            
        Returns:
            True if successful, False otherwise
        """
        try:
            await self.connect()
            result = await self.client.set(key, value, ex=expire)
            logger.debug(f"Redis SET {key} (expire={expire}): {result}")
            return bool(result)
        except Exception as e:
            logger.error(f"Redis SET error for key {key}: {e}", exc_info=True)
            return False

    async def delete(self, key: str) -> bool:
        """
        Delete key from Redis.
        
        Args:
            key: Key to delete
            
        Returns:
            True if key was deleted, False otherwise
        """
        try:
            await self.connect()
            result = await self.client.delete(key)
            logger.debug(f"Redis DELETE {key}: {result}")
            return bool(result)
        except Exception as e:
            logger.error(f"Redis DELETE error for key {key}: {e}", exc_info=True)
            return False

    # =========================================================================
    # CONVERSATION PERSISTENCE
    # =========================================================================
    
    async def save_conversation(
        self,
        session_id: str,
        messages: list,
        metadata: dict = None
    ) -> bool:
        """
        Save conversation history for a session.
        
        Args:
            session_id: Unique session identifier
            messages: List of message dicts
            metadata: Optional session metadata
            
        Returns:
            True if successful
        """
        try:
            await self.connect()
            
            import json
            from datetime import datetime
            
            # Prepare conversation data
            conversation_data = {
                "session_id": session_id,
                "messages": messages,
                "metadata": metadata or {},
                "updated_at": datetime.utcnow().isoformat(),
                "message_count": len(messages)
            }
            
            # Set created_at only if new session
            existing = await self.get_session_metadata(session_id)
            if existing:
                conversation_data["created_at"] = existing.get("created_at")
            else:
                conversation_data["created_at"] = datetime.utcnow().isoformat()
            
            # Store with TTL
            ttl_seconds = settings.redis_session_ttl_days * 24 * 60 * 60
            key = f"session:{session_id}:conversation"
            
            await self.client.set(key, json.dumps(conversation_data), ex=ttl_seconds)
            
            # Update session index
            await self._update_session_index(session_id, conversation_data)
            
            logger.debug(f"Saved conversation for session {session_id} ({len(messages)} messages)")
            return True
            
        except Exception as e:
            logger.error(f"Error saving conversation for {session_id}: {e}", exc_info=True)
            return False
    
    async def get_conversation(self, session_id: str) -> Optional[dict]:
        """
        Retrieve conversation history for a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Conversation data dict or None
        """
        try:
            await self.connect()
            import json
            
            key = f"session:{session_id}:conversation"
            data = await self.client.get(key)
            
            if data:
                return json.loads(data)
            return None
            
        except Exception as e:
            logger.error(f"Error getting conversation for {session_id}: {e}", exc_info=True)
            return None
    
    async def get_session_metadata(self, session_id: str) -> Optional[dict]:
        """
        Get metadata for a session (without full message history).
        
        Args:
            session_id: Session identifier
            
        Returns:
            Session metadata dict or None
        """
        try:
            conversation = await self.get_conversation(session_id)
            if conversation:
                return {
                    "session_id": session_id,
                    "created_at": conversation.get("created_at"),
                    "updated_at": conversation.get("updated_at"),
                    "message_count": conversation.get("message_count", 0),
                    "metadata": conversation.get("metadata", {})
                }
            return None
            
        except Exception as e:
            logger.error(f"Error getting session metadata for {session_id}: {e}", exc_info=True)
            return None
    
    async def list_sessions(self, limit: int = 50) -> list:
        """
        List recent sessions with metadata.
        
        Args:
            limit: Maximum number of sessions to return
            
        Returns:
            List of session metadata dicts
        """
        try:
            await self.connect()
            import json
            
            # Get session index
            index_key = "sessions:index"
            index_data = await self.client.get(index_key)
            
            if not index_data:
                return []
            
            sessions = json.loads(index_data)
            
            # Sort by updated_at (most recent first)
            sessions.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
            
            return sessions[:limit]
            
        except Exception as e:
            logger.error(f"Error listing sessions: {e}", exc_info=True)
            return []
    
    async def _update_session_index(self, session_id: str, data: dict) -> None:
        """Update the session index with session metadata."""
        try:
            import json
            
            index_key = "sessions:index"
            index_data = await self.client.get(index_key)
            
            if index_data:
                sessions = json.loads(index_data)
            else:
                sessions = []
            
            # Update or add session
            session_entry = {
                "session_id": session_id,
                "created_at": data.get("created_at"),
                "updated_at": data.get("updated_at"),
                "message_count": data.get("message_count", 0)
            }
            
            # Remove existing entry if present
            sessions = [s for s in sessions if s.get("session_id") != session_id]
            sessions.append(session_entry)
            
            # Keep only last 1000 sessions in index
            if len(sessions) > 1000:
                sessions.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
                sessions = sessions[:1000]
            
            await self.client.set(index_key, json.dumps(sessions))
            
        except Exception as e:
            logger.error(f"Error updating session index: {e}", exc_info=True)
    
    async def delete_session(self, session_id: str) -> bool:
        """
        Delete a session and its conversation history.
        
        Args:
            session_id: Session to delete
            
        Returns:
            True if deleted
        """
        try:
            await self.connect()
            import json
            
            # Delete conversation
            await self.delete(f"session:{session_id}:conversation")
            
            # Delete evaluations
            await self.delete(f"session:{session_id}:evaluations")
            
            # Remove from index
            index_key = "sessions:index"
            index_data = await self.client.get(index_key)
            
            if index_data:
                sessions = json.loads(index_data)
                sessions = [s for s in sessions if s.get("session_id") != session_id]
                await self.client.set(index_key, json.dumps(sessions))
            
            logger.info(f"Deleted session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting session {session_id}: {e}", exc_info=True)
            return False
    
    # =========================================================================
    # EVALUATION STORAGE
    # =========================================================================
    
    async def save_evaluation(self, session_id: str, evaluation: dict) -> bool:
        """
        Save evaluation metrics for a session.
        
        Args:
            session_id: Session identifier
            evaluation: Evaluation result dict
            
        Returns:
            True if successful
        """
        try:
            await self.connect()
            import json
            
            key = f"session:{session_id}:evaluations"
            
            # Get existing evaluations
            existing = await self.client.get(key)
            if existing:
                evaluations = json.loads(existing)
            else:
                evaluations = []
            
            evaluations.append(evaluation)
            
            # Keep last 100 evaluations per session
            if len(evaluations) > 100:
                evaluations = evaluations[-100:]
            
            ttl_seconds = settings.redis_session_ttl_days * 24 * 60 * 60
            await self.client.set(key, json.dumps(evaluations), ex=ttl_seconds)
            
            logger.debug(f"Saved evaluation for session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving evaluation for {session_id}: {e}", exc_info=True)
            return False
    
    async def get_evaluations(self, session_id: str) -> list:
        """
        Get evaluation metrics for a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            List of evaluation dicts
        """
        try:
            await self.connect()
            import json
            
            key = f"session:{session_id}:evaluations"
            data = await self.client.get(key)
            
            if data:
                return json.loads(data)
            return []
            
        except Exception as e:
            logger.error(f"Error getting evaluations for {session_id}: {e}", exc_info=True)
            return []

    async def close(self) -> None:
        """Close Redis connection and cleanup resources."""
        if self.client:
            try:
                await self.client.close()
                logger.info("Redis client closed")
            except Exception as e:
                logger.error(f"Error closing Redis client: {e}")
            finally:
                self.client = None
        
        if self._connection_pool:
            try:
                await self._connection_pool.disconnect()
                logger.info("Redis connection pool closed")
            except Exception as e:
                logger.error(f"Error closing Redis connection pool: {e}")
            finally:
                self._connection_pool = None

    async def __aenter__(self):
        """Context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        await self.close()

