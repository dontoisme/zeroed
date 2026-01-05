#!/usr/bin/env python3
"""
Zeroed - Zero-based budgeting CLI

A YNAB-style personal finance tool for managing budgets,
importing transactions, and tracking spending.

Usage:
    zeroed accounts list           # List all accounts
    zeroed accounts create         # Create new account
    zeroed import csv <file>       # Import transactions from CSV
    zeroed transactions list       # List transactions
    zeroed budget show             # Show current month budget
    zeroed budget set              # Set category budget
    zeroed reports spending        # Spending by category
"""

import click
from pathlib import Path
from rich.console import Console

from .core.database import init_db, get_session, create_default_categories

console = Console()


@click.group()
@click.option(
    "--db",
    type=click.Path(),
    default=None,
    help="Database file path (default: cli/data/budget.db)"
)
@click.pass_context
def cli(ctx, db):
    """
    Zeroed - Zero-based budgeting CLI

    Personal finance management with YNAB-style zero-based budgeting.
    """
    ctx.ensure_object(dict)

    # Initialize database
    init_db(db)
    ctx.obj["db_path"] = db

    # Create default categories on first run
    with get_session() as session:
        create_default_categories(session)


@cli.command()
def version():
    """Show the version."""
    console.print("[bold green]Zeroed[/bold green] v0.1.0")
    console.print("Zero-based budgeting CLI")


@cli.command()
def init():
    """Initialize a new budget database with default categories."""
    with get_session() as session:
        create_default_categories(session)
    console.print("[green]Database initialized with default categories![/green]")


# Import command groups
from .commands import accounts, categories, transactions, budget, rules, import_cmd, reports

cli.add_command(accounts.accounts_group, name="accounts")
cli.add_command(categories.categories_group, name="categories")
cli.add_command(transactions.transactions_group, name="transactions")
cli.add_command(budget.budget_group, name="budget")
cli.add_command(rules.rules_group, name="rules")
cli.add_command(import_cmd.import_group, name="import")
cli.add_command(reports.reports_group, name="reports")


if __name__ == "__main__":
    cli()
