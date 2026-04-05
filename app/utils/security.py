"""
Security utilities — JWT authentication and role-based access control.

Provides:
    - Password hashing and verification (bcrypt via passlib)
    - JWT token creation and decoding
    - FastAPI dependencies for authentication and authorization

Configuration:
    SECRET_KEY and token expiry are read from app.config (environment variables).
"""

from datetime import datetime, timedelta
from typing import List

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_HOURS
from app.database import get_db
from app.models.user import User

# ─── Password Hashing ───────────────────────────────────────────

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a bcrypt hash."""
    return pwd_context.verify(plain_password, hashed_password)


# ─── JWT Token Management ───────────────────────────────────────

def create_token(data: dict) -> str:
    """
    Create a JWT access token.

    The token payload includes:
        - user_id: int
        - role: str
        - exp: expiration timestamp
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    to_encode["exp"] = expire
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    """
    Decode and validate a JWT token.

    Raises JWTError if the token is invalid or expired.
    """
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])


# ─── Authentication Dependencies ────────────────────────────────

security_scheme = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    FastAPI dependency: Extract and validate the JWT from the Authorization header.
    Returns the authenticated User object.

    Raises:
        401 Unauthorized — if token is missing, invalid, or expired
        401 Unauthorized — if the user no longer exists in the database
    """
    token = credentials.credentials

    try:
        payload = decode_token(token)
        user_id: int = payload.get("user_id")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing user_id",
            )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return user


def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    FastAPI dependency: Ensures the authenticated user is active.

    Raises:
        403 Forbidden — if the user account is deactivated
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated. Contact an administrator.",
        )
    return current_user


# ─── Role-Based Access Control ───────────────────────────────────

class RoleChecker:
    """
    FastAPI dependency class for role-based access control.

    Usage as a dependency that also injects the user:
        def endpoint(user: User = Depends(RoleChecker(["admin", "analyst"]))):
            ...

    Design Decision:
        Using a callable class rather than a plain function allows
        parameterized role requirements — each endpoint declares its
        required roles cleanly without code duplication.
    """

    def __init__(self, allowed_roles: List[str]):
        self.allowed_roles = allowed_roles

    def __call__(self, current_user: User = Depends(get_current_active_user)) -> User:
        if current_user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Access denied. Required role(s): {', '.join(self.allowed_roles)}. "
                    f"Your role: {current_user.role}"
                ),
            )
        return current_user
