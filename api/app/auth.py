"""
OC-Monitor v3.0 - authentication helpers.
"""
from datetime import datetime, timedelta, timezone
from secrets import compare_digest
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel
from app.config import settings

ALGORITHM = "HS256"
security = HTTPBearer(auto_error=False)


class TokenData(BaseModel):
    username: Optional[str] = None


class User(BaseModel):
    username: str
    disabled: bool = False


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    payload = data.copy()
    payload.update({"exp": expire})
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def authenticate_admin(username: str, password: str) -> Optional[User]:
    if not settings.INITIAL_ADMIN_PASSWORD:
        return None
    if not compare_digest(username, settings.INITIAL_ADMIN_USERNAME):
        return None
    if not compare_digest(password, settings.INITIAL_ADMIN_PASSWORD):
        return None
    return User(username=username)


def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> TokenData:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated", headers={"WWW-Authenticate": "Bearer"})
    try:
        payload = jwt.decode(credentials.credentials, settings.SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials", headers={"WWW-Authenticate": "Bearer"}) from exc
    username = payload.get("sub")
    if not username:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials", headers={"WWW-Authenticate": "Bearer"})
    return TokenData(username=username)


def get_current_active_user(token_data: TokenData = Depends(verify_token)) -> User:
    if token_data.username != settings.INITIAL_ADMIN_USERNAME:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return User(username=token_data.username)
