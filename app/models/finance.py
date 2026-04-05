"""
FinanceRecord model — stores individual financial transactions/entries.

Each record is associated with a user (created_by) and supports soft deletion.
Fields like type (income/expense) and category enable filtering and analytics.
"""

from datetime import datetime, date as date_type

from sqlalchemy import Column, Integer, String, Float, Date, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base


class FinanceRecord(Base):
    __tablename__ = "finance_records"

    id = Column(Integer, primary_key=True, index=True)
    amount = Column(Float, nullable=False)
    type = Column(String(20), nullable=False, index=True)       # income | expense
    category = Column(String(100), nullable=False, index=True)  # e.g. salary, rent, groceries
    date = Column(Date, nullable=False, index=True)
    notes = Column(String(500), nullable=True, default="")

    # Ownership and audit trail
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)  # Soft delete flag
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationship back to user
    creator = relationship("User", back_populates="records")

    def __repr__(self):
        return f"<FinanceRecord(id={self.id}, type='{self.type}', amount={self.amount})>"
