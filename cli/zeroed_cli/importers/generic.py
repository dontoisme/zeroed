"""
Generic CSV importer with configurable column mappings.

Works with most bank CSV exports by auto-detecting common column names.
"""

import csv
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from .base import BaseImporter
from ..core.models import Transaction


class GenericImporter(BaseImporter):
    """Generic CSV importer with auto-detection."""

    name = "generic"
    institution = "Any"
    description = "Generic importer - auto-detects common column formats"

    # Common column name variations
    DATE_COLUMNS = [
        "date", "transaction date", "trans date", "posting date",
        "post date", "transaction_date", "Date"
    ]
    AMOUNT_COLUMNS = [
        "amount", "transaction amount", "debit/credit", "Amount"
    ]
    DEBIT_COLUMNS = [
        "debit", "withdrawal", "debit amount", "withdrawals"
    ]
    CREDIT_COLUMNS = [
        "credit", "deposit", "credit amount", "deposits"
    ]
    PAYEE_COLUMNS = [
        "description", "payee", "merchant", "name", "memo",
        "transaction description", "Description"
    ]
    MEMO_COLUMNS = [
        "memo", "notes", "reference", "check number"
    ]

    # Common date formats to try
    DATE_FORMATS = [
        "%m/%d/%Y",
        "%Y-%m-%d",
        "%m/%d/%y",
        "%d/%m/%Y",
        "%Y/%m/%d",
        "%m-%d-%Y",
        "%d-%m-%Y",
    ]

    def detect(self, filepath: Path) -> bool:
        """Generic always returns False to be used as fallback."""
        return False

    def parse(self, filepath: Path, account_id: int) -> List[Transaction]:
        """Parse CSV with auto-detected columns."""
        transactions = []

        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            headers = [h.lower().strip() for h in (reader.fieldnames or [])]
            original_headers = reader.fieldnames or []

            # Find column mappings
            date_col = self._find_column(headers, original_headers, self.DATE_COLUMNS)
            amount_col = self._find_column(headers, original_headers, self.AMOUNT_COLUMNS)
            debit_col = self._find_column(headers, original_headers, self.DEBIT_COLUMNS)
            credit_col = self._find_column(headers, original_headers, self.CREDIT_COLUMNS)
            payee_col = self._find_column(headers, original_headers, self.PAYEE_COLUMNS)
            memo_col = self._find_column(headers, original_headers, self.MEMO_COLUMNS)

            if not date_col:
                raise ValueError("Could not find date column")
            if not amount_col and not (debit_col or credit_col):
                raise ValueError("Could not find amount column(s)")
            if not payee_col:
                raise ValueError("Could not find payee/description column")

            for row in reader:
                txn = self._parse_row(
                    row, account_id,
                    date_col, amount_col, debit_col, credit_col,
                    payee_col, memo_col
                )
                if txn:
                    transactions.append(txn)

        return transactions

    def _find_column(
        self,
        lower_headers: List[str],
        original_headers: List[str],
        candidates: List[str]
    ) -> Optional[str]:
        """Find a column by checking candidate names."""
        for candidate in candidates:
            candidate_lower = candidate.lower()
            if candidate_lower in lower_headers:
                idx = lower_headers.index(candidate_lower)
                return original_headers[idx]
        return None

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Try to parse date using common formats."""
        date_str = date_str.strip()
        for fmt in self.DATE_FORMATS:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue
        return None

    def _parse_row(
        self,
        row: dict,
        account_id: int,
        date_col: str,
        amount_col: Optional[str],
        debit_col: Optional[str],
        credit_col: Optional[str],
        payee_col: str,
        memo_col: Optional[str]
    ) -> Optional[Transaction]:
        """Parse a single row."""
        # Parse date
        date_str = row.get(date_col, "")
        txn_date = self._parse_date(date_str)
        if not txn_date:
            return None

        # Parse amount
        amount = 0.0
        if amount_col:
            # Single amount column
            amount_str = row.get(amount_col, "0")
            amount_str = amount_str.replace("$", "").replace(",", "").strip()
            if amount_str.startswith("(") and amount_str.endswith(")"):
                # Accounting format for negative
                amount_str = "-" + amount_str[1:-1]
            try:
                amount = float(amount_str) if amount_str else 0
            except ValueError:
                return None
        else:
            # Separate debit/credit columns
            if debit_col:
                debit_str = row.get(debit_col, "0")
                debit_str = debit_str.replace("$", "").replace(",", "").strip()
                try:
                    debit = float(debit_str) if debit_str else 0
                    amount -= abs(debit)
                except ValueError:
                    pass

            if credit_col:
                credit_str = row.get(credit_col, "0")
                credit_str = credit_str.replace("$", "").replace(",", "").strip()
                try:
                    credit = float(credit_str) if credit_str else 0
                    amount += abs(credit)
                except ValueError:
                    pass

        if amount == 0:
            return None

        # Get payee
        payee = row.get(payee_col, "").strip()
        if not payee:
            payee = "Unknown"

        # Get memo
        memo = row.get(memo_col, "").strip() if memo_col else None

        return self.create_transaction(
            account_id=account_id,
            txn_date=txn_date,
            amount=amount,
            payee_name=payee,
            memo=memo,
            import_source="generic"
        )
