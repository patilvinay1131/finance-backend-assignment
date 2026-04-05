"""
Financial records routes — CRUD operations with role-based access control.

Thin HTTP handlers that delegate to FinanceService for all business logic.

Access control:
    - Viewers & Analysts: Can read records (list with filtering, get by ID)
    - Admins: Full CRUD (create, read, update, soft-delete)
"""

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.finance import FinanceRecord
from app.models.user import User
from app.schemas.finance_schema import (
    FinanceCreate,
    FinanceUpdate,
    FinanceResponse,
    PaginatedFinanceResponse,
)
from app.schemas.user_schema import MessageResponse
from app.services.finance_service import FinanceService
from app.utils.security import RoleChecker

router = APIRouter(prefix="/api/v1/records", tags=["Financial Records"])

# Role dependencies
require_any_role = RoleChecker(["viewer", "analyst", "admin"])
require_admin = RoleChecker(["admin"])


def _to_response(record: FinanceRecord) -> FinanceResponse:
    """Convert a FinanceRecord ORM object to a FinanceResponse schema."""
    return FinanceResponse(
        id=record.id,
        amount=record.amount,
        record_type=record.type,
        category=record.category,
        record_date=record.date,
        notes=record.notes,
        created_by=record.created_by,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


@router.post(
    "/",
    response_model=FinanceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a financial record",
    description="Admin-only. Create a new income or expense record.",
)
def create_record(
    record: FinanceCreate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    service = FinanceService(db)
    new_record = service.create_record(
        amount=record.amount,
        record_type=record.record_type.value,
        category=record.category,
        record_date=record.record_date,
        notes=record.notes,
        created_by=admin.id,
    )
    return _to_response(new_record)


@router.get(
    "/",
    response_model=PaginatedFinanceResponse,
    summary="List financial records",
    description="All authenticated users. Returns paginated records with optional filters.",
)
def list_records(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(10, ge=1, le=100, description="Results per page"),
    type: Optional[str] = Query(None, description="Filter by type: income or expense"),
    category: Optional[str] = Query(None, description="Filter by category"),
    date_from: Optional[date] = Query(None, description="Start date (inclusive)"),
    date_to: Optional[date] = Query(None, description="End date (inclusive)"),
    current_user: User = Depends(require_any_role),
    db: Session = Depends(get_db),
):
    service = FinanceService(db)
    result = service.list_records(
        page=page,
        per_page=per_page,
        type_filter=type,
        category_filter=category,
        date_from=date_from,
        date_to=date_to,
    )
    return PaginatedFinanceResponse(
        records=[_to_response(r) for r in result["records"]],
        total=result["total"],
        page=result["page"],
        per_page=result["per_page"],
        total_pages=result["total_pages"],
    )


@router.get(
    "/{record_id}",
    response_model=FinanceResponse,
    summary="Get a financial record by ID",
    description="All authenticated users. Returns a single record.",
)
def get_record(
    record_id: int,
    current_user: User = Depends(require_any_role),
    db: Session = Depends(get_db),
):
    service = FinanceService(db)
    return _to_response(service.get_record(record_id))


@router.put(
    "/{record_id}",
    response_model=FinanceResponse,
    summary="Update a financial record",
    description="Admin-only. Update any field of a financial record.",
)
def update_record(
    record_id: int,
    record_update: FinanceUpdate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    service = FinanceService(db)
    update_data = record_update.model_dump(exclude_unset=True, by_alias=False)
    record = service.update_record(record_id, update_data)
    return _to_response(record)


@router.delete(
    "/{record_id}",
    response_model=MessageResponse,
    summary="Delete a financial record (soft delete)",
    description="Admin-only. Marks the record as deleted. It will not appear in queries.",
)
def delete_record(
    record_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    service = FinanceService(db)
    service.soft_delete_record(record_id)
    return MessageResponse(
        message=f"Record {record_id} has been deleted",
        detail="Soft-deleted. Record is hidden from queries but preserved in the database.",
    )
