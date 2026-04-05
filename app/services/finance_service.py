"""
Finance service — encapsulates all business logic for financial records.

Separates data access patterns, business rules, and aggregation logic
from the HTTP layer. Each method is independently testable.
"""

from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import func, extract, case
from sqlalchemy.orm import Session

from app.models.finance import FinanceRecord


class FinanceService:
    """Handles financial record CRUD and dashboard analytics."""

    def __init__(self, db: Session):
        self.db = db

    # ─── Helper: Active records query ────────────────────────────

    def _active_records(self):
        """Base query that excludes soft-deleted records."""
        return self.db.query(FinanceRecord).filter(FinanceRecord.is_deleted == False)

    def _get_record_or_404(self, record_id: int) -> FinanceRecord:
        """Fetch a single active record by ID. Raises 404 if not found."""
        record = self._active_records().filter(FinanceRecord.id == record_id).first()
        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Record with id {record_id} not found",
            )
        return record

    # ─── CRUD Operations ─────────────────────────────────────────

    def create_record(
        self,
        amount: float,
        record_type: str,
        category: str,
        record_date: date,
        notes: str,
        created_by: int,
    ) -> FinanceRecord:
        """Create a new financial record. Validates type before insertion."""
        record = FinanceRecord(
            amount=amount,
            type=record_type,
            category=category,
            date=record_date,
            notes=notes,
            created_by=created_by,
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def get_record(self, record_id: int) -> FinanceRecord:
        """Get a single record by ID."""
        return self._get_record_or_404(record_id)

    def list_records(
        self,
        page: int = 1,
        per_page: int = 10,
        type_filter: Optional[str] = None,
        category_filter: Optional[str] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> dict:
        """
        List records with optional filters and pagination.

        Filters:
            - type_filter: 'income' or 'expense'
            - category_filter: partial match (case-insensitive)
            - date_from / date_to: inclusive date range

        Business rules:
            - date_from must be <= date_to when both are provided
            - type_filter must be 'income' or 'expense'
        """
        query = self._active_records()

        # Validate and apply type filter
        if type_filter:
            if type_filter not in ("income", "expense"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Type must be 'income' or 'expense'",
                )
            query = query.filter(FinanceRecord.type == type_filter)

        # Category: case-insensitive partial match
        if category_filter:
            query = query.filter(FinanceRecord.category.ilike(f"%{category_filter}%"))

        # Date range
        if date_from:
            query = query.filter(FinanceRecord.date >= date_from)
        if date_to:
            query = query.filter(FinanceRecord.date <= date_to)
        if date_from and date_to and date_from > date_to:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="date_from must be before or equal to date_to",
            )

        # Pagination
        total = query.count()
        total_pages = max(1, (total + per_page - 1) // per_page)

        records = (
            query.order_by(FinanceRecord.date.desc(), FinanceRecord.created_at.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )

        return {
            "records": records,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages,
        }

    def update_record(self, record_id: int, update_data: dict) -> FinanceRecord:
        """
        Update fields of an existing record.
        Only non-None fields in update_data are applied.
        """
        record = self._get_record_or_404(record_id)

        # Map schema field names → model field names
        field_mapping = {"record_type": "type", "record_date": "date"}

        for field, value in update_data.items():
            model_field = field_mapping.get(field, field)
            if model_field == "type" and value is not None:
                setattr(record, model_field, value.value if hasattr(value, "value") else value)
            else:
                setattr(record, model_field, value)

        self.db.commit()
        self.db.refresh(record)
        return record

    def soft_delete_record(self, record_id: int) -> FinanceRecord:
        """
        Soft-delete a record — marks is_deleted=True.

        The record is preserved in the database for audit purposes
        but will be excluded from all queries and analytics.
        """
        record = self._get_record_or_404(record_id)
        record.is_deleted = True
        self.db.commit()
        return record

    # ─── Dashboard Analytics ─────────────────────────────────────

    def get_summary(self) -> dict:
        """
        Compute overall financial summary.

        Returns total income, total expenses, net balance, and record count.
        Only non-deleted records are considered.
        """
        base = self._active_records()

        total_income = (
            base.filter(FinanceRecord.type == "income")
            .with_entities(func.coalesce(func.sum(FinanceRecord.amount), 0))
            .scalar()
        )

        total_expenses = (
            base.filter(FinanceRecord.type == "expense")
            .with_entities(func.coalesce(func.sum(FinanceRecord.amount), 0))
            .scalar()
        )

        total_records = base.count()

        return {
            "total_income": round(total_income, 2),
            "total_expenses": round(total_expenses, 2),
            "net_balance": round(total_income - total_expenses, 2),
            "total_records": total_records,
        }

    def get_category_summary(self) -> list[dict]:
        """
        Aggregate income and expense totals per category.

        Uses SQL conditional aggregation (CASE WHEN) for efficiency —
        a single query instead of N+1 queries per category.
        """
        results = (
            self.db.query(
                FinanceRecord.category,
                func.coalesce(
                    func.sum(case((FinanceRecord.type == "income", FinanceRecord.amount), else_=0)),
                    0,
                ).label("total_income"),
                func.coalesce(
                    func.sum(case((FinanceRecord.type == "expense", FinanceRecord.amount), else_=0)),
                    0,
                ).label("total_expense"),
            )
            .filter(FinanceRecord.is_deleted == False)
            .group_by(FinanceRecord.category)
            .order_by(FinanceRecord.category)
            .all()
        )

        return [
            {
                "category": row.category,
                "total_income": round(row.total_income, 2),
                "total_expense": round(row.total_expense, 2),
                "net": round(row.total_income - row.total_expense, 2),
            }
            for row in results
        ]

    def get_monthly_trends(self, months: int = 12) -> list[dict]:
        """
        Compute monthly income/expense trends.

        Groups records by year-month and calculates running totals.
        Default lookback period is 12 months.
        """
        cutoff_date = (datetime.utcnow() - timedelta(days=months * 30)).date()

        results = (
            self.db.query(
                extract("year", FinanceRecord.date).label("year"),
                extract("month", FinanceRecord.date).label("month"),
                func.coalesce(
                    func.sum(case((FinanceRecord.type == "income", FinanceRecord.amount), else_=0)),
                    0,
                ).label("income"),
                func.coalesce(
                    func.sum(case((FinanceRecord.type == "expense", FinanceRecord.amount), else_=0)),
                    0,
                ).label("expense"),
            )
            .filter(FinanceRecord.is_deleted == False, FinanceRecord.date >= cutoff_date)
            .group_by("year", "month")
            .order_by("year", "month")
            .all()
        )

        return [
            {
                "month": f"{int(row.year)}-{int(row.month):02d}",
                "income": round(row.income, 2),
                "expense": round(row.expense, 2),
                "net": round(row.income - row.expense, 2),
            }
            for row in results
        ]

    def get_recent_records(self, limit: int = 10) -> list[FinanceRecord]:
        """Return the N most recent non-deleted records, ordered by date."""
        return (
            self._active_records()
            .order_by(FinanceRecord.date.desc(), FinanceRecord.created_at.desc())
            .limit(limit)
            .all()
        )
