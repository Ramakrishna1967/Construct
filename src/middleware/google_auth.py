"""
Google OAuth Authentication Module.

Handles Google login, JWT token generation, and user session management.
"""

import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from dataclasses import dataclass
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from fastapi import HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from src.config import get_settings
from src.logging_config import get_logger

logger = get_logger(__name__)
settings = get_settings()

security = HTTPBearer(auto_error=False)


@dataclass
class UserInfo:
    """User information from Google OAuth."""
    id: str
    email: str
    name: str
    picture: Optional[str] = None
    email_verified: bool = True


@dataclass
class TokenPayload:
    """JWT token payload."""
    user_id: str
    email: str
    name: str
    exp: datetime
    iat: datetime


# In-memory user store (replace with database in production)
_users: Dict[str, Dict[str, Any]] = {}
_user_usage: Dict[str, Dict[str, int]] = {}


async def verify_google_token(token: str) -> Optional[UserInfo]:
    """
    Verify Google OAuth token and extract user info.
    
    Args:
        token: Google ID token from frontend
        
    Returns:
        UserInfo if valid, None otherwise
    """
    try:
        if not settings.google_client_id:
            logger.warning("Google Client ID not configured")
            return None
        
        # Verify the token with Google
        idinfo = id_token.verify_oauth2_token(
            token,
            google_requests.Request(),
            settings.google_client_id
        )
        
        # Check issuer
        if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
            logger.warning("Invalid token issuer")
            return None
        
        # Extract user info
        user = UserInfo(
            id=idinfo['sub'],
            email=idinfo['email'],
            name=idinfo.get('name', idinfo['email'].split('@')[0]),
            picture=idinfo.get('picture'),
            email_verified=idinfo.get('email_verified', True)
        )
        
        # Store/update user
        _users[user.id] = {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "picture": user.picture,
            "created_at": _users.get(user.id, {}).get("created_at", datetime.utcnow().isoformat()),
            "last_login": datetime.utcnow().isoformat()
        }
        
        logger.info(f"User authenticated: {user.email}")
        return user
        
    except ValueError as e:
        logger.error(f"Invalid Google token: {e}")
        return None
    except Exception as e:
        logger.error(f"Error verifying Google token: {e}")
        return None


def create_jwt_token(user: UserInfo) -> str:
    """
    Create JWT token for authenticated user.
    
    Args:
        user: Verified user info
        
    Returns:
        JWT token string
    """
    now = datetime.utcnow()
    payload = {
        "user_id": user.id,
        "email": user.email,
        "name": user.name,
        "iat": now,
        "exp": now + timedelta(hours=settings.jwt_expiry_hours)
    }
    
    token = jwt.encode(
        payload,
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm
    )
    
    return token


def verify_jwt_token(token: str) -> Optional[TokenPayload]:
    """
    Verify JWT token and extract payload.
    
    Args:
        token: JWT token string
        
    Returns:
        TokenPayload if valid, None otherwise
    """
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm]
        )
        
        return TokenPayload(
            user_id=payload["user_id"],
            email=payload["email"],
            name=payload["name"],
            exp=datetime.fromtimestamp(payload["exp"]),
            iat=datetime.fromtimestamp(payload["iat"])
        )
        
    except jwt.ExpiredSignatureError:
        logger.warning("JWT token expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid JWT token: {e}")
        return None


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[TokenPayload]:
    """
    Dependency to get current authenticated user.
    
    Args:
        credentials: Bearer token from request
        
    Returns:
        TokenPayload if authenticated, None otherwise
    """
    if not credentials:
        return None
    
    return verify_jwt_token(credentials.credentials)


async def require_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> TokenPayload:
    """
    Dependency that requires authenticated user.
    
    Raises:
        HTTPException: If not authenticated
    """
    if not credentials:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    user = verify_jwt_token(credentials.credentials)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    return user


def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    """Get user data by ID."""
    return _users.get(user_id)


def track_user_action(user_id: str, action: str) -> None:
    """
    Track user action for analytics.
    
    Args:
        user_id: User ID
        action: Action name (review, chat, file_access)
    """
    today = datetime.utcnow().strftime("%Y-%m-%d")
    
    if user_id not in _user_usage:
        _user_usage[user_id] = {}
    
    if today not in _user_usage[user_id]:
        _user_usage[user_id][today] = {"review": 0, "chat": 0, "file_access": 0}
    
    if action in _user_usage[user_id][today]:
        _user_usage[user_id][today][action] += 1
    
    logger.debug(f"Tracked action '{action}' for user {user_id}")


def get_user_usage(user_id: str) -> Dict[str, Any]:
    """
    Get user's usage statistics.
    
    Args:
        user_id: User ID
        
    Returns:
        Usage stats with daily limits
    """
    today = datetime.utcnow().strftime("%Y-%m-%d")
    daily_limit = 100  # Free tier limit
    
    usage = _user_usage.get(user_id, {}).get(today, {"review": 0, "chat": 0, "file_access": 0})
    
    return {
        "daily_limit": daily_limit,
        "used_today": usage.get("review", 0) + usage.get("chat", 0),
        "remaining": max(0, daily_limit - usage.get("review", 0) - usage.get("chat", 0)),
        "breakdown": usage,
        "date": today
    }


__all__ = [
    "UserInfo",
    "TokenPayload",
    "verify_google_token",
    "create_jwt_token",
    "verify_jwt_token",
    "get_current_user",
    "require_user",
    "get_user_by_id",
    "track_user_action",
    "get_user_usage"
]
