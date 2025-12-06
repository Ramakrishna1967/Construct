"""
Configuration management for AI Code Reviewer backend.

Uses Pydantic Settings for type-safe configuration with environment variable support.
"""

import os
from typing import Optional, List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Google AI Configuration
    google_api_key: str = Field(..., description="Google Gemini API key")
    gemini_model: str = Field(
        default="gemini-2.0-flash-exp",
        description="Gemini model to use for code generation"
    )
    gemini_temperature: float = Field(
        default=0.0,
        ge=0.0,
        le=2.0,
        description="Temperature for LLM responses"
    )
    
    # Redis Configuration
    redis_url: str = Field(
        default="redis://localhost:6379",
        description="Redis connection URL"
    )
    redis_max_retries: int = Field(
        default=3,
        description="Maximum Redis connection retry attempts"
    )
    redis_retry_delay: float = Field(
        default=1.0,
        description="Delay between Redis retry attempts (seconds)"
    )
    
    # Docker Configuration
    docker_image: str = Field(
        default="python:3.11-slim",
        description="Docker image for sandbox execution"
    )
    docker_timeout: int = Field(
        default=30,
        description="Docker container execution timeout (seconds)"
    )
    docker_memory_limit: str = Field(
        default="512m",
        description="Docker container memory limit"
    )
    docker_cpu_limit: float = Field(
        default=1.0,
        description="Docker container CPU limit (cores)"
    )
    
    # Application Configuration
    app_host: str = Field(default="0.0.0.0", description="Application host")
    app_port: int = Field(default=8000, ge=1, le=65535, description="Application port")
    log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"
    )
    
    # Security Configuration
    allowed_file_extensions: str = Field(
        default=".py,.txt,.md,.json,.yaml,.yml,.toml",
        description="Comma-separated allowed file extensions"
    )
    max_file_size_mb: int = Field(
        default=10,
        description="Maximum file size for read operations (MB)"
    )
    command_timeout: int = Field(
        default=60,
        description="Command execution timeout (seconds)"
    )
    
    # Code Indexer Configuration
    indexer_max_file_size_mb: int = Field(
        default=5,
        description="Maximum file size for code indexing (MB)"
    )
    indexer_file_extensions: str = Field(
        default=".py",
        description="Comma-separated file extensions to index"
    )
    
    # CORS Configuration
    cors_origins: str = Field(
        default="*",
        description="Comma-separated CORS origins or * for all"
    )
    cors_allow_credentials: bool = Field(
        default=True,
        description="Allow credentials in CORS requests"
    )
    
    # LangSmith Tracing Configuration
    langchain_tracing_enabled: bool = Field(
        default=False,
        description="Enable LangSmith tracing for observability"
    )
    langchain_api_key: str = Field(
        default="",
        description="LangSmith API key (get free at smith.langchain.com)"
    )
    langchain_project: str = Field(
        default="ai-code-reviewer",
        description="LangSmith project name for grouping traces"
    )
    
    # Session Persistence Configuration
    redis_session_ttl_days: int = Field(
        default=7,
        description="Number of days to keep session data in Redis"
    )
    redis_socket_timeout: int = Field(
        default=5,
        description="Redis socket timeout in seconds"
    )
    
    # ==========================================================================
    # SECURITY & AUTHENTICATION
    # ==========================================================================
    
    environment: str = Field(
        default="development",
        description="Environment: development, staging, or production"
    )
    api_keys: str = Field(
        default="",
        description="Comma-separated list of valid API keys for authentication"
    )
    require_auth_in_dev: bool = Field(
        default=False,
        description="Require authentication even in development mode"
    )
    
    # ==========================================================================
    # GOOGLE OAUTH & JWT AUTHENTICATION
    # ==========================================================================
    
    google_client_id: str = Field(
        default="",
        description="Google OAuth Client ID from Google Cloud Console"
    )
    google_client_secret: str = Field(
        default="",
        description="Google OAuth Client Secret"
    )
    jwt_secret: str = Field(
        default="change-this-in-production-use-secrets-token",
        description="Secret key for JWT token signing (generate with: python -c 'import secrets; print(secrets.token_hex(32))')"
    )
    jwt_algorithm: str = Field(
        default="HS256",
        description="JWT signing algorithm"
    )
    jwt_expiry_hours: int = Field(
        default=24,
        description="JWT token expiry time in hours"
    )
    
    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v):
        """Validate environment is valid."""
        valid_envs = ["development", "staging", "production"]
        if v.lower() not in valid_envs:
            raise ValueError(f"environment must be one of {valid_envs}")
        return v.lower()
    
    @property
    def api_keys_list(self) -> List[str]:
        """Get API keys as list."""
        if not self.api_keys:
            return []
        return [key.strip() for key in self.api_keys.split(",") if key.strip()]
    
    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.environment == "production"
    
    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v):
        """Validate log level is valid."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"log_level must be one of {valid_levels}")
        return v.upper()
    
    @field_validator("google_api_key")
    @classmethod
    def validate_api_key(cls, v):
        """Validate API key is not empty."""
        if not v or v.strip() == "":
            raise ValueError("GOOGLE_API_KEY must be set")
        return v
    
    @property
    def allowed_extensions_list(self) -> List[str]:
        """Get allowed file extensions as list."""
        return [ext.strip() for ext in self.allowed_file_extensions.split(",")]
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Get CORS origins as list."""
        if self.cors_origins == "*":
            return ["*"]
        return [origin.strip() for origin in self.cors_origins.split(",")]


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get or create settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reload_settings() -> Settings:
    """Reload settings from environment."""
    global _settings
    _settings = Settings()
    return _settings
