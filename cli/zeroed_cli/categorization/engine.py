"""
Transaction categorization engine.

Uses rules and payee matching to auto-categorize transactions.
"""

import re
from typing import Optional, List
from sqlalchemy.orm import Session

from ..core.models import Category, Payee, PayeeMatchRule, MatchType


class CategorizationEngine:
    """
    Rules-based transaction categorization.

    Priority:
    1. Exact payee match with default category
    2. Pattern match rules (ordered by priority)
    3. None (uncategorized)
    """

    def __init__(self, session: Session):
        self.session = session
        self._rules = None

    @property
    def rules(self) -> List[PayeeMatchRule]:
        """Lazily load match rules."""
        if self._rules is None:
            self._rules = (
                self.session.query(PayeeMatchRule)
                .order_by(PayeeMatchRule.priority.desc())
                .all()
            )
        return self._rules

    def categorize(self, payee_name: str) -> Optional[Category]:
        """
        Auto-categorize based on payee name.

        Args:
            payee_name: Raw payee name from transaction

        Returns:
            Category if a match is found, None otherwise
        """
        if not payee_name:
            return None

        payee_lower = payee_name.lower().strip()

        # 1. Check for exact payee match
        payee = (
            self.session.query(Payee)
            .filter(Payee.name.ilike(payee_lower))
            .first()
        )

        if payee and payee.default_category_id and payee.auto_categorize:
            return payee.default_category

        # 2. Try pattern matching rules
        for rule in self.rules:
            if self._matches_rule(payee_lower, rule):
                return rule.payee.default_category

        return None

    def _matches_rule(self, payee_name: str, rule: PayeeMatchRule) -> bool:
        """Check if payee matches a rule."""
        pattern = rule.pattern.lower()

        if rule.match_type == MatchType.CONTAINS:
            return pattern in payee_name
        elif rule.match_type == MatchType.STARTS_WITH:
            return payee_name.startswith(pattern)
        elif rule.match_type == MatchType.EXACT:
            return payee_name == pattern
        elif rule.match_type == MatchType.REGEX:
            try:
                return bool(re.match(pattern, payee_name, re.IGNORECASE))
            except re.error:
                return False

        return False

    def create_rule(
        self,
        pattern: str,
        category_name: str,
        match_type: MatchType = MatchType.CONTAINS,
        priority: int = 0
    ) -> PayeeMatchRule:
        """
        Create a new categorization rule.

        Args:
            pattern: Pattern to match
            category_name: Name of category to assign
            match_type: Type of matching
            priority: Higher priority rules are checked first

        Returns:
            Created PayeeMatchRule
        """
        # Find category
        category = (
            self.session.query(Category)
            .filter(Category.name.ilike(f"%{category_name}%"))
            .first()
        )
        if not category:
            raise ValueError(f"Category not found: {category_name}")

        # Create or find payee
        payee_name = f"Rule: {pattern}"
        payee = (
            self.session.query(Payee)
            .filter(Payee.name == payee_name)
            .first()
        )
        if not payee:
            payee = Payee(
                name=payee_name,
                default_category_id=category.id,
                auto_categorize=True
            )
            self.session.add(payee)
            self.session.flush()

        # Create rule
        rule = PayeeMatchRule(
            payee_id=payee.id,
            pattern=pattern,
            match_type=match_type,
            priority=priority
        )
        self.session.add(rule)

        # Invalidate cache
        self._rules = None

        return rule

    def learn_from_categorization(
        self,
        payee_name: str,
        category: Category
    ) -> Payee:
        """
        Learn from a manual categorization.

        Creates or updates a payee with the default category.

        Args:
            payee_name: Original payee name
            category: Category that was assigned

        Returns:
            Created or updated Payee
        """
        # Find or create payee
        payee = (
            self.session.query(Payee)
            .filter(Payee.name.ilike(payee_name))
            .first()
        )

        if payee:
            payee.default_category_id = category.id
        else:
            payee = Payee(
                name=payee_name,
                default_category_id=category.id,
                auto_categorize=True
            )
            self.session.add(payee)

        return payee

    def suggest_categories(self, payee_name: str, limit: int = 5) -> List[Category]:
        """
        Suggest categories based on similar payees.

        Args:
            payee_name: Payee name to find suggestions for
            limit: Maximum number of suggestions

        Returns:
            List of suggested categories
        """
        if not payee_name or len(payee_name) < 3:
            return []

        # Find payees with similar names
        prefix = payee_name[:5].lower()
        similar = (
            self.session.query(Payee)
            .filter(Payee.name.ilike(f"%{prefix}%"))
            .filter(Payee.default_category_id.isnot(None))
            .limit(limit)
            .all()
        )

        # Get unique categories
        seen = set()
        categories = []
        for payee in similar:
            if payee.default_category_id not in seen:
                seen.add(payee.default_category_id)
                categories.append(payee.default_category)

        return categories
