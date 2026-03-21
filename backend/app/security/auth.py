"""Security: Authentication, Authorization, Tenant Isolation"""
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel

from app.core.config import settings

# Simple bearer token auth (can be extended to JWT)
security = HTTPBearer(auto_error=False)


class TokenPayload(BaseModel):
    """JWT token payload"""
    sub: str  # user_id
    tenant_id: Optional[str] = None
    project_id: Optional[str] = None
    role: str = "user"  # "admin", "user", "service"


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> TokenPayload:
    """Extract and validate current user from token"""
    # Skip auth in debug mode for testing
    if settings.debug:
        return TokenPayload(
            sub="test-user",
            tenant_id="test-tenant",
            project_id="test-project",
            role="admin"
        )

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    token = credentials.credentials
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=["HS256"],
        )
        return TokenPayload(**payload)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )


def create_access_token(data: dict, expires_delta: Optional[int] = None) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        to_encode.update({"exp": expires_delta})
    return jwt.encode(to_encode, settings.secret_key, algorithm="HS256")
