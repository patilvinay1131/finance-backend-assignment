"""
Authentication routes — register, login, and profile endpoints.

These are thin HTTP handlers that delegate business logic to UserService.
They handle only: request parsing, response formatting, and HTTP concerns.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.user_schema import (
    UserCreate,
    UserLogin,
    UserResponse,
    TokenResponse,
)
from app.services.user_service import UserService
from app.utils.security import get_current_active_user

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Create a new user account. Email must be unique. Password is hashed with bcrypt.",
)
def register(user: UserCreate, db: Session = Depends(get_db)):
    service = UserService(db)
    new_user = service.register(
        name=user.name,
        email=user.email,
        password=user.password,
        role=user.role.value,
    )
    return new_user


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login and get JWT token",
    description="Authenticate with email and password. Returns a JWT bearer token.",
)
def login(credentials: UserLogin, db: Session = Depends(get_db)):
    service = UserService(db)
    user, token = service.authenticate(
        email=credentials.email,
        password=credentials.password,
    )
    return TokenResponse(
        access_token=token,
        user=UserResponse.model_validate(user),
    )


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user profile",
    description="Returns the profile of the currently authenticated user.",
)
def get_profile(current_user: User = Depends(get_current_active_user)):
    return current_user
