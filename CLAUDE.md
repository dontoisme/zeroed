# Claude Context: Zeroed Budget App

This file helps Claude understand the Zeroed project structure and common operations.

## Project Overview

Zeroed is a YNAB-style zero-based budgeting app with:
- **Python CLI** (`cli/`) - Data import, budget management, reports
- **Next.js Web** (`web/`) - Visual dashboard for budget viewing

Both share a single SQLite database at `cli/data/budget.db`.

## Key Files

### CLI (Python)
| File | Purpose |
|------|---------|
| `cli/zeroed_cli/main.py` | CLI entry point, command groups |
| `cli/zeroed_cli/core/models.py` | SQLAlchemy models (Account, Category, Transaction, etc.) |
| `cli/zeroed_cli/core/database.py` | Database session management, initialization |
| `cli/zeroed_cli/services/budget_service.py` | Zero-based budgeting logic |
| `cli/zeroed_cli/importers/chase.py` | Chase CSV parser |
| `cli/zeroed_cli/categorization/engine.py` | Auto-categorization rules |

### Web (Next.js)
| File | Purpose |
|------|---------|
| `web/prisma/schema.prisma` | Database schema (mirrors SQLAlchemy) |
| `web/src/lib/prisma.ts` | Prisma client singleton |
| `web/src/app/api/budget/route.ts` | Budget API endpoint |
| `web/src/app/page.tsx` | Main budget dashboard page |

## Database Schema

Core tables:
- `accounts` - Bank accounts, credit cards
- `category_groups` - Budget category groups (Bills, Everyday, etc.)
- `categories` - Individual categories within groups
- `transactions` - All financial transactions
- `payees` - Merchant/payee names
- `payee_match_rules` - Auto-categorization rules
- `budget_entries` - Monthly budget allocations per category
- `goals` - Savings goals per category

## Important: DateTime Format

**Critical**: The database uses this datetime format for compatibility between SQLAlchemy and Prisma:
```
YYYY-MM-DD HH:MM:SS
Example: 2026-01-04 17:36:14
```

Do NOT use:
- Microseconds: `2026-01-04 17:36:14.123456` (breaks Prisma)
- ISO with T: `2026-01-04T17:36:14` (breaks Prisma)
- Z suffix: `2026-01-04T17:36:14Z` (breaks SQLAlchemy)

The `utcnow_iso()` function in `models.py` handles this.

## Common Tasks

### Run CLI Commands
```bash
zeroed accounts list
zeroed categories list --tree
zeroed budget show
zeroed budget set "Groceries" 500
zeroed import csv file.csv --account "Chase Checking"
```

### Start Web Dashboard
```bash
cd ~/Projects/zeroed/web
npm run dev
# http://localhost:3000
```

### Fix Web Dashboard Issues
```bash
cd ~/Projects/zeroed/web
rm -rf .next node_modules/.prisma
npx prisma generate
npm run dev
```

### Reset Database
```bash
rm ~/Projects/zeroed/cli/data/budget.db
zeroed categories list  # Recreates with defaults
```

## Zero-Based Budgeting Logic

### Ready to Assign Calculation
```python
ready_to_assign = (
    total_income_this_month
    - total_budgeted_this_month
    + carryover_from_previous_months
)

carryover = (
    all_previous_income
    + all_previous_spending  # negative values
    - all_previous_budgeted
)
```

### Category Available Balance
```python
available = budgeted_this_month + activity  # activity is negative for spending
```

## Adding New Features

### New CLI Command
1. Create file in `cli/zeroed_cli/commands/`
2. Register in `cli/zeroed_cli/main.py`

### New API Endpoint
1. Create route in `web/src/app/api/`
2. Use Prisma client from `@/lib/prisma`

### New Database Column
1. Add to SQLAlchemy model in `cli/zeroed_cli/core/models.py`
2. Add to Prisma schema in `web/prisma/schema.prisma`
3. Run `npx prisma db push` or migrate

## Enums (Stored as Strings)

SQLite doesn't support enums, so these are stored as strings:

| Type | Values |
|------|--------|
| AccountType | CHECKING, SAVINGS, CREDIT_CARD, CASH, INVESTMENT |
| TransactionType | INFLOW, OUTFLOW, TRANSFER |
| GoalType | TARGET_BALANCE, TARGET_BY_DATE, MONTHLY_FUNDING, SPENDING |
| MatchType | CONTAINS, STARTS_WITH, EXACT, REGEX |

## Default Categories

Created automatically on first run:
```
Bills: Rent/Mortgage, Electric, Internet, Phone, Insurance
Everyday: Groceries, Dining Out, Transportation, Gas
Fun: Entertainment, Hobbies, Subscriptions
Savings Goals: Emergency Fund, Vacation, Big Purchases
Giving: Charity, Gifts
```
