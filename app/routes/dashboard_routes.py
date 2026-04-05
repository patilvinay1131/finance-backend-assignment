"""
Dashboard routes — aggregated analytics and summary endpoints.

Thin HTTP handlers that delegate to FinanceService for all analytics logic.
All authenticated users can access these endpoints.
"""

from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.finance_schema import (
    DashboardSummary,
    CategoryBreakdown,
    CategorySummaryResponse,
    MonthlyTrend,
    TrendsResponse,
    RecentRecordResponse,
)
from app.services.finance_service import FinanceService
from app.utils.security import RoleChecker

router = APIRouter(prefix="/api/v1/dashboard", tags=["Dashboard & Analytics"])

# All authenticated users can access dashboard
require_any_role = RoleChecker(["viewer", "analyst", "admin"])


@router.get(
    "/summary",
    response_model=DashboardSummary,
    summary="Financial overview",
    description="Returns total income, total expenses, net balance, and record count.",
)
def get_summary(
    current_user: User = Depends(require_any_role),
    db: Session = Depends(get_db),
):
    service = FinanceService(db)
    data = service.get_summary()
    return DashboardSummary(**data)


@router.get(
    "/category-summary",
    response_model=CategorySummaryResponse,
    summary="Category-wise breakdown",
    description="Returns income and expense totals grouped by category.",
)
def get_category_summary(
    current_user: User = Depends(require_any_role),
    db: Session = Depends(get_db),
):
    service = FinanceService(db)
    categories = service.get_category_summary()
    return CategorySummaryResponse(
        categories=[CategoryBreakdown(**c) for c in categories]
    )


@router.get(
    "/trends",
    response_model=TrendsResponse,
    summary="Monthly income/expense trends",
    description="Returns monthly income and expense totals. Default: last 12 months.",
)
def get_trends(
    months: int = Query(12, ge=1, le=60, description="Number of months to look back"),
    current_user: User = Depends(require_any_role),
    db: Session = Depends(get_db),
):
    service = FinanceService(db)
    trends = service.get_monthly_trends(months=months)
    return TrendsResponse(trends=[MonthlyTrend(**t) for t in trends])


@router.get(
    "/recent",
    response_model=List[RecentRecordResponse],
    summary="Recent transactions",
    description="Returns the most recent financial records. Default: last 10.",
)
def get_recent_activity(
    limit: int = Query(10, ge=1, le=50, description="Number of recent records"),
    current_user: User = Depends(require_any_role),
    db: Session = Depends(get_db),
):
    service = FinanceService(db)
    records = service.get_recent_records(limit=limit)
    return [
        RecentRecordResponse(
            id=r.id,
            amount=r.amount,
            record_type=r.type,
            category=r.category,
            record_date=r.date,
            notes=r.notes,
            created_at=r.created_at,
        )
        for r in records
    ]
