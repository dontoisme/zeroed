"""
CLI command groups for Zeroed.
"""

from . import accounts
from . import categories
from . import transactions
from . import budget
from . import rules
from . import import_cmd
from . import reports

__all__ = [
    "accounts",
    "categories",
    "transactions",
    "budget",
    "rules",
    "import_cmd",
    "reports",
]
