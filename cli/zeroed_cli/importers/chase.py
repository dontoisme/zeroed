"""
Chase bank CSV importer.

Supports both Chase checking/savings and Chase credit card formats.
"""

import csv
from datetime import datetime
from pathlib import Path
from typing import List

from .base import BaseImporter
from ..core.models import Transaction


class ChaseImporter(BaseImporter):
    """Import Chase bank CSV exports."""

    name = "chase"
    institution = "Chase Bank"
    description = "Chase checking, savings, and credit card statements"

    # Chase credit card columns
    CC_COLUMNS = {
        "date": "Transaction Date",
        "post_date": "Post Date",
        "description": "Description",
        "category": "Category",
        "type": "Type",
        "amount": "Amount",
        "memo": "Memo",
    }

    # Chase checking/savings columns
    BANK_COLUMNS = {
        "date": "Posting Date",
        "description": "Description",
        "amount": "Amount",
        "type": "Type",
        "balance": "Balance",
    }

    def detect(self, filepath: Path) -> bool:
        """Detect if this is a Chase CSV."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                headers = reader.fieldnames or []

                # Check for credit card format
                if "Transaction Date" in headers and "Description" in headers:
                    return True

                # Check for checking/savings format
                if "Posting Date" in headers and "Description" in headers:
                    return True

                return False
        except Exception:
            return False

    def parse(self, filepath: Path, account_id: int) -> List[Transaction]:
        """Parse Chase CSV format."""
        transactions = []

        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames or []

            # Determine format
            is_credit_card = "Transaction Date" in headers

            for row in reader:
                if is_credit_card:
                    txn = self._parse_credit_card_row(row, account_id)
                else:
                    txn = self._parse_bank_row(row, account_id)

                if txn:
                    transactions.append(txn)

        return transactions

    def _parse_credit_card_row(self, row: dict, account_id: int) -> Transaction:
        """Parse a credit card CSV row."""
        # Parse date (MM/DD/YYYY)
        date_str = row.get(self.CC_COLUMNS["date"], "")
        try:
            txn_date = datetime.strptime(date_str, "%m/%d/%Y").date()
        except ValueError:
            return None

        # Parse amount (negative for charges, positive for payments/credits)
        amount_str = row.get(self.CC_COLUMNS["amount"], "0")
        try:
            amount = float(amount_str)
        except ValueError:
            return None

        # Description is payee
        payee = row.get(self.CC_COLUMNS["description"], "").strip()
        memo = row.get(self.CC_COLUMNS["memo"], "").strip() or None

        return self.create_transaction(
            account_id=account_id,
            txn_date=txn_date,
            amount=amount,
            payee_name=payee,
            memo=memo,
            import_source="chase_cc"
        )

    def _parse_bank_row(self, row: dict, account_id: int) -> Transaction:
        """Parse a checking/savings CSV row."""
        # Parse date (MM/DD/YYYY)
        date_str = row.get(self.BANK_COLUMNS["date"], "")
        try:
            txn_date = datetime.strptime(date_str, "%m/%d/%Y").date()
        except ValueError:
            return None

        # Parse amount
        amount_str = row.get(self.BANK_COLUMNS["amount"], "0")
        try:
            amount = float(amount_str)
        except ValueError:
            return None

        # Description is payee
        payee = row.get(self.BANK_COLUMNS["description"], "").strip()

        return self.create_transaction(
            account_id=account_id,
            txn_date=txn_date,
            amount=amount,
            payee_name=payee,
            import_source="chase_bank"
        )
