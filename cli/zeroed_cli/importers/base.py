"""
Base importer class for CSV files.
"""

from abc import ABC, abstractmethod
from datetime import date
from pathlib import Path
from typing import List
import hashlib

from ..core.models import Transaction, TransactionType


class BaseImporter(ABC):
    """Base class for CSV importers."""

    name: str = "base"
    institution: str = "Unknown"
    description: str = "Base importer"

    @abstractmethod
    def parse(self, filepath: Path, account_id: int) -> List[Transaction]:
        """
        Parse CSV file into Transaction objects.

        Args:
            filepath: Path to CSV file
            account_id: ID of the account to import into

        Returns:
            List of Transaction objects (not yet added to session)
        """
        pass

    @abstractmethod
    def detect(self, filepath: Path) -> bool:
        """
        Check if this importer can handle the file.

        Args:
            filepath: Path to CSV file

        Returns:
            True if this importer should handle the file
        """
        pass

    @staticmethod
    def generate_import_id(
        account_id: int,
        txn_date: date,
        amount: float,
        payee_name: str
    ) -> str:
        """Generate unique ID for deduplication during import."""
        data = f"{account_id}:{txn_date.isoformat()}:{amount:.2f}:{payee_name}"
        return hashlib.md5(data.encode()).hexdigest()

    @staticmethod
    def create_transaction(
        account_id: int,
        txn_date: date,
        amount: float,
        payee_name: str,
        memo: str = None,
        import_source: str = None
    ) -> Transaction:
        """Create a Transaction object with proper import_id."""
        import_id = BaseImporter.generate_import_id(
            account_id, txn_date, amount, payee_name
        )

        return Transaction(
            account_id=account_id,
            date=txn_date,
            amount=amount,
            transaction_type=(
                TransactionType.INFLOW if amount > 0 else TransactionType.OUTFLOW
            ),
            memo=memo,
            import_id=import_id,
            import_source=import_source,
            raw_payee_name=payee_name,
        )
