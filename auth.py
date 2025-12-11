import secrets
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

# Simulated users database (in production, use hashed passwords!)
USERS_DB = {
    "admin": "secret123",
    "user": "pass456"
}

# Active tokens storage (in production, use Redis or similar)
active_tokens = {}

TOKEN_EXPIRE_HOURS = 24


def create_access_token(username: str) -> str:
    """Generate a new access token"""
    token = secrets.token_urlsafe(32)
    active_tokens[token] = {
        "username": username,
        "expires": datetime.now() + timedelta(hours=TOKEN_EXPIRE_HOURS)
    }
    return token


def verify_user_credentials(username: str, password: str) -> bool:
    """Verify username and password"""
    return username in USERS_DB and USERS_DB[username] == password


def invalidate_user_tokens(username: str) -> None:
    """Invalidate all tokens for a user"""
    tokens_to_remove = [t for t, data in active_tokens.items() if data["username"] == username]
    for token in tokens_to_remove:
        del active_tokens[token]


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """Dependency to get current authenticated user"""
    token = credentials.credentials
    
    if token not in active_tokens:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token_data = active_tokens[token]
    
    if datetime.now() > token_data["expires"]:
        del active_tokens[token]
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return token_data["username"]
