"""
User management routes — admin-only endpoints for managing users.

Thin HTTP handlers that delegate to UserService for all business logic.
All endpoints require the admin role.
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.user_schema import UserResponse, UserUpdate, MessageResponse
from app.services.user_service import UserService
from app.utils.security import RoleChecker

router = APIRouter(prefix="/api/v1/users", tags=["User Management"])

# All routes in this module require admin role
require_admin = RoleChecker(["admin"])


@router.get(
    "/",
    response_model=dict,
    summary="List all users",
    description="Admin-only. Returns a paginated list of all users in the system.",
)
def list_users(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(10, ge=1, le=100, description="Results per page"),
    role: Optional[str] = Query(None, description="Filter by role"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    service = UserService(db)
    result = service.list_users(
        page=page,
        per_page=per_page,
        role_filter=role,
        active_filter=is_active,
    )
    result["users"] = [UserResponse.model_validate(u) for u in result["users"]]
    return result


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    summary="Get user by ID",
    description="Admin-only. Returns details of a specific user.",
)
def get_user(
    user_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    service = UserService(db)
    return service.get_user_by_id(user_id)


@router.put(
    "/{user_id}",
    response_model=UserResponse,
    summary="Update user",
    description="Admin-only. Update a user's name, role, or active status.",
)
def update_user(
    user_id: int,
    user_update: UserUpdate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    service = UserService(db)
    update_data = user_update.model_dump(exclude_unset=True)
    return service.update_user(user_id, admin_id=admin.id, update_data=update_data)


@router.patch(
    "/{user_id}/deactivate",
    response_model=MessageResponse,
    summary="Deactivate user",
    description="Admin-only. Deactivate a user account (soft disable).",
)
def deactivate_user(
    user_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    service = UserService(db)
    user = service.set_active_status(user_id, admin_id=admin.id, active=False)
    return MessageResponse(message=f"User '{user.email}' has been deactivated")


@router.patch(
    "/{user_id}/activate",
    response_model=MessageResponse,
    summary="Activate user",
    description="Admin-only. Reactivate a previously deactivated user account.",
)
def activate_user(
    user_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    service = UserService(db)
    user = service.set_active_status(user_id, admin_id=admin.id, active=True)
    return MessageResponse(message=f"User '{user.email}' has been activated")
