# Zeroed Quick Reference

## Accounts
```bash
zeroed accounts list                              # List all accounts
zeroed accounts create "Name" --type checking    # Create account
# Types: checking, savings, credit_card, cash, investment
```

## Categories
```bash
zeroed categories list --tree                    # View hierarchy
zeroed categories list                           # Flat list
```

## Budget
```bash
zeroed budget show                               # Current month
zeroed budget show --month 2026-01               # Specific month
zeroed budget set "Category" 500                 # Set amount
zeroed budget auto                               # Get suggestions
```

## Transactions
```bash
zeroed transactions list                         # All recent
zeroed transactions list --account "Name"        # By account
zeroed transactions list --month 2026-01         # By month
zeroed transactions categorize                   # Auto-categorize
```

## Import
```bash
zeroed import csv file.csv --account "Name"      # Import CSV
zeroed import profiles                           # List formats
```

## Rules
```bash
zeroed rules list                                # All rules
zeroed rules create "PATTERN" --category "Cat"   # New rule
# Types: contains (default), starts_with, exact, regex
```

## Reports
```bash
zeroed reports summary                           # Overview
zeroed reports spending --months 6               # By category
```

## Web Dashboard
```bash
cd ~/Projects/zeroed/web && npm run dev          # Start
# Open http://localhost:3000
```

---

## New Budget Workflow

```bash
# 1. Create accounts
zeroed accounts create "Chase Checking" --type checking
zeroed accounts create "Credit Card" --type credit_card

# 2. Set budget amounts
zeroed budget set "Rent/Mortgage" 2000
zeroed budget set "Groceries" 600
zeroed budget set "Dining Out" 200
# ... continue for all categories

# 3. Import transactions
zeroed import csv statement.csv --account "Chase Checking"

# 4. Categorize
zeroed transactions categorize

# 5. Review
zeroed budget show
```

## Monthly Routine

```bash
# 1. Import new statements
zeroed import csv checking.csv --account "Chase Checking"
zeroed import csv credit.csv --account "Credit Card"

# 2. Auto-categorize
zeroed transactions categorize

# 3. Check budget
zeroed budget show

# 4. Review spending
zeroed reports summary
```

## Set Up Auto-Categorization

```bash
zeroed rules create "TRADER JOE" --category "Groceries"
zeroed rules create "WHOLE FOODS" --category "Groceries"
zeroed rules create "CHEVRON" --category "Gas"
zeroed rules create "NETFLIX" --category "Subscriptions"
zeroed rules create "UBER EATS" --category "Dining Out"
```

---

## Troubleshooting

```bash
# CLI not working
cd ~/Projects/zeroed/cli && pip install -e .

# Web not working
cd ~/Projects/zeroed/web
rm -rf .next && npx prisma generate && npm run dev

# Reset database
rm ~/Projects/zeroed/cli/data/budget.db
zeroed categories list  # Recreates defaults

# Port in use
lsof -ti:3000 | xargs kill -9
```
