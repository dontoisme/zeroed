# Zeroed - Zero-Based Budget App

[![Powered by Claude Code](https://raw.githubusercontent.com/dontoisme/awesome-powered-by-claude-code/main/badges/powered-by-claude-code-dark.svg)](https://github.com/dontoisme/awesome-powered-by-claude-code)

A YNAB-style personal finance application with a Python CLI for data management and a Next.js web dashboard for visualization. Uses local SQLite storage for privacy.

## Architecture

```
zeroed/
├── cli/                    # Python CLI (Click + Rich + SQLAlchemy)
│   ├── zeroed_cli/
│   │   ├── commands/       # CLI command groups
│   │   ├── core/           # Database, models, config
│   │   ├── importers/      # Bank-specific CSV parsers
│   │   ├── categorization/ # Auto-categorization engine
│   │   └── services/       # Budget logic
│   └── data/budget.db      # SQLite database
│
└── web/                    # Next.js dashboard
    ├── prisma/             # Prisma schema (mirrors SQLAlchemy)
    └── src/
        ├── app/api/        # API routes
        └── components/     # React components
```

## Quick Start

### CLI Setup
```bash
cd ~/Projects/zeroed/cli
pip install -e .
zeroed --help
```

### Web Dashboard
```bash
cd ~/Projects/zeroed/web
npm install
npm run dev
# Open http://localhost:3000
```

---

## CLI Commands Reference

### Account Management

```bash
# List all accounts
zeroed accounts list

# Create a new account
zeroed accounts create "Chase Checking" --type checking
zeroed accounts create "Chase Sapphire" --type credit_card
zeroed accounts create "Savings" --type savings

# Account types: checking, savings, credit_card, cash, investment
```

### Category Management

```bash
# View all categories in tree format
zeroed categories list --tree

# View flat list
zeroed categories list
```

Default categories (YNAB-style):
- **Bills**: Rent/Mortgage, Electric, Internet, Phone, Insurance
- **Everyday**: Groceries, Dining Out, Transportation, Gas
- **Fun**: Entertainment, Hobbies, Subscriptions
- **Savings Goals**: Emergency Fund, Vacation, Big Purchases
- **Giving**: Charity, Gifts

### Budget Operations

```bash
# Show current month's budget
zeroed budget show

# Show specific month
zeroed budget show --month 2026-01

# Set budget for a category
zeroed budget set "Groceries" 500
zeroed budget set "Rent/Mortgage" 2000

# Get AI-suggested budgets based on 3-month spending average
zeroed budget auto
```

### Transaction Import

```bash
# Import from CSV file
zeroed import csv ~/Downloads/chase_statement.csv --account "Chase Checking"

# List available import profiles
zeroed import profiles

# Supported formats:
# - Chase (checking & credit card)
# - Generic CSV (configurable columns)
```

### Transaction Management

```bash
# List recent transactions
zeroed transactions list

# Filter by account
zeroed transactions list --account "Chase Checking"

# Filter by month
zeroed transactions list --month 2026-01

# Auto-categorize uncategorized transactions
zeroed transactions categorize
```

### Categorization Rules

```bash
# List all rules
zeroed rules list

# Create a new rule (auto-categorize "TRADER JOE" as Groceries)
zeroed rules create "TRADER JOE" --category "Groceries"

# Rule types: contains (default), starts_with, exact, regex
zeroed rules create "^AMZN" --category "Shopping" --type regex
```

### Reports

```bash
# Spending summary
zeroed reports summary

# Spending by category (last 6 months)
zeroed reports spending --months 6
```

---

## Common Workflows

### 1. Initial Setup (New Budget)

```bash
# 1. Create your accounts
zeroed accounts create "Chase Checking" --type checking
zeroed accounts create "Chase Sapphire" --type credit_card
zeroed accounts create "Ally Savings" --type savings

# 2. View default categories (already created)
zeroed categories list --tree

# 3. Set your first month's budget
zeroed budget set "Rent/Mortgage" 2000
zeroed budget set "Groceries" 600
zeroed budget set "Dining Out" 200
zeroed budget set "Gas" 150
zeroed budget set "Electric" 100
zeroed budget set "Internet" 80
zeroed budget set "Phone" 50
zeroed budget set "Entertainment" 100
zeroed budget set "Subscriptions" 50

# 4. View your budget
zeroed budget show
```

### 2. Monthly Budget Routine

```bash
# 1. Import latest statements
zeroed import csv ~/Downloads/chase_checking_jan.csv --account "Chase Checking"
zeroed import csv ~/Downloads/chase_cc_jan.csv --account "Chase Sapphire"

# 2. Auto-categorize transactions
zeroed transactions categorize

# 3. Review uncategorized transactions
zeroed transactions list --uncategorized

# 4. Check your budget status
zeroed budget show

# 5. View spending report
zeroed reports summary
```

### 3. Setting Up Auto-Categorization

```bash
# Create rules for common merchants
zeroed rules create "TRADER JOE" --category "Groceries"
zeroed rules create "WHOLE FOODS" --category "Groceries"
zeroed rules create "SAFEWAY" --category "Groceries"
zeroed rules create "CHEVRON" --category "Gas"
zeroed rules create "SHELL" --category "Gas"
zeroed rules create "NETFLIX" --category "Subscriptions"
zeroed rules create "SPOTIFY" --category "Subscriptions"
zeroed rules create "UBER EATS" --category "Dining Out"
zeroed rules create "DOORDASH" --category "Dining Out"

# Test auto-categorization
zeroed transactions categorize
```

### 4. End of Month Review

```bash
# 1. Import final statements
zeroed import csv ~/Downloads/statement.csv --account "Chase Checking"

# 2. Categorize any remaining transactions
zeroed transactions categorize

# 3. Review spending
zeroed reports spending --months 1

# 4. Check budget status
zeroed budget show

# 5. Get suggestions for next month
zeroed budget auto
```

### 5. Starting a New Month

```bash
# 1. View previous month for reference
zeroed budget show --month 2026-01

# 2. Set new month's budget (copy or adjust)
zeroed budget set "Groceries" 600
# ... set other categories

# 3. Check "Ready to Assign"
zeroed budget show
```

---

## Web Dashboard

### Starting the Dashboard

```bash
cd ~/Projects/zeroed/web
npm run dev
```

Open http://localhost:3000

### Features

1. **Budget View**: Monthly budget with all categories
2. **Ready to Assign**: Shows unbudgeted money
3. **Month Navigation**: Switch between months
4. **Category Breakdown**: Budgeted vs. Activity vs. Available

### API Endpoints

- `GET /api/budget?month=2026-01` - Get budget for a month

---

## Zero-Based Budgeting Concepts

### "Every Dollar Has a Job"
In zero-based budgeting, you assign every dollar of income to a category until "Ready to Assign" equals zero.

### Ready to Assign
```
Ready to Assign = Total Income - Total Budgeted + Carryover from Previous Months
```

### Category Available Balance
```
Available = Budgeted This Month + Activity (spending is negative)
```

### Handling Overspending
If a category goes negative (overspent), that amount reduces your "Ready to Assign" next month.

---

## Database

### Location
```
~/Projects/zeroed/cli/data/budget.db
```

### Backup
```bash
cp ~/Projects/zeroed/cli/data/budget.db ~/Projects/zeroed/cli/data/budget.db.backup
```

### Reset (Start Fresh)
```bash
rm ~/Projects/zeroed/cli/data/budget.db
zeroed categories list  # Triggers recreation with defaults
```

---

## CSV Import Formats

### Chase Checking
```csv
Details,Posting Date,Description,Amount,Type,Balance,Check or Slip #
DEBIT,01/15/2026,TRADER JOE'S,-45.67,DEBIT_CARD,1234.56,
```

### Chase Credit Card
```csv
Transaction Date,Post Date,Description,Category,Type,Amount,Memo
01/15/2026,01/16/2026,AMAZON.COM,Shopping,Sale,-29.99,
```

### Generic CSV
For other formats, the importer will ask you to map columns:
- Date column
- Amount column (or separate inflow/outflow)
- Payee/Description column
- Optional: Memo column

---

## Troubleshooting

### CLI not found
```bash
cd ~/Projects/zeroed/cli
pip install -e .
```

### Web dashboard errors
```bash
cd ~/Projects/zeroed/web
rm -rf .next node_modules/.prisma
npx prisma generate
npm run dev
```

### Database datetime issues
If you see "Inconsistent column data" errors:
```bash
# The database uses space-separated datetime format: "2026-01-04 17:36:14"
# Both SQLAlchemy and Prisma expect this format
```

### Port already in use
```bash
# Kill process on port 3000
lsof -ti:3000 | xargs kill -9
```

---

## Tech Stack

- **CLI**: Python 3.9+, Click, Rich, SQLAlchemy, Pydantic
- **Web**: Next.js 16, React 19, Prisma 5, Tailwind CSS, Recharts
- **Database**: SQLite (shared between CLI and web)
