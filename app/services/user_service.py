"""
User service — encapsulates all business logic related to user management.

This layer sits between routes (HTTP) and models (database) to ensure:
    - Business rules are enforced in one place
    - Route handlers remain thin and focused on HTTP concerns
    - Logic is testable independently of the web framework
"""

from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.user import User
from app.utils.security import hash_password, verify_password, create_token


class UserService:
    """Handles user registration, authentication, and admin management."""

    def __init__(self, db: Session):
        self.db = db

    # ─── Authentication ──────────────────────────────────────────

    def register(self, name: str, email: str, password: str, role: str) -> User:
        """
        Register a new user account.

        Business rules:
            - Email must be unique across the system
            - Password is hashed with bcrypt before storage
            - Default role is 'viewer' if not specified
        """
        existing = self.db.query(User).filter(User.email == email).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Email '{email}' is already registered",
            )

        user = User(
            name=name,
            email=email,
            hashed_password=hash_password(password),
            role=role,
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def authenticate(self, email: str, password: str) -> tuple[User, str]:
        """
        Authenticate user credentials and issue a JWT token.

        Business rules:
            - User must exist and password must match
            - Deactivated accounts cannot log in
            - Token includes user_id and role for downstream authorization

        Returns:
            Tuple of (user, access_token)
        """
        user = self.db.query(User).filter(User.email == email).first()

        if not user or not verify_password(password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is deactivated. Contact an administrator.",
            )

        token = create_token({"user_id": user.id, "role": user.role})
        return user, token

    # ─── Admin User Management ───────────────────────────────────

    def list_users(
        self,
        page: int = 1,
        per_page: int = 10,
        role_filter: Optional[str] = None,
        active_filter: Optional[bool] = None,
    ) -> dict:
        """Return a paginated, filtered list of all users."""
        query = self.db.query(User)

        if role_filter:
            query = query.filter(User.role == role_filter)
        if active_filter is not None:
            query = query.filter(User.is_active == active_filter)

        total = query.count()
        total_pages = max(1, (total + per_page - 1) // per_page)

        users = (
            query.order_by(User.created_at.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )

        return {
            "users": users,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages,
        }

    def get_user_by_id(self, user_id: int) -> User:
        """Fetch a single user by ID. Raises 404 if not found."""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with id {user_id} not found",
            )
        return user

    def update_user(self, user_id: int, admin_id: int, update_data: dict) -> User:
        """
        Update a user's profile (admin operation).

        Business rules:
            - Admins cannot deactivate their own account (prevents lockout)
            - Admins cannot change their own role (prevents privilege loss)
        """
        user = self.get_user_by_id(user_id)

        if user.id == admin_id and update_data.get("is_active") is False:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You cannot deactivate your own account",
            )

        if user.id == admin_id and "role" in update_data and update_data["role"] is not None:
            new_role = update_data["role"]
            if hasattr(new_role, "value"):
                new_role = new_role.value
            if new_role != user.role:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="You cannot change your own role",
                )

        for field, value in update_data.items():
            if field == "role" and value is not None:
                setattr(user, field, value.value if hasattr(value, "value") else value)
            else:
                setattr(user, field, value)

        self.db.commit()
        self.db.refresh(user)
        return user

    def set_active_status(self, user_id: int, admin_id: int, active: bool) -> User:
        """
        Activate or deactivate a user account.

        Business rules:
            - Admin cannot change their own active status
            - Already-matching status raises a 400
        """
        user = self.get_user_by_id(user_id)

        if user.id == admin_id:
            action = "deactivate" if not active else "activate"
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"You cannot {action} your own account",
            )

        if user.is_active == active:
            state = "active" if active else "deactivated"
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"User is already {state}",
            )

        user.is_active = active
        self.db.commit()
        return user
