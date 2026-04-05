"""
Pydantic schemas for User-related API requests and responses.

Handles input validation, serialization, and ensures sensitive fields
like passwords are never exposed in API responses.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


class RoleEnum(str, Enum):
    """Valid user roles for the system."""
    viewer = "viewer"
    analyst = "analyst"
    admin = "admin"


# ─── Request Schemas ─────────────────────────────────────────────

class UserCreate(BaseModel):
    """Schema for user registration."""
    name: str = Field(..., min_length=1, max_length=100, description="Full name")
    email: EmailStr = Field(..., description="Unique email address")
    password: str = Field(..., min_length=6, max_length=128, description="Password (min 6 chars)")
    role: RoleEnum = Field(default=RoleEnum.viewer, description="User role")

    @field_validator("name")
    @classmethod
    def name_must_not_be_blank(cls, v):
        if not v.strip():
            raise ValueError("Name cannot be blank")
        return v.strip()


class UserLogin(BaseModel):
    """Schema for user login."""
    email: EmailStr = Field(..., description="Registered email")
    password: str = Field(..., min_length=1, description="Account password")


class UserUpdate(BaseModel):
    """Schema for admin to update user details."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    role: Optional[RoleEnum] = None
    is_active: Optional[bool] = None

    @field_validator("name")
    @classmethod
    def name_must_not_be_blank(cls, v):
        if v is not None and not v.strip():
            raise ValueError("Name cannot be blank")
        return v.strip() if v else v


# ─── Response Schemas ────────────────────────────────────────────

class UserResponse(BaseModel):
    """Schema for user data in API responses (no password)."""
    id: int
    name: str
    email: str
    role: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    """Schema for login response containing JWT token."""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class MessageResponse(BaseModel):
    """Generic message response."""
    message: str
    detail: Optional[str] = None
