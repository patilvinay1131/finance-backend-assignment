"""
Pydantic schemas for Finance-related API requests and responses.

Includes validation for record types (income/expense), positive amounts,
and structured response schemas for dashboard analytics.

Note: Fields use aliases where needed to avoid Python keyword conflicts
(e.g., 'type' and 'date' are valid JSON field names but need careful handling).
"""

from __future__ import annotations

from datetime import date as DateType, datetime
from enum import Enum
from typing import Optional, List

from pydantic import BaseModel, Field, field_validator


class RecordType(str, Enum):
    """Valid financial record types."""
    income = "income"
    expense = "expense"


# ─── Request Schemas ─────────────────────────────────────────────

class FinanceCreate(BaseModel):
    """Schema for creating a new financial record."""
    amount: float = Field(..., gt=0, description="Transaction amount (must be positive)")
    record_type: RecordType = Field(..., alias="type", description="Record type: income or expense")
    category: str = Field(..., min_length=1, max_length=100, description="Category name")
    record_date: DateType = Field(..., alias="date", description="Transaction date (YYYY-MM-DD)")
    notes: Optional[str] = Field(default="", max_length=500, description="Optional notes")

    model_config = {"populate_by_name": True}

    @field_validator("category")
    @classmethod
    def category_must_not_be_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Category cannot be blank")
        return v.strip()

    @field_validator("notes")
    @classmethod
    def clean_notes(cls, v: Optional[str]) -> str:
        return v.strip() if v else ""


class FinanceUpdate(BaseModel):
    """Schema for updating an existing financial record. All fields optional."""
    amount: Optional[float] = Field(None, gt=0, description="Transaction amount")
    record_type: Optional[RecordType] = Field(None, alias="type", description="Record type")
    category: Optional[str] = Field(None, min_length=1, max_length=100)
    record_date: Optional[DateType] = Field(None, alias="date")
    notes: Optional[str] = Field(None, max_length=500)

    model_config = {"populate_by_name": True}

    @field_validator("category")
    @classmethod
    def category_must_not_be_blank(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.strip():
            raise ValueError("Category cannot be blank")
        return v.strip() if v else v


# ─── Response Schemas ────────────────────────────────────────────

class FinanceResponse(BaseModel):
    """Schema for a single financial record in API responses."""
    id: int
    amount: float
    record_type: str = Field(alias="type")
    category: str
    record_date: DateType = Field(alias="date")
    notes: Optional[str]
    created_by: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True, "populate_by_name": True}


class PaginatedFinanceResponse(BaseModel):
    """Paginated list of finance records."""
    records: List[FinanceResponse]
    total: int
    page: int
    per_page: int
    total_pages: int


# ─── Dashboard Response Schemas ──────────────────────────────────

class DashboardSummary(BaseModel):
    """Overall financial summary."""
    total_income: float
    total_expenses: float
    net_balance: float
    total_records: int


class CategoryBreakdown(BaseModel):
    """Income/expense totals for a single category."""
    category: str
    total_income: float
    total_expense: float
    net: float


class CategorySummaryResponse(BaseModel):
    """Category-wise financial breakdown."""
    categories: List[CategoryBreakdown]


class MonthlyTrend(BaseModel):
    """Income/expense data for a single month."""
    month: str  # Format: "YYYY-MM"
    income: float
    expense: float
    net: float


class TrendsResponse(BaseModel):
    """Monthly trends over time."""
    trends: List[MonthlyTrend]


class RecentRecordResponse(BaseModel):
    """A recent transaction for the activity feed."""
    id: int
    amount: float
    record_type: str = Field(alias="type")
    category: str
    record_date: DateType = Field(alias="date")
    notes: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True, "populate_by_name": True}
