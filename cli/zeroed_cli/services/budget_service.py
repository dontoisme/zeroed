"""
Budget service implementing zero-based budgeting logic.

Core YNAB principles:
1. Give every dollar a job
2. Embrace your true expenses
3. Roll with the punches
4. Age your money
"""

from datetime import date
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..core.models import (
    Account, Category, CategoryGroup, Transaction,
    BudgetEntry, Goal, GoalType
)


class BudgetService:
    """
    Zero-based budgeting logic.

    Handles:
    - Ready to Assign calculation
    - Category available balances
    - Budget suggestions based on spending history
    - Goal progress tracking
    """

    def __init__(self, session: Session):
        self.session = session

    def get_ready_to_assign(self, month: date) -> float:
        """
        Calculate 'Ready to Assign' (available to budget).

        = Total income (inflows to budget accounts)
        - Total budgeted amounts
        + Carryover from previous months
        """
        month_start = date(month.year, month.month, 1)

        # Get next month start
        if month.month == 12:
            next_month = date(month.year + 1, 1, 1)
        else:
            next_month = date(month.year, month.month + 1, 1)

        # Total inflows this month (income)
        inflows = (
            self.session.query(func.coalesce(func.sum(Transaction.amount), 0))
            .join(Account, Transaction.account_id == Account.id)
            .filter(Account.is_on_budget == True)
            .filter(Transaction.amount > 0)
            .filter(Transaction.date >= month_start)
            .filter(Transaction.date < next_month)
            .scalar()
        ) or 0

        # Total budgeted this month
        budgeted = (
            self.session.query(func.coalesce(func.sum(BudgetEntry.budgeted), 0))
            .filter(BudgetEntry.month == month_start)
            .scalar()
        ) or 0

        # Previous month carryover (unspent from all previous months)
        carryover = self._get_total_carryover(month_start)

        return inflows + carryover - budgeted

    def _get_total_carryover(self, month_start: date) -> float:
        """
        Get total unspent/overspent from all previous months.

        This is the cumulative available balance.
        """
        # Sum all historical budgeted amounts
        total_budgeted = (
            self.session.query(func.coalesce(func.sum(BudgetEntry.budgeted), 0))
            .filter(BudgetEntry.month < month_start)
            .scalar()
        ) or 0

        # Sum all historical inflows
        total_inflows = (
            self.session.query(func.coalesce(func.sum(Transaction.amount), 0))
            .join(Account, Transaction.account_id == Account.id)
            .filter(Account.is_on_budget == True)
            .filter(Transaction.amount > 0)
            .filter(Transaction.date < month_start)
            .scalar()
        ) or 0

        # Sum all historical outflows (negative)
        total_outflows = (
            self.session.query(func.coalesce(func.sum(Transaction.amount), 0))
            .join(Account, Transaction.account_id == Account.id)
            .filter(Account.is_on_budget == True)
            .filter(Transaction.amount < 0)
            .filter(Transaction.date < month_start)
            .scalar()
        ) or 0

        # Carryover = historical inflows + outflows - historical budgeted
        # (outflows are already negative)
        return total_inflows + total_outflows - total_budgeted

    def _get_category_available(self, category_id: int, month: date) -> float:
        """
        Calculate available balance for a category in a month.

        Available = Budgeted this month + Activity this month + Carryover
        """
        month_start = date(month.year, month.month, 1)

        # Get budgeted amount this month
        entry = (
            self.session.query(BudgetEntry)
            .filter(BudgetEntry.category_id == category_id)
            .filter(BudgetEntry.month == month_start)
            .first()
        )
        budgeted = entry.budgeted if entry else 0

        # Get activity (spending) this month
        if month.month == 12:
            next_month = date(month.year + 1, 1, 1)
        else:
            next_month = date(month.year, month.month + 1, 1)

        activity = (
            self.session.query(func.coalesce(func.sum(Transaction.amount), 0))
            .filter(Transaction.category_id == category_id)
            .filter(Transaction.date >= month_start)
            .filter(Transaction.date < next_month)
            .scalar()
        ) or 0

        # Get carryover (cumulative from all previous months)
        prev_budgeted = (
            self.session.query(func.coalesce(func.sum(BudgetEntry.budgeted), 0))
            .filter(BudgetEntry.category_id == category_id)
            .filter(BudgetEntry.month < month_start)
            .scalar()
        ) or 0

        prev_activity = (
            self.session.query(func.coalesce(func.sum(Transaction.amount), 0))
            .filter(Transaction.category_id == category_id)
            .filter(Transaction.date < month_start)
            .scalar()
        ) or 0

        carryover = prev_budgeted + prev_activity

        return budgeted + activity + carryover

    def get_month_budget(self, month: date) -> Dict[str, Any]:
        """Get full budget view for a month."""
        month_start = date(month.year, month.month, 1)

        if month.month == 12:
            next_month = date(month.year + 1, 1, 1)
        else:
            next_month = date(month.year, month.month + 1, 1)

        groups = []
        for group in (
            self.session.query(CategoryGroup)
            .filter(CategoryGroup.is_hidden == False)
            .order_by(CategoryGroup.sort_order)
        ):
            categories = []
            for cat in (
                self.session.query(Category)
                .filter(Category.group_id == group.id)
                .filter(Category.is_hidden == False)
                .order_by(Category.sort_order)
            ):
                # Get budget entry
                entry = (
                    self.session.query(BudgetEntry)
                    .filter(BudgetEntry.category_id == cat.id)
                    .filter(BudgetEntry.month == month_start)
                    .first()
                )
                budgeted = entry.budgeted if entry else 0

                # Get activity this month
                activity = (
                    self.session.query(func.coalesce(func.sum(Transaction.amount), 0))
                    .filter(Transaction.category_id == cat.id)
                    .filter(Transaction.date >= month_start)
                    .filter(Transaction.date < next_month)
                    .scalar()
                ) or 0

                available = self._get_category_available(cat.id, month)

                # Goal progress
                goal_info = None
                if cat.goal:
                    goal_info = self._calculate_goal_progress(cat.goal, month, available)

                categories.append({
                    "id": cat.id,
                    "name": cat.name,
                    "budgeted": budgeted,
                    "activity": activity,
                    "available": available,
                    "goal": goal_info
                })

            groups.append({
                "id": group.id,
                "name": group.name,
                "categories": categories
            })

        return {
            "month": month_start.isoformat(),
            "ready_to_assign": self.get_ready_to_assign(month),
            "groups": groups
        }

    def set_category_budget(
        self,
        category_name: str,
        month: date,
        amount: float
    ) -> BudgetEntry:
        """Set or update budget for a category."""
        month_start = date(month.year, month.month, 1)

        category = (
            self.session.query(Category)
            .filter(Category.name.ilike(f"%{category_name}%"))
            .first()
        )

        if not category:
            raise ValueError(f"Category not found: {category_name}")

        entry = (
            self.session.query(BudgetEntry)
            .filter(BudgetEntry.category_id == category.id)
            .filter(BudgetEntry.month == month_start)
            .first()
        )

        if entry:
            entry.budgeted = amount
        else:
            entry = BudgetEntry(
                category_id=category.id,
                month=month_start,
                budgeted=amount
            )
            self.session.add(entry)

        return entry

    def suggest_budgets(self, month: date, lookback_months: int = 3) -> List[Dict[str, Any]]:
        """
        Suggest budget amounts based on average spending.

        Looks at the last N months of spending per category.
        """
        month_start = date(month.year, month.month, 1)

        # Calculate lookback start
        lookback_year = month.year
        lookback_month = month.month - lookback_months
        while lookback_month <= 0:
            lookback_month += 12
            lookback_year -= 1
        lookback_start = date(lookback_year, lookback_month, 1)

        suggestions = []

        for cat in self.session.query(Category).filter(Category.is_hidden == False):
            # Get average spending in lookback period
            total_spending = (
                self.session.query(func.coalesce(func.sum(Transaction.amount), 0))
                .filter(Transaction.category_id == cat.id)
                .filter(Transaction.amount < 0)  # Only outflows
                .filter(Transaction.date >= lookback_start)
                .filter(Transaction.date < month_start)
                .scalar()
            ) or 0

            # Average (spending is negative, so negate to get positive suggestion)
            avg_spending = abs(total_spending) / lookback_months if total_spending else 0

            if avg_spending > 0:
                # Get current budget
                current_entry = (
                    self.session.query(BudgetEntry)
                    .filter(BudgetEntry.category_id == cat.id)
                    .filter(BudgetEntry.month == month_start)
                    .first()
                )
                current = current_entry.budgeted if current_entry else 0

                suggestions.append({
                    "category": cat.name,
                    "category_id": cat.id,
                    "suggested": round(avg_spending, 2),
                    "current": current
                })

        # Sort by suggested amount descending
        suggestions.sort(key=lambda x: x["suggested"], reverse=True)

        return suggestions

    def _calculate_goal_progress(
        self,
        goal: Goal,
        month: date,
        available: float
    ) -> Dict[str, Any]:
        """Calculate goal progress."""
        month_start = date(month.year, month.month, 1)

        if goal.goal_type == GoalType.TARGET_BALANCE:
            progress = (available / goal.target_amount) * 100 if goal.target_amount else 0
            return {
                "type": "target_balance",
                "target": goal.target_amount,
                "saved": available,
                "progress": min(100, max(0, progress)),
                "remaining": max(0, goal.target_amount - available) if goal.target_amount else 0
            }

        elif goal.goal_type == GoalType.TARGET_BY_DATE:
            progress = (available / goal.target_amount) * 100 if goal.target_amount else 0
            months_remaining = self._months_between(month_start, goal.target_date)
            remaining = max(0, goal.target_amount - available) if goal.target_amount else 0
            monthly_needed = remaining / max(1, months_remaining)
            return {
                "type": "target_by_date",
                "target": goal.target_amount,
                "target_date": goal.target_date.isoformat() if goal.target_date else None,
                "saved": available,
                "progress": min(100, max(0, progress)),
                "monthly_needed": monthly_needed,
                "months_remaining": months_remaining
            }

        elif goal.goal_type == GoalType.MONTHLY_FUNDING:
            # Check if funded this month
            entry = (
                self.session.query(BudgetEntry)
                .filter(BudgetEntry.category_id == goal.category_id)
                .filter(BudgetEntry.month == month_start)
                .first()
            )
            budgeted = entry.budgeted if entry else 0
            return {
                "type": "monthly_funding",
                "target": goal.monthly_funding,
                "budgeted": budgeted,
                "funded": budgeted >= (goal.monthly_funding or 0)
            }

        elif goal.goal_type == GoalType.SPENDING:
            return {
                "type": "spending",
                "target": goal.target_amount,
                "available": available
            }

        return {}

    def _months_between(self, start: date, end: date) -> int:
        """Calculate months between two dates."""
        if not end:
            return 12  # Default to 1 year if no target date
        return (end.year - start.year) * 12 + (end.month - start.month)
