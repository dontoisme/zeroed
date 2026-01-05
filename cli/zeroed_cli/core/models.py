"""
SQLAlchemy models for Zeroed budget application.

Core entities:
- Account: Bank accounts, credit cards, cash
- CategoryGroup / Category: Budget hierarchy
- Transaction: Individual transactions
- Payee / PayeeMatchRule: Auto-categorization
- BudgetEntry: Monthly category allocations
- Goal: Savings targets
- ImportProfile: CSV format configurations
"""

from datetime import datetime, date
from typing import Optional, List
from decimal import Decimal
import enum
import hashlib

from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Date,
    ForeignKey, Text, Enum, UniqueConstraint, Index
)
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()


def utcnow_iso():
    """Return UTC now without microseconds for Prisma compatibility."""
    return datetime.utcnow().replace(microsecond=0)


class AccountType(enum.Enum):
    """Types of financial accounts."""
    CHECKING = "checking"
    SAVINGS = "savings"
    CREDIT_CARD = "credit_card"
    CASH = "cash"
    INVESTMENT = "investment"


class TransactionType(enum.Enum):
    """Transaction flow direction."""
    INFLOW = "inflow"
    OUTFLOW = "outflow"
    TRANSFER = "transfer"


class GoalType(enum.Enum):
    """Types of savings goals."""
    TARGET_BALANCE = "target_balance"      # Save X total
    TARGET_BY_DATE = "target_by_date"      # Save X by date
    MONTHLY_FUNDING = "monthly_funding"    # Save X per month
    SPENDING = "spending"                  # Budget X for spending


class MatchType(enum.Enum):
    """Types of payee matching rules."""
    CONTAINS = "contains"
    STARTS_WITH = "starts_with"
    EXACT = "exact"
    REGEX = "regex"


class Account(Base):
    """
    Financial accounts - bank accounts, credit cards, cash, etc.

    On-budget accounts affect your budget.
    Tracking accounts (is_on_budget=False) are for net worth only.
    """
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True)
    account_type = Column(Enum(AccountType), nullable=False)
    institution = Column(String(100))
    account_number_last4 = Column(String(4))

    # Balances
    current_balance = Column(Float, default=0)
    cleared_balance = Column(Float, default=0)

    # Budget tracking
    is_on_budget = Column(Boolean, default=True)
    is_closed = Column(Boolean, default=False)

    notes = Column(Text)
    created_at = Column(DateTime, default=utcnow_iso)
    updated_at = Column(DateTime, default=utcnow_iso, onupdate=utcnow_iso)

    # Relationships
    transactions = relationship(
        "Transaction",
        back_populates="account",
        foreign_keys="Transaction.account_id"
    )

    def __repr__(self):
        return f"<Account {self.name} ({self.account_type.value})>"

    def update_balance(self):
        """Recalculate balance from transactions."""
        total = sum(t.amount for t in self.transactions)
        self.current_balance = total
        self.cleared_balance = sum(
            t.amount for t in self.transactions if t.is_cleared
        )


class CategoryGroup(Base):
    """
    Groups of budget categories.

    Examples: Bills, Everyday, Savings Goals, Fun
    """
    __tablename__ = "category_groups"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True)
    sort_order = Column(Integer, default=0)
    is_hidden = Column(Boolean, default=False)
    created_at = Column(DateTime, default=utcnow_iso)

    # Relationships
    categories = relationship(
        "Category",
        back_populates="group",
        order_by="Category.sort_order"
    )

    def __repr__(self):
        return f"<CategoryGroup {self.name}>"


class Category(Base):
    """
    Budget categories within groups.

    Examples: Groceries, Rent, Entertainment
    """
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True)
    group_id = Column(Integer, ForeignKey("category_groups.id"), nullable=False)
    name = Column(String(100), nullable=False)
    sort_order = Column(Integer, default=0)
    is_hidden = Column(Boolean, default=False)
    notes = Column(Text)
    created_at = Column(DateTime, default=utcnow_iso)

    # Relationships
    group = relationship("CategoryGroup", back_populates="categories")
    transactions = relationship("Transaction", back_populates="category")
    budget_entries = relationship("BudgetEntry", back_populates="category")
    goal = relationship("Goal", back_populates="category", uselist=False)

    # Unique constraint on name within group
    __table_args__ = (
        UniqueConstraint('group_id', 'name', name='uq_category_group_name'),
    )

    def __repr__(self):
        return f"<Category {self.group.name}: {self.name}>"


class Payee(Base):
    """
    Merchants/payees with optional default category for auto-categorization.
    """
    __tablename__ = "payees"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False, unique=True)
    default_category_id = Column(Integer, ForeignKey("categories.id"))
    auto_categorize = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utcnow_iso)

    # Relationships
    transactions = relationship("Transaction", back_populates="payee")
    default_category = relationship("Category")
    match_rules = relationship("PayeeMatchRule", back_populates="payee", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Payee {self.name}>"


class PayeeMatchRule(Base):
    """
    Rules for matching imported payee names to canonical payees.

    Used for auto-categorization during import.
    """
    __tablename__ = "payee_match_rules"

    id = Column(Integer, primary_key=True)
    payee_id = Column(Integer, ForeignKey("payees.id"), nullable=False)
    pattern = Column(String(255), nullable=False)
    match_type = Column(Enum(MatchType), default=MatchType.CONTAINS)
    priority = Column(Integer, default=0)  # Higher = checked first

    # Relationships
    payee = relationship("Payee", back_populates="match_rules")

    __table_args__ = (
        Index('ix_payee_match_rules_priority', 'priority'),
    )

    def __repr__(self):
        return f"<PayeeMatchRule {self.match_type.value}: '{self.pattern}' -> {self.payee.name}>"


class Transaction(Base):
    """
    Individual financial transactions.
    """
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"))
    payee_id = Column(Integer, ForeignKey("payees.id"))
    transfer_account_id = Column(Integer, ForeignKey("accounts.id"))

    # Transaction details
    date = Column(Date, nullable=False, index=True)
    amount = Column(Float, nullable=False)  # Positive = inflow, Negative = outflow
    transaction_type = Column(Enum(TransactionType), nullable=False)

    memo = Column(String(500))
    is_cleared = Column(Boolean, default=False)
    is_reconciled = Column(Boolean, default=False)

    # Import tracking for deduplication
    import_id = Column(String(100), unique=True, index=True)
    import_source = Column(String(50))  # Which CSV format/bank
    raw_payee_name = Column(String(255))  # Original from import

    created_at = Column(DateTime, default=utcnow_iso)
    updated_at = Column(DateTime, default=utcnow_iso, onupdate=utcnow_iso)

    # Relationships
    account = relationship(
        "Account",
        back_populates="transactions",
        foreign_keys=[account_id]
    )
    transfer_account = relationship("Account", foreign_keys=[transfer_account_id])
    category = relationship("Category", back_populates="transactions")
    payee = relationship("Payee", back_populates="transactions")

    __table_args__ = (
        Index('ix_transactions_date_account', 'date', 'account_id'),
        Index('ix_transactions_category', 'category_id'),
    )

    def __repr__(self):
        return f"<Transaction {self.date} ${self.amount:.2f} {self.payee.name if self.payee else 'Unknown'}>"

    @staticmethod
    def generate_import_id(account_id: int, date: date, amount: float, payee_name: str) -> str:
        """Generate unique ID for deduplication during import."""
        data = f"{account_id}:{date.isoformat()}:{amount:.2f}:{payee_name}"
        return hashlib.md5(data.encode()).hexdigest()


class BudgetEntry(Base):
    """
    Monthly budget allocation for a category.

    One entry per category per month.
    """
    __tablename__ = "budget_entries"

    id = Column(Integer, primary_key=True)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    month = Column(Date, nullable=False)  # First day of month
    budgeted = Column(Float, default=0)

    created_at = Column(DateTime, default=utcnow_iso)
    updated_at = Column(DateTime, default=utcnow_iso, onupdate=utcnow_iso)

    # Relationships
    category = relationship("Category", back_populates="budget_entries")

    __table_args__ = (
        UniqueConstraint('category_id', 'month', name='uq_budget_category_month'),
        Index('ix_budget_entries_month', 'month'),
    )

    def __repr__(self):
        return f"<BudgetEntry {self.month.strftime('%Y-%m')} {self.category.name}: ${self.budgeted:.2f}>"


class Goal(Base):
    """
    Savings goals attached to categories.

    Goal types:
    - TARGET_BALANCE: Save X total amount
    - TARGET_BY_DATE: Save X by a specific date
    - MONTHLY_FUNDING: Save X every month
    - SPENDING: Budget X for spending
    """
    __tablename__ = "goals"

    id = Column(Integer, primary_key=True)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False, unique=True)
    goal_type = Column(Enum(GoalType), nullable=False)

    target_amount = Column(Float)  # For TARGET_BALANCE, TARGET_BY_DATE
    target_date = Column(Date)  # For TARGET_BY_DATE
    monthly_funding = Column(Float)  # For MONTHLY_FUNDING

    created_at = Column(DateTime, default=utcnow_iso)
    updated_at = Column(DateTime, default=utcnow_iso, onupdate=utcnow_iso)

    # Relationships
    category = relationship("Category", back_populates="goal")

    def __repr__(self):
        return f"<Goal {self.category.name} ({self.goal_type.value})>"


class ImportProfile(Base):
    """
    CSV import configuration profiles for different banks.

    Stores column mappings and parsing options.
    """
    __tablename__ = "import_profiles"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True)
    institution = Column(String(100))

    # Column mappings
    date_column = Column(String(50))
    date_format = Column(String(50), default="%m/%d/%Y")
    amount_column = Column(String(50))
    amount_inflow_column = Column(String(50))  # Some CSVs split in/out
    amount_outflow_column = Column(String(50))
    payee_column = Column(String(50))
    memo_column = Column(String(50))

    # Processing options
    skip_header_rows = Column(Integer, default=1)
    amount_multiplier = Column(Float, default=1.0)  # -1 to invert

    created_at = Column(DateTime, default=utcnow_iso)

    def __repr__(self):
        return f"<ImportProfile {self.name} ({self.institution})>"


# Default category structure for YNAB-style setup
DEFAULT_CATEGORIES = {
    "Bills": [
        "Rent/Mortgage",
        "Electric",
        "Internet",
        "Phone",
        "Insurance",
    ],
    "Everyday": [
        "Groceries",
        "Dining Out",
        "Transportation",
        "Gas",
    ],
    "Fun": [
        "Entertainment",
        "Hobbies",
        "Subscriptions",
    ],
    "Savings Goals": [
        "Emergency Fund",
        "Vacation",
        "Big Purchases",
    ],
    "Giving": [
        "Charity",
        "Gifts",
    ],
}
